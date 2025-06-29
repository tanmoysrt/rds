import traceback

import grpc
from google.protobuf.empty_pb2 import Empty

from generated.inter_agent_pb2 import (
    CheckDatabaseReachabilityRequest,
    CheckDatabaseReachabilityResponse,
    RequestRsyncAccessRequest,
    RequestRsyncAccessResponse,
    RevokeRsyncAccessRequest,
    SyncReplicationUserRequest,
)
from generated.inter_agent_pb2_grpc import InterAgentServiceServicer
from agent import ServerConfig
from agent.domain.mysql import MySQL
from agent.helpers import (
    find_available_port,
    generate_random_string,
    get_db_client_from_cluster_config,
    get_working_etcd_cred_of_cluster,
)
from agent.internal.config import ClusterConfig


class InterAgentService(InterAgentServiceServicer):
    def RequestRsyncAccess(self, request:RequestRsyncAccessRequest, context) -> RequestRsyncAccessResponse:
        from podman import PodmanClient

        node = MySQL(request.node_id)
        if node.model.cluster_id != request.cluster_id:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details("Node does not belong to the specified cluster.")
            return RequestRsyncAccessResponse()

        random_id = generate_random_string(length=16)
        rsync_container_id = f"rsync.{request.cluster_id}.{request.node_id}.{random_id}"

        config = ServerConfig()
        port = find_available_port(start_port=20000, end_port=25000)
        username = generate_random_string(length=32)
        password = generate_random_string(length=32)

        try:
            with PodmanClient.from_env() as client:
                client.containers.run(
                    name=rsync_container_id,
                    image=config.rsync_image,
                    detach=True,
                    mounts=[{
                        "type": "bind",
                        "source": node.data_path,
                        "target": "/data"
                    }],
                    ports={
                        "2222/tcp": port
                    },
                    environment={
                        "SSH_PORT": "2222",
                        "USER_UID": str(config.rsync_default_uid),
                        "USER_GID": str(config.rsync_default_gid),
                        "USER_NAME": username,
                        "USER_PASSWORD": password
                    }
                )

            return RequestRsyncAccessResponse(
                instance_id=rsync_container_id,
                port=port,
                username=username,
                password=password,
                src_path="/data"
            )
        except Exception:
            traceback.print_exc()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to create rsync container.")
            return RequestRsyncAccessResponse()

    def RevokeRsyncAccess(self, request:RevokeRsyncAccessRequest, context):
        from podman import PodmanClient
        from podman.errors.exceptions import NotFound as PodmanNotFound

        if not request.instance_id.startswith( f"rsync.{request.cluster_id}."):
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details("Invalid instance ID or does not match the cluster and node.")
            return Empty()

        with PodmanClient.from_env() as client:
            # Check if the container exists
            if not client.containers.exists(request.instance_id):
                return Empty()

            # Force remove the container
            try:
                client.containers.remove(request.instance_id, force=True)
            except PodmanNotFound:
                return Empty()
            except Exception:
                traceback.print_exc()
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to remove rsync container")

        return Empty()

    def SyncReplicationUser(self, request:SyncReplicationUserRequest, context):
        mysql = MySQL(request.node_id)
        if mysql.model.cluster_id != request.cluster_id:
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details("Node does not belong to the specified cluster.")
            return Empty()
        mysql.sync_replica_user()
        return Empty()

    def CheckDatabaseReachability(self, request:CheckDatabaseReachabilityRequest, context) -> CheckDatabaseReachabilityResponse:
        from agent.internal.etcd_client import Etcd3Client

        server_config = ServerConfig()
        try:
            username, password = get_working_etcd_cred_of_cluster(request.cluster_id)
            config = ClusterConfig(etcd_client=Etcd3Client(
                addresses=[f"{server_config.etcd_host}:{server_config.etcd_port}"],
                user=username,
                password=password,
                timeout=2
            ), cluster_id=request.cluster_id)

            # Check if node_id exists in the cluster
            if request.node_id not in config.node_ids:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Node ID {request.node_id} not found in cluster {request.cluster_id}.")
                return CheckDatabaseReachabilityResponse(reachable=False)

            # Try to connect to the database
            db_client = get_db_client_from_cluster_config(config, request.node_id, timeout=5)
            return CheckDatabaseReachabilityResponse(reachable=db_client.is_reachable())
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to check database reachability: {e!s}")
            return CheckDatabaseReachabilityResponse(reachable=False)
