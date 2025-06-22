import hashlib
import traceback

import grpc

from generated.common_pb2 import ResponseMetadata, Status
from server import ServerConfig
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
                is_request_message_support_meta = request_message_type in self.protobuf_messages_with_meta
                is_response_message_support_meta = response_message_type in self.protobuf_messages_with_meta

                # If is_async tag is found in metadata
                # Then verify, if both request and response message types for async job
                # Create a job and return a response with metadata
                if (
                        service != "InterAgentService" and # This is to avoid creating jobs for inter-agent RPCs by mistake
                        hasattr(request, "meta") and
                        getattr(request.meta, "is_async", False) and
                        is_request_message_support_meta and
                        is_response_message_support_meta
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
                        timeout=metadata.timeout_seconds if metadata.HasField("timeout") else None,
                    )
                    return job.grpc_response

                try:
                    response = original_handler(request, context)
                    if is_response_message_support_meta and (
                        not hasattr(response, "meta")
                        or response.meta.status == 0
                    ):
                        response.meta.CopyFrom(ResponseMetadata(
                            status=Status.SUCCESS
                        ))
                    return response
                except grpc.RpcError as e:
                    # Don't handle RpcError here, let it propagate
                    raise e
                except Exception as e:
                    if is_response_message_support_meta:
                        return self.protobuf_messages[response_message_type](
                            meta=ResponseMetadata(
                                status=Status.FAILURE,
                                error_message=str(e),
                                traceback=traceback.format_exc(),
                            )
                        )
                    raise e

            return grpc.unary_unary_rpc_method_handler(
                new_handler,
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler


class AuthTokenValidatorInterceptor(grpc.ServerInterceptor):
    def __init__(self, config: ServerConfig):
        super().__init__()
        self.config = config

    def intercept_service(self, continuation, handler_call_details):
        """
        'direct' users can call any function, but 'cluster' users can only call rds.InterAgentService functions.
        """
        handler = continuation(handler_call_details)
        if handler is None:
            return None

        metadata = dict(handler_call_details.invocation_metadata or [])
        auth_token = metadata.get('auth_token')
        try:
            _, service, _ = handler_call_details.method.split("/")

            # Split it and check the src_type and target
            src_type, token, cluster_id = auth_token.split(':', 2)
            if not src_type or not token or src_type not in ['direct', 'cluster']:
                raise ValueError("Invalid auth_token format")

            # cluster type can't be used for calling any function other than rds.InterAgentService
            if src_type == "cluster" and service != "rds.InterAgentService":
                raise ValueError("Cluster auth_token can only be used for rds.InterAgentService")

            # cluster type should have a valid cluster_id
            if src_type == "cluster" and not cluster_id:
                raise ValueError("Cluster auth_token must include a cluster_id")

            # In inter-agent cluster communication, only unary methods are allowed
            if src_type == "cluster" and not handler.unary_unary:
                raise ValueError("Cluster auth_token can only be used for unary methods")

            # Validate auth token
            if src_type == "direct" and hashlib.sha256(token.encode()).hexdigest() != self.config.auth_token_hash:
                raise ValueError("Invalid auth_token")

            if src_type == "cluster":
                if cluster_id not in self.config.cluster_shared_token:
                    raise ValueError("Invalid cluster_id in auth_token")
                if token != self.config.cluster_shared_token[cluster_id]:
                    raise ValueError("Invalid auth_token for the given cluster_id")

            # Add `cluster_id` to the request (If required)
            if src_type == "cluster":
                def new_handler(request, context):
                    request.cluster_id = cluster_id
                    return handler.unary_unary(request, context)
                return grpc.unary_unary_rpc_method_handler(
                    new_handler,
                    request_deserializer=handler.request_deserializer,
                    response_serializer=handler.response_serializer
                )
            if src_type == "direct":
                def new_handler(request, context):
                    if (src_type == "direct" and
                            service == "rds.InterAgentService" and
                            not (hasattr(request, "cluster_id") or request.cluster_id)
                    ):
                        raise ValueError("To access rds.InterAgentService from control node, please include cluster_id in request")

                    return handler.unary_unary(request, context)
                return grpc.unary_unary_rpc_method_handler(
                    new_handler,
                    request_deserializer=handler.request_deserializer,
                    response_serializer=handler.response_serializer
                )
            raise ValueError("Invalid src_type")
        except ValueError as e:
            message = str(e) or 'Invalid auth_token format'
            def abort_handler(request, context, message=message):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, message)
            return grpc.unary_unary_rpc_method_handler(abort_handler)

