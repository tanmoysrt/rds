import contextlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from generated.inter_agent_pb2 import CheckDatabaseReachabilityRequest, CheckDatabaseReachabilityResponse
from server.domain.mysql import MySQL
from server.internal.config import ClusterConfig


def handle_dead_node(node_id:str):
    """
    This function needs to verify whether the node is actually dead
    If it's dead just mark it as offline and handle it accordingly.

    Verification Flow (If at any step it starts working, assume that the node is healthy)-
    1. Ask proxy node to check if the node is reachable
    2. Then ask self + all other nodes to check if the node is reachable
    3. If all checks fail, then mark the node as dead and update cluster config
    """
    db = MySQL(node_id)
    cluster_config = ClusterConfig(etcd_client=db.kv, cluster_id=db.model.cluster_id)

    # 1. Ask proxy node to check if the node is reachable
    proxy_agent = db.get_agent_for_proxy()
    reachability_response_from_proxy:CheckDatabaseReachabilityResponse = proxy_agent.inter_agent_service.CheckDatabaseReachability(
        CheckDatabaseReachabilityRequest(
            cluster_id=db.model.cluster_id,
            node_id=node_id
        )
    )
    if reachability_response_from_proxy.reachable:
        return

    # 2. Ask all other online nodes to check if the node is reachable
    no_of_nodes_reachable = 0
    node_ids = cluster_config.online_master_node_ids + cluster_config.online_replica_node_ids + cluster_config.online_read_only_node_ids
    # Remove `node_id` from the list to avoid hitting itself
    node_ids = [nid for nid in node_ids if nid != node_id]
    no_of_nodes_for_win = len(node_ids) * 0.6

    def check_node_reachability(other_node_id) -> bool:
        agent = db.get_agent_for_node(other_node_id)
        reachability_response: CheckDatabaseReachabilityResponse = agent.inter_agent_service.CheckDatabaseReachability(
            CheckDatabaseReachabilityRequest(
                cluster_id=db.model.cluster_id,
                node_id=node_id
            )
        )
        return reachability_response.reachable

    with ThreadPoolExecutor() as executor:
        future_to_node = {executor.submit(check_node_reachability, other_node_id): other_node_id for other_node_id in node_ids}
        for future in as_completed(future_to_node):
            with contextlib.suppress(Exception):
                if future.result():
                    no_of_nodes_reachable = no_of_nodes_reachable + 1
                    if no_of_nodes_for_win > no_of_nodes_reachable:
                        print(f"Node {node_id} is reachable by by 60% of nodes, not marking it as dead.")
                        return

    # If more than 60% node says the node is dead, then mark it as dead
    if no_of_nodes_reachable < (len(node_ids) * 0.6):
        etcd_client = db.kv
        old_version = cluster_config.version

        txn_success, _  = etcd_client.transaction(
            compare=[
                etcd_client.transactions.version(cluster_config.kv_cluster_config_key) == old_version
            ],
            success=[
                etcd_client.transactions.put(
                    cluster_config.kv_cluster_config_key,
                    cluster_config.copy_and_mark_node_as_offline(node_id).SerializeToString()
                )
            ],
            failure=[]
        )

        if txn_success:
            print(f"Config updated successfully, marking {node_id} as dead.")
        else:
            print("Update failed. key changed in between.")
    else:
        print(f"Node {node_id} is reachable by some nodes, not marking it as dead.")
