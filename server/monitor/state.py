import asyncio
import contextlib
import datetime
import threading
import time
import traceback

from server import ServerConfig
from server.domain.mysql import MySQL
from server.domain.proxy import Proxy
from server.helpers import (
    KVEvent,
    get_working_etcd_cred_of_cluster,
    is_cluster_in_use,
    parse_etcd_watch_event,
)
from server.internal.etcd_client import Etcd3Client
from server.internal.scheduler import RQScheduler
from server.internal.utils import get_redis_client


class EtcdStateMonitor:
    """
    This will monitor the state changes in etcd
    In most of the cases, it will push update in redis pubsub
    Or, trigger some actions based on the state changes

    It's better to keep the actions outside of this class
    """

    def __init__(self):
        self.config = ServerConfig()
        self.redis = get_redis_client(async_client=True)
        self.sync_db_ids_lock = asyncio.Lock()
        self.stop_events: dict[str, threading.Event] = {}
        self.watch_threads: dict[str, threading.Thread] = {}

    def act_on_kv_event(self, cluster_id:str, event:KVEvent):
        try:
            # 1: Auto sync backend servers for all proxies
            if event.action == "update" and event.event_type == "config" and event.data:
                print(Proxy.sync_backend_servers_for_all_proxies(cluster_id=cluster_id, config=event.data))
        except:
            print(f"Error while acting on config change for cluster {cluster_id}: {event}")
            traceback.print_exc()

    def monitor_cluster_state(self, cluster_id:str):

        """
        Multiple service can be part of a single cluster
        Rather than monitoring for each service, spawn a single listener for the cluster

        Now, we can have multiple credentials due to multiple services in a cluster
        All the credentials will be valid most of the time, but during removing db from current server,
        that credential will be deactivated.

        In that case, we should fetch latest credentials and try them one by one.
        """
        stop_event = self.stop_events[cluster_id]

        username = None
        password = None

        while not stop_event.is_set():
            try:
                if not username or not password:
                    username, password = get_working_etcd_cred_of_cluster(cluster_id)

                with Etcd3Client(
                    addresses=[f"{self.config.etcd_host}:{self.config.etcd_port}"],
                    user=username,
                    password=password,
                    timeout=10,
                ) as client:
                    events_iterator, cancel = client.watch_prefix(
                        self.config.kv_cluster_prefix.format(cluster_id=cluster_id)
                    )
                    for event in events_iterator:
                        if stop_event.is_set():
                            cancel()
                            break

                        parsed_event = parse_etcd_watch_event(event)
                        # Blocking call
                        self.act_on_kv_event(cluster_id, parsed_event)
            except Exception as e:
                print(f"[{cluster_id}] watch error: {e}")
                username = None
                password = None
                time.sleep(5)


    def add_cluster_to_monitoring(self, cluster_id:str):
        if cluster_id in self.watch_threads:
            return

        event = threading.Event()
        self.stop_events[cluster_id] = event

        thread = threading.Thread(target=self.monitor_cluster_state, args=(cluster_id,), daemon=True)
        self.watch_threads[cluster_id] = thread
        thread.start()

    def remove_cluster_from_monitoring(self, cluster_id:str):
        event = self.stop_events.pop(cluster_id, None)
        thread = self.watch_threads.pop(cluster_id, None)

        if event:
            event.set()
        if thread:
            thread.join(timeout=5)

    def add_service_to_monitoring(self, db_id:str):
        db = MySQL(db_id)
        self.add_cluster_to_monitoring(db.model.cluster_id)

    def remove_service_from_monitoring(self, db_id:str):
        # Check if we have any other services in the same cluster
        db = MySQL(db_id)
        if is_cluster_in_use(db.model.cluster_id):
            # Other service can still use the cluster
            # If there is no other service, then we can remove the cluster from monitoring
            return
        self.remove_cluster_from_monitoring(db.model.cluster_id)

    async def process_requested_changes_in_monitoring(self):
        while True:
            try:
                pubsub = self.redis.pubsub()
                await pubsub.subscribe(self.config.etcd_monitor_commands_redis_channel)
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
                                self.remove_service_from_monitoring(db_id)

                            if cmd in ["add", "reload"]:
                                self.add_service_to_monitoring(db_id)
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
                    current_monitoring = set(self.watch_threads.keys())

                    to_add = db_ids - current_monitoring
                    to_remove = current_monitoring - db_ids

                    for db_id in to_add:
                        await self.redis.publish(
                            self.config.etcd_monitor_commands_redis_channel, f"add {db_id}"
                        )

                    for db_id in to_remove:
                        await self.redis.publish(
                            self.config.etcd_monitor_commands_redis_channel, f"remove {db_id}"
                        )

                await asyncio.sleep(300)  # Reconcile every 5 minutes
            except Exception as e:
                print("Failed while syncing db ids to monitor from local db : ", e)
                traceback.print_exc()


    async def run(self):
        await asyncio.gather(
            self.process_requested_changes_in_monitoring(),
            self.sync_monitored_db_ids_periodically()
        )

    def schedule_auto_sync_proxysql_users(self):
        job_id = "auto_sync_proxies_users"
        # Remove the job if it already exists
        with contextlib.suppress(Exception):
            RQScheduler.cancel(job_id)
        # Schedule the job to sync users for all proxies
        RQScheduler.schedule(
            scheduled_time=datetime.datetime.now(datetime.timezone.utc),
            func=Proxy.sync_users_for_all_proxies,
            interval=300, # Sync every 5 minutes
            repeat=None, # Repeat indefinitely
            id=job_id,
        )

    def schedule_auto_sync_proxysql_backend_servers(self):
        job_id = "auto_sync_proxies_backend_servers"
        # Remove the job if it already exists
        with contextlib.suppress(Exception):
            RQScheduler.cancel(job_id)
        # Schedule the job to sync backend servers for all proxies
        RQScheduler.schedule(
            scheduled_time=datetime.datetime.now(datetime.timezone.utc),
            func=Proxy.sync_backend_servers_for_all_proxies,
            interval=1800, # Sync every 30 minutes
            repeat=None, # Repeat indefinitely
            id=job_id,
        )



if __name__ == "__main__":
    monitor = EtcdStateMonitor()
    # Schedule periodic tasks
    monitor.schedule_auto_sync_proxysql_backend_servers()
    monitor.schedule_auto_sync_proxysql_users()
    # Run the monitor
    asyncio.run(monitor.run())
