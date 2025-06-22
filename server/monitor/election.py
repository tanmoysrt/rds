from client import Agent
from generated.extras_pb2 import DBHealthStatus
from generated.inter_agent_pb2 import CheckDatabaseReachabilityRequest, CheckDatabaseReachabilityResponse
from server.helpers import get_working_etcd_cred_of_cluster
from server.internal.bg_job.job import queue
from server.internal.config import ClusterConfig, ServerConfig
from server.internal.etcd_client import Etcd3Client


class NodeElection:
    """
    If master node goes down, the nodes can do election to chose most capable node as new master

    To do election, only a single node should initiate the election process.
    If it can't do the election, leave it, some other node will do it.

    When some node marked as offline, it has been already checked by other nodes that it is not reachable.
    So, it is safe to do election.

    Rules -
    1. Check once more if the node is reachable by the proxy node -- sanity check
    2. Fetch the eligible nodes which can become master (Only replica nodes can become master)
    3. Remove nodes which has outdated gtid than the current master node.
    4. Sort the nodes by their weight (weight is set by controlplane in config, should be linked with some cpu/memory/disk resource quota)
    5. Chose the most appropriate node
    6. Check with proxy node if future master node is reachable
    7. Switch the master node in cluster config
    8. Mark the old master node as replica in cluster config

    During this process -
    Hold the election lock in etcd to avoid multiple nodes doing election at the same time.
    """

    def elect_new_master_if_required(self, cluster_id:str, config:ClusterConfig):
        if len(config.online_master_node_ids)> 0:
            return

        queue().enqueue(
            self._elect_new_master,
            cluster_id,
        )

    def _elect_new_master(self, cluster_id:str):
        print("Electing new master for cluster:", cluster_id)
        username, password = get_working_etcd_cred_of_cluster(cluster_id)
        server_config = ServerConfig()
        etcd_client = Etcd3Client(
            addresses=[f"{server_config.etcd_host}:{server_config.etcd_port}"],
            user=username,
            password=password,
        )
        cluster_config = ClusterConfig(etcd_client, cluster_id)
        if len(cluster_config.online_master_node_ids) > 0:
            return

        if len(cluster_config.offline_master_node_ids) == 0:
            return

        offline_master_node_id = cluster_config.offline_master_node_ids[0]

        # 1:  Ask proxy to check the reachability of the current master node
        proxy = cluster_config.proxy
        proxy_agent =  Agent(
            host=proxy.ip,
            port=proxy.agent_port,
            trusted_ca_path=ServerConfig().grpc_ca_path,
            token=cluster_config.shared_token,
            com_type="cluster",
            cluster_id=cluster_id
        )

        print("Checking reachability of offline master node:", offline_master_node_id)
        reachability_response_from_proxy:CheckDatabaseReachabilityResponse = proxy_agent.inter_agent_service.CheckDatabaseReachability(
            CheckDatabaseReachabilityRequest(
                cluster_id=cluster_id,
                node_id=offline_master_node_id
            )
        )
        if reachability_response_from_proxy.reachable:
            # No need to do anything
            # The node will soon mark itself as online
            return

        lock = etcd_client.lock(server_config.kv_cluster_election_lock_key.format(cluster_id=cluster_id), ttl=1800)

        print("Acquiring election lock for cluster:", cluster_id)
        if not lock.acquire(timeout=20):
            # If fail to acquire the lock, it means some other node is already doing the election
            # so, just put the job in queue and return
            self.elect_new_master_if_required(cluster_id, cluster_config)

        print("Election lock acquired for cluster:", cluster_id)
        try:
            # 2: Fetch eligible nodes which can become master
            eligible_nodes = cluster_config.online_replica_node_ids
            if not eligible_nodes:
                print(f"No eligible nodes to become master in cluster {cluster_id}.")
                return

            # 3. Fetch all nodes latest broadcasted status
            node_status: dict[str, DBHealthStatus] = {}

            for node_id in eligible_nodes + [offline_master_node_id]:
                node_status_key = server_config.kv_cluster_node_status_key.format(
                    cluster_id=cluster_id, node_id=node_id
                )
                status_data, _ = etcd_client.get(node_status_key)
                if status_data:
                    node_status[node_id] = DBHealthStatus.FromString(status_data)

            if offline_master_node_id not in node_status:
                """
                If we don't have the status of the offline master node,
                Then we can't take any action automatically
                """
                return

            master_node_gtid = node_status[offline_master_node_id].global_transaction_id

            # 4. Remove nodes which has outdated gtid than the current master node.
            eligible_nodes = [
                node_id
                for node_id in eligible_nodes
                if compare_gtid(node_status[node_id].global_transaction_id, master_node_gtid) >= 0
            ]

            # 5. Sort the nodes by their weight in descending order
            eligible_nodes.sort(
                key=lambda node_id: cluster_config.get_node(node_id).weight, reverse=True
            )

            # 6. Keep trying to check reachability of the most eligible nodes one by one
            elected_master_id = None
            for node_id in eligible_nodes:
                reachability_response_from_proxy: CheckDatabaseReachabilityResponse = (
                    proxy_agent.inter_agent_service.CheckDatabaseReachability(
                        CheckDatabaseReachabilityRequest(cluster_id=cluster_id, node_id=node_id)
                    )
                )
                if reachability_response_from_proxy.reachable:
                    elected_master_id = node_id
                    break

            if not elected_master_id:
                # Found no eligible node which is reachable
                # TODO: this updates should reach control-plane
                return

            # 7. Use transaction to switch the master node in cluster config
            cluster_config.reload()
            # Check once more if no master node is online
            if len(cluster_config.online_master_node_ids) > 0:
                return

            old_version = cluster_config.version
            # Try updating the cluster config only if we have a new master node
            txn_success, _ = etcd_client.transaction(
                compare=[
                    etcd_client.transactions.version(cluster_config.kv_cluster_config_key)
                    == old_version
                ],
                success=[
                    etcd_client.transactions.put(
                        cluster_config.kv_cluster_config_key,
                        cluster_config.copy_and_switch_master_replica(
                            elected_master_id, offline_master_node_id
                        ).SerializeToString(),
                    )
                ],
                failure=[],
            )
            if txn_success:
                print(f"New master node elected: {elected_master_id} in cluster {cluster_id}")
            else:
                print(
                    "Failed to elect new master node due to concurrent modification of cluster config."
                )
        finally:
            lock.release()

def compare_gtid(gtid_a: str, gtid_b: str) -> int:
        """
        Compare two GTIDs.
        Returns:
            -1 if gtid1 < gtid2
             0 if gtid1 == gtid2
             1 if gtid1 > gtid2
        """

        gtid1_parts = gtid_a.split('-')
        gtid2_parts = gtid_b.split('-')

        if len(gtid1_parts) != 3 or len(gtid2_parts) != 3:
            return -1

        # If 2nd pos value is different, then return -1
        if gtid1_parts[1] != gtid2_parts[1]:
            return -1 if gtid1_parts[1] < gtid2_parts[1] else 1

        # Compare the third part (sequence number)
        try:
            gtid1_seq = int(gtid1_parts[2])
            gtid2_seq = int(gtid2_parts[2])
            if gtid1_seq < gtid2_seq:
                return -1
            if gtid1_seq > gtid2_seq:
                return 1
            return 0
        except ValueError:
            return -1  # If conversion fails, treat as less than
