from typing import Literal

import grpc

from generated.healthcheck_pb2_grpc import HealthCheckServiceStub
from generated.job_pb2_grpc import JobServiceStub
from generated.mysql_pb2_grpc import MySQLServiceStub
from generated.proxy_pb2_grpc import ProxyServiceStub


class Agent:
    def __init__(self, host: str, port: int, trusted_ca_path: str, token: str, com_type: Literal["direct", "cluster"] = "direct", cluster_id: str = None):
        """
        com_type: "direct" when control-plane wants to communicate with the agent directly, all the functions are allowed to be called.
                  "cluster" when one agent wants to communicate with another agent in same cluster, only a limited set of functions are allowed.
        """
        if com_type != "direct" and not cluster_id:
            raise ValueError("cluster_id must be provided when com_type is 'cluster'")

        self.host = host
        self.port = port
        self.trusted_ca_path = trusted_ca_path
        self.com_type = com_type
        self.cluster_id = cluster_id
        self.token = token
        self.channel = self._get_channel()

    @property
    def healthcheck_service(self) -> HealthCheckServiceStub:
        return HealthCheckServiceStub(self.channel)

    @property
    def inter_agent_rpc_service(self) -> HealthCheckServiceStub:
        """
        This service is used for inter-agent communication in a cluster.
        It allows agents to check the health of each other to help in automated failover and also to perform basic operations.
        """
        return HealthCheckServiceStub(self.channel)

    @property
    def job_service(self) -> JobServiceStub:
        return JobServiceStub(self.channel)

    @property
    def mysql_service(self) -> MySQLServiceStub:
        return MySQLServiceStub(self.channel)

    @property
    def proxy_service(self) -> ProxyServiceStub:
        return ProxyServiceStub(self.channel)

    def _get_channel(self):
        address = f"{self.host}:{self.port}"
        if self.trusted_ca_path:
            # TODO: cache the trusted CA certificates to avoid reading from disk every time
            with open(self.trusted_ca_path, 'rb') as f:
                trusted_certs = f.read()
            credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)
        else:
            credentials = grpc.ssl_channel_credentials()

        composite_credentials = grpc.composite_channel_credentials(
            credentials, self._get_token_credentials()
        )
        return grpc.secure_channel(address, composite_credentials)

    def _get_token_credentials(self):
        def metadata_callback(context, callback):
            if self.com_type == "direct":
                callback((('auth_token', f'{self.com_type}:{self.token}:'),), None)
            elif self.com_type == "cluster":
                callback((('auth_token', f'{self.com_type}:{self.token}:{self.cluster_id}'),), None)
        return grpc.metadata_call_credentials(metadata_callback)

    def __del__(self):
        if hasattr(self, "channel"):
            self.channel.close()
