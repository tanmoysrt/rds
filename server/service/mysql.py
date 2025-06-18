from generated.mysql_pb2 import (
    MySQLCreateRequest,
    MySQLDeleteResponse,
    MySQLIdRequest,
    MySQLInfoResponse,
    MySQLStatusResponse,
    MySQLUpgradeRequest,
)
from generated.mysql_pb2_grpc import MySQLServiceServicer
from server.domain.mysql import MySQL


def to_grpc_mysql_info(mysql: MySQL) -> MySQLInfoResponse:
    return MySQLInfoResponse(
        id=mysql.model.id,
        cluster_id=mysql.model.cluster_id,
        image=mysql.model.image,
        tag=mysql.model.tag,
        server_id=mysql.server_id,
        db_port=mysql.db_port,
        service=mysql.model.service,
        base_path=mysql.base_path,
        status=mysql.status.name,
    )

class MySQLService(MySQLServiceServicer):
    def Create(self, request:MySQLCreateRequest, context) -> MySQLInfoResponse:
        if request.base_path is None:
            raise ValueError("base_path is required")

        if request.cluster_id is None:
            raise ValueError("cluster_id is required")

        if request.etcd_username is None or request.etcd_password is None:
            raise ValueError("etcd_username and etcd_password are required")

        if request.id and MySQL.exists(request.id):
            raise ValueError(f"MySQL with id {request.id} already exists")

        return to_grpc_mysql_info(MySQL.create(
            service_id=request.id if request.HasField("id") else None,
            cluster_id=request.cluster_id,
            base_path=request.base_path,
            image=request.image if request.HasField("image") else "docker.io/mariadb",
            tag=request.tag if request.HasField("tag") else "latest",
            server_id=request.server_id if request.HasField("server_id") else None,
            db_port=request.db_port if request.HasField("db_port") else None,
            service=request.service,
            etcd_username=request.etcd_username,
            etcd_password=request.etcd_password,
        ))

    def Get(self, request:MySQLIdRequest, context) -> MySQLInfoResponse:
        return to_grpc_mysql_info(MySQL(request.id))

    def Status(self, request:MySQLIdRequest, context) -> MySQLStatusResponse:
        mysql = MySQL(request.id)
        return  MySQLStatusResponse(status=mysql.status.name)

    def Start(self, request:MySQLIdRequest, context) -> MySQLStatusResponse:
        mysql = MySQL(request.id)
        mysql.start()
        return  MySQLStatusResponse(status=mysql.status.name)

    def Stop(self, request:MySQLIdRequest, context) -> MySQLStatusResponse:
        mysql = MySQL(request.id)
        mysql.stop()
        return  MySQLStatusResponse(status=mysql.status.name)

    def Restart(self, request:MySQLIdRequest, context) -> MySQLStatusResponse:
        mysql = MySQL(request.id)
        mysql.restart()
        return  MySQLStatusResponse(status=mysql.status.name)

    def Delete(self, request:MySQLIdRequest, context) -> MySQLDeleteResponse:
        mysql = MySQL(request.id)
        mysql.delete()
        return MySQLDeleteResponse(deleted=True)

    def Upgrade(self, request:MySQLUpgradeRequest, context) -> MySQLInfoResponse:
        mysql = MySQL(request.id)
        mysql.update_version(image=request.image, tag=request.tag)
        return to_grpc_mysql_info(MySQL(request.id))
