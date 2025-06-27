import asyncio
import time
import traceback
from concurrent.futures.thread import ThreadPoolExecutor

from generated.extras_pb2 import ClusterNodeStatus, DBHealthStatus
from agent import ServerConfig
from agent.domain.mysql import MySQL
from agent.internal.utils import get_redis_client


class MySQLHealthCheckMonitor:
    def __init__(self):
        self.config = ServerConfig()
        self.tasks: dict[str, asyncio.Task] = {}
        self.tasks_lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.redis = get_redis_client(async_client=True)
        self.sync_db_ids_lock = asyncio.Lock()
        self.last_sync_in_cluster_config: dict[str, float] = {}

    async def monitor_db_health(self, db_id:str):
        loop = asyncio.get_running_loop()
        db_record = MySQL(db_id)
        _ = db_record.get_db_conn() # Ensure the connection object is created
        while True:
            start = time.time()
            try:
                result: tuple[bool, DBHealthStatus] = await loop.run_in_executor(
                    self.executor,
                    db_record.get_health_info
                )
                success, health_info = result
                if success:
                    db_record.kv.put(db_record.kv_cluster_node_status_key, health_info.SerializeToString())
                    if db_id not in self.last_sync_in_cluster_config or \
                            time.time() - self.last_sync_in_cluster_config[db_id] > 600: # 10 minutes
                        self.mark_db_as_online_in_config(db_record)
                else:
                    # Remove the db_id from last_sync_in_cluster_config
                    # So that it can quickly marked as online again once we get a successful health check
                    if db_id in self.last_sync_in_cluster_config:
                        del self.last_sync_in_cluster_config[db_id]
            finally:
                end = time.time()
                elapsed_ms = int((end - start)*1000)
                wait_time = max(0, (self.config.db_healthcheck_interval_ms - elapsed_ms))
                wait_time = max(wait_time, self.config.db_healthcheck_minimum_interval_ms)
                await asyncio.sleep(wait_time/1000)  # Convert ms to seconds

    def mark_db_as_online_in_config(self, db_record: MySQL):
        """
        If DB is online but marked as offline in cluster config, mark it as online.
        Do this operation every 10 minute.

        :return:
        """
        try:
            db_record.cluster_config.reload()
            if db_record.cluster_config.get_node(db_record.model.id).status != ClusterNodeStatus.OFFLINE:
                # If node is already marked as online / in maintenance, do nothing
                return

            old_version = db_record.cluster_config.version
            etcd_client = db_record.kv
            txn_success, _  = etcd_client.transaction(
                compare=[
                    etcd_client.transactions.version(db_record.cluster_config.kv_cluster_config_key) == old_version
                ],
                success=[
                    etcd_client.transactions.put(
                        db_record.cluster_config.kv_cluster_config_key,
                        db_record.cluster_config.copy_and_mark_node_as_online(db_record.model.id).SerializeToString()
                    )
                ],
                failure=[]
            )
            if txn_success:
                print("Marked db as online in cluster config:", db_record.model.id)
                self.last_sync_in_cluster_config[db_record.model.id] = time.time()
            else:
                print("Failed to mark db as online in cluster config, config updated in-between. Will be retried later")

        except Exception as e:
            print("Failed to reload cluster config for db:", db_record.model.id, e)

    async def add_db_to_monitoring(self, db_id:str):
        async with self.tasks_lock:
            if db_id in self.tasks:
                return
            if not MySQL.exists(db_id):
                return
            task = asyncio.create_task(self.monitor_db_health(db_id))
            self.tasks[db_id] = task

    async def remove_db_from_monitoring(self, db_id:str):
        async with self.tasks_lock:
            if db_id not in self.tasks:
                return
            self.tasks[db_id].cancel()
            try:
                await self.tasks[db_id]
            except asyncio.CancelledError:
                pass
            del self.tasks[db_id]

    async def process_requested_changes_in_monitoring(self):
        while True:
            try:
                pubsub = self.redis.pubsub()
                await pubsub.subscribe(self.config.mysql_monitor_commands_redis_channel)

                async for msg in pubsub.listen():
                    if msg["type"] != "message":
                        continue

                    try:
                        async with self.sync_db_ids_lock:
                            cmd_parts = msg["data"].decode().strip().split(maxsplit=2)
                            if len(cmd_parts) != 2:
                                continue

                            cmd = cmd_parts[0]
                            db_id = cmd_parts[1]

                            if cmd in ["remove", "reload"]:
                                await self.remove_db_from_monitoring(db_id)

                            if cmd in ["add", "reload"]:
                                await self.add_db_to_monitoring(db_id)
                    except Exception as e:
                        print("Command handling error:", e)
                        traceback.print_exc()
            except Exception as e:
                print("Redis connection failed, retrying in 5s...", e)
                traceback.print_exc()
                await asyncio.sleep(5)

    async def sync_monitored_db_ids_periodically(self):
        while True:
            try:
                # Try to acquire the lock to prevent concurrent modifications
                # by the watch_commands method
                async with self.sync_db_ids_lock:
                    db_ids = set(MySQL.get_all())
                    current_monitoring = set(self.tasks.keys())

                    to_add = db_ids - current_monitoring
                    to_remove = current_monitoring - db_ids

                    for db_id in to_add:
                        await  self.redis.publish(self.config.mysql_monitor_commands_redis_channel, f"add {db_id}")

                    for db_id in to_remove:
                        await self.redis.publish(self.config.mysql_monitor_commands_redis_channel, f"remove {db_id}")

                await asyncio.sleep(300) # Reconcile every 5 minutes
            except Exception as e:
                print("Failed while syncing db ids to monitor from local db : ", e)
                traceback.print_exc()

    async def run(self):
        await asyncio.gather(
            self.process_requested_changes_in_monitoring(),
            self.sync_monitored_db_ids_periodically(),
        )


if __name__ == "__main__":
    monitor = MySQLHealthCheckMonitor()
    asyncio.run(monitor.run())
