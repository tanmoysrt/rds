from concurrent import futures

import grpc

from server import ServerConfig
from server.internal.interceptors import AsyncJobInterceptor, AuthTokenValidatorInterceptor
from server.internal.proto_utils import (
    discover_grpc_service_impls,
    discover_protobuf_messages,
    discover_protobuf_messages_with_meta,
)


def init_server() -> grpc.Server:
    messages = discover_protobuf_messages()
    messages_with_meta = discover_protobuf_messages_with_meta()
    service_impls = discover_grpc_service_impls()

    config = ServerConfig()
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[
            AuthTokenValidatorInterceptor(config=config),
            AsyncJobInterceptor(
                protobuf_messages=messages,
                protobuf_messages_with_meta=messages_with_meta,
                service_impls=service_impls,
            ),
        ],
    )

    # Register all protobuf messages
    for service_name, impl in service_impls.items():
        impl.adapter(impl.class_obj(), server)

    # Add SSL credentials if cert and key are provided
    if config.grpc_cert_path and config.grpc_key_path:
        with open(config.grpc_cert_path, 'rb') as f:
            server_cert = f.read()
        with open(config.grpc_key_path, 'rb') as f:
            private_key = f.read()
        with open(config.grpc_ca_path, "rb") as f:
            ca_cert = f.read()
        creds = grpc.ssl_server_credentials([(private_key, server_cert)], root_certificates=ca_cert)
        server.add_secure_port(f'[::]:{config.grpc_port}', creds)
    else:
        server.add_insecure_port(f'[::]:{config.grpc_port}')

    return server
