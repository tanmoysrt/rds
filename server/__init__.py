import os

from server.internal.config import ServerConfig

config = ServerConfig()
config._base_path = os.getcwd()

config.grpc_port = 50051
config.redis_port = 6379
config.generated_protobuf_dir = "generated"
config.service_impl_dir = "server/service"
config.job_update_stream_redis_channel = "job_update_stream"
