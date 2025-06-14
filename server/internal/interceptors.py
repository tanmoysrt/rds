

import grpc

from server.internal.bg_job.utils import create_job
from server.internal.db.models import JobModel
from server.internal.proto_utils import ServiceImplInfo


class AsyncJobInterceptor(grpc.ServerInterceptor):
    def __init__(self, protobuf_messages: dict[str, type], protobuf_messages_with_meta: set[str], service_impls: dict[str, ServiceImplInfo]):
        super().__init__()
        self.protobuf_messages = protobuf_messages
        self.protobuf_messages_with_meta = protobuf_messages_with_meta
        self.service_impls = service_impls

    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler is None:
            return None

        if handler.unary_unary:
            original_handler = handler.unary_unary
            _, service, method = handler_call_details.method.split("/")

            def new_handler(request, context):
                request_message_type = f"{request.__class__.__module__}.{request.__class__.__name__}"
                response_message_type = self.service_impls[service].method_response_types[method]
                # If is_async tag is found in metadata
                # Then verify, if both request and response message types for async job
                # Create a job and return a response with metadata
                if (
                        hasattr(request, "meta") and
                        getattr(request.meta, "is_async", False) and
                        request_message_type in self.protobuf_messages_with_meta and
                        response_message_type in self.protobuf_messages_with_meta
                ):
                    metadata = request.meta
                    job:JobModel = create_job(
                        service,
                        method,
                        request_message_type,
                        request.SerializeToString(),
                        response_message_type,
                        ref=metadata.ref if metadata.HasField("ref") else None,
                        scheduled_at=metadata.scheduled_at.ToDatetime() if metadata.HasField("scheduled_at") else None,
                        timeout=metadata.timeout if metadata.HasField("timeout") else None,
                    )
                    return job.grpc_response
                return original_handler(request, context)

            return grpc.unary_unary_rpc_method_handler(
                new_handler,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler
