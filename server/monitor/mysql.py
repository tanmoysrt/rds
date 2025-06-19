import asyncio
import time
import traceback
from concurrent.futures.thread import ThreadPoolExecutor

from generated.extras_pb2 import DBHealthStatus
from server import ServerConfig
from server.domain.mysql import MySQL
from server.internal.utils import get_redis_client


class MySQLHealthCheckMonitor:
    def __init__(self):
        self.config = ServerConfig()
        self.tasks: dict[str, asyncio.Task] = {}
        self.tasks_lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor(max_workers=50)
        self.redis = get_redis_client(async_client=True)
        self.sync_db_ids_lock = asyncio.Lock()

    async def monitor_db_health(self, db_id:str):
        loop = asyncio.get_running_loop()
        db_record = MySQL(db_id)
        while True:
            start = time.time()
            try:
                result: tuple[bool, DBHealthStatus] = await loop.run_in_executor(
                    self.executor,
                    db_record.get_health_info
                )
                success, health_info = result
                if not success:
                    print(f"[{db_id}] Health check failed, will check later")
                else:
                    db_record.kv.put(db_record.kv_cluster_node_status_key, health_info.SerializeToString())
            except Exception as e:
                print(f"[{db_id}] Health check failed for unknown reason: {e}")
                traceback.print_exc()
            finally:
                end = time.time()
                elapsed_ms = int((end - start)*1000)
                wait_time = max(0, (self.config.db_healthcheck_interval_ms - elapsed_ms))
                wait_time = max(wait_time, self.config.db_healthcheck_minimum_interval_ms)
                await asyncio.sleep(wait_time/1000)  # Convert ms to seconds

    async def add_db(self, db_id:str):
        async with self.tasks_lock:
            if db_id in self.tasks:
                return
            if not MySQL.exists(db_id):
                return
            task = asyncio.create_task(self.monitor_db_health(db_id))
            self.tasks[db_id] = task

    async def remove_db(self, db_id:str):
        async with self.tasks_lock:
            if db_id not in self.tasks:
                return
            self.tasks[db_id].cancel()
            try:
                await self.tasks[db_id]
            except asyncio.CancelledError:
                pass
            del self.tasks[db_id]

    async def process_requested_changes(self):
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
                                await self.remove_db(db_id)

                            if cmd in ["add", "reload"]:
                                await self.add_db(db_id)
                    except Exception as e:
                        print("Command handling error:", e)
                        traceback.print_exc()
            except Exception as e:
                print("Redis connection failed, retrying in 5s...", e)
                traceback.print_exc()
                await asyncio.sleep(5)

    async def sync_monitored_db_ids(self):
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
            self.process_requested_changes(),
            self.sync_monitored_db_ids(),
        )


if __name__ == "__main__":
    monitor = MySQLHealthCheckMonitor()
    asyncio.run(monitor.run())
