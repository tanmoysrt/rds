import time

from generated.common_pb2 import ResponseMetadata, Status
from generated.proxysql_pb2 import ProxySQLInitResponse
from generated.proxysql_pb2_grpc import ProxySQLServiceServicer


class ProxySQLService(ProxySQLServiceServicer):
    def Start(self, request, context):
        time.sleep(1)
        return ProxySQLInitResponse(
            meta=ResponseMetadata(status=Status.SUCCESS),
            success=True,
            message="Hello from ProxySQLService.Start()",
        )
