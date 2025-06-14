from concurrent import futures

import grpc

from server.internal.interceptors import AsyncJobInterceptor
from server.internal.proto_utils import (
    discover_grpc_service_impls,
    discover_protobuf_messages,
    discover_protobuf_messages_with_meta,
)


def init_server() -> grpc.Server:
    messages = discover_protobuf_messages()
    messages_with_meta = discover_protobuf_messages_with_meta()
    service_impls = discover_grpc_service_impls()

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[
            AsyncJobInterceptor(
                protobuf_messages=messages,
                protobuf_messages_with_meta=messages_with_meta,
                service_impls=service_impls,
            )
        ],
    )

    # Register all protobuf messages
    for service_name, impl in service_impls.items():
        impl.adapter(impl.class_obj(), server)

    return server
