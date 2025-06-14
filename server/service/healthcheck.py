from google.protobuf.empty_pb2 import Empty

from generated.healthcheck_pb2 import PingResponse
from generated.healthcheck_pb2_grpc import HealthCheckServiceServicer


class HealthCheckService(HealthCheckServiceServicer):
    def Ping(self, request:Empty, context) -> PingResponse:
        return PingResponse(success=True)
