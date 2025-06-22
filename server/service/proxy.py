
from generated.proxy_pb2 import (
    ProxyCreateRequest,
    ProxyDeleteResponse,
    ProxyIdRequest,
    ProxyInfoResponse,
    ProxyMonitorCredentialResponse,
    ProxyStatusResponse,
    ProxySyncUsersRequest,
    ProxySyncUsersResponse,
    ProxyUpgradeRequest,
)
from generated.proxy_pb2_grpc import ProxyServiceServicer
from server.domain.proxy import Proxy


def to_grpc_proxy_info(proxy: Proxy) -> ProxyInfoResponse:
    return ProxyInfoResponse(
        id=proxy.model.id,
        cluster_id=proxy.model.cluster_id,
        image=proxy.model.image,
        tag=proxy.model.tag,
        db_readwrite_port=proxy.db_readwrite_port,
        db_readonly_port=proxy.db_readonly_port,
        base_path=proxy.base_path,
        status=proxy.status.name,
    )

class ProxyService(ProxyServiceServicer):
    def Create(self, request:ProxyCreateRequest, context) -> ProxyInfoResponse:
        if request.base_path is None:
            raise ValueError("base_path is required")

        if request.cluster_id is None:
            raise ValueError("cluster_id is required")

        if request.etcd_username is None or request.etcd_password is None:
            raise ValueError("etcd_username and etcd_password are required")

        if request.id and Proxy.exists(request.id):
            raise ValueError(f"Proxy with id {request.id} already exists")

        return to_grpc_proxy_info(Proxy.create(
            service_id=request.id if request.HasField("id") else None,
            cluster_id=request.cluster_id,
            base_path=request.base_path,
            image=request.image if request.HasField("image") else "docker.io/proxysql/proxysql",
            tag=request.tag if request.HasField("tag") else "latest",
            db_readwrite_port=request.db_readwrite_port,
            db_readonly_port=request.db_readonly_port,
            etcd_username=request.etcd_username,
            etcd_password=request.etcd_password,
        ))

    def Get(self, request:ProxyIdRequest, context) -> ProxyInfoResponse:
        return to_grpc_proxy_info(Proxy(request.id))

    def Status(self, request:ProxyIdRequest, context) -> ProxyStatusResponse:
        proxy = Proxy(request.id)
        return ProxyStatusResponse(status=proxy.status.name)

    def Start(self, request:ProxyIdRequest, context) -> ProxyStatusResponse:
        proxy = Proxy(request.id)
        proxy.start()
        return ProxyStatusResponse(status=proxy.status.name)

    def Stop(self, request:ProxyIdRequest, context) -> ProxyStatusResponse:
        proxy = Proxy(request.id)
        proxy.stop()
        return ProxyStatusResponse(status=proxy.status.name)

    def Restart(self, request:ProxyIdRequest, context) -> ProxyStatusResponse:
        proxy = Proxy(request.id)
        proxy.restart()
        return ProxyStatusResponse(status=proxy.status.name)

    def Delete(self, request:ProxyIdRequest, context) -> ProxyDeleteResponse:
        proxy = Proxy(request.id)
        proxy.delete()
        return ProxyDeleteResponse(deleted=True)

    def GetMonitorCredential(self, request:ProxyIdRequest, context) -> ProxyMonitorCredentialResponse:
        proxy = Proxy(request.id)
        return ProxyMonitorCredentialResponse(username="monitor", password=proxy.monitor_password)

    def Upgrade(self, request:ProxyUpgradeRequest, context) -> ProxyInfoResponse:
        proxy = Proxy(request.id)
        proxy.update_version(image=request.image, tag=request.tag)
        return to_grpc_proxy_info(proxy)

    def SyncUsers(self, request:ProxySyncUsersRequest, context) -> ProxySyncUsersResponse:
        proxy = Proxy(request.id)
        added_users, removed_users, updated_users = proxy.sync_users()
        return ProxySyncUsersResponse(
            added_users=added_users,
            removed_users=removed_users,
            updated_users=updated_users
        )
