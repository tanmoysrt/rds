import traceback

import grpc
from google.protobuf.empty_pb2 import Empty
from podman import PodmanClient

from generated.inter_agent_pb2 import (
    RequestRsyncAccessRequest,
    RequestRsyncAccessResponse,
    RevokeRsyncAccessRequest,
)
from generated.inter_agent_pb2_grpc import InterAgentServiceServicer
from server import ServerConfig
from server.domain.mysql import MySQL
from server.helpers import find_available_port, generate_random_string


class InterAgentService(InterAgentServiceServicer):
    def RequestRsyncAccess(self, request:RequestRsyncAccessRequest, context) -> RequestRsyncAccessResponse:
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
            with PodmanClient() as client:
                client.containers.run(
                    name=rsync_container_id,
                    image=config.rsync_image,
                    remove=True,
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
        except Exception as e:
            print(str(e))
            traceback.print_exc()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Failed to create rsync container.")
            return RequestRsyncAccessResponse()

    def RevokeRsyncAccess(self, request:RevokeRsyncAccessRequest, context):
        if not request.instance_id.startswith( f"rsync.{request.cluster_id}."):
            context.set_code(grpc.StatusCode.PERMISSION_DENIED)
            context.set_details("Invalid instance ID or does not match the cluster and node.")
            return Empty()

        with PodmanClient() as client:
            # Check if the container exists
            if not client.containers.exists(request.instance_id):
                return Empty()

            # Force remove the container
            try:
                client.containers.remove(request.instance_id, force=True)
            except Exception as e:
                print(str(e))
                traceback.print_exc()
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Failed to remove rsync container")
        return Empty()
