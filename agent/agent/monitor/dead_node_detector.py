import heapq
import threading
import time

from generated.extras_pb2 import DBHealthStatus
from agent.monitor.dead_node_handler import handle_dead_node


class DeadNodeDetector:
    def __init__(self, timeout_seconds):
        self.timeout_seconds = timeout_seconds
        self.last_seen = {}
        self.heap = []
        self.dead = set()
        self.dead_node_handling_failed = set()
        self.lock = threading.Lock()

        # Start monitoring in a separate thread
        threading.Thread(target=self.monitor_loop, daemon=True).start()
        threading.Thread(target=self.retry_failed_dead_node_handling_loop, daemon=True).start()


    def update(self, node_id:str, health_status:DBHealthStatus):
        # TODO: consider gtid also. take that into account for node failure detection
        # TODO: + consider the reporting time of the health status
        with self.lock:
            """
            In case of using report
            """
            now = time.time()
            self.last_seen[node_id] = now
            heapq.heappush(self.heap, (now + self.timeout_seconds, node_id))
            if node_id in self.dead:
                self.dead.remove(node_id)
                self.dead_node_handling_failed.discard(node_id)
                print(f"[RECOVERED] {node_id} at {now:.2f}")

    def _handle_dead_node(self, node_id:str):
        try:
            if node_id not in self.dead:
                return
            handle_dead_node(node_id)
        except Exception as e:
            print(f"[ERROR] {node_id}: {e}")

    def monitor_loop(self):
        while True:
            time.sleep(1)
            now = time.time()
            with self.lock:
                while self.heap and self.heap[0][0] <= now:
                    expire_time, node_id = heapq.heappop(self.heap)
                    last = self.last_seen.get(node_id, 0)
                    if last <= now - self.timeout_seconds and node_id not in self.dead:
                        self.dead.add(node_id)
                        # Open a new thread and call the handle_dead_node function
                        threading.Thread(target=self._handle_dead_node, args=(node_id,), daemon=True).start()


    def retry_failed_dead_node_handling_loop(self):
        time.sleep(30)
        for node_id in list(self.dead_node_handling_failed):
            threading.Thread(target=self._handle_dead_node, args=(node_id,), daemon=True).start()
