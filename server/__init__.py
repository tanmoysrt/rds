import os

from server.internal.config import ServerConfig

# Development configuration

config = ServerConfig()
base_path = os.getcwd()
config._base_path = base_path

config.grpc_port = 50051
config.redis_port = 6379
config.generated_protobuf_dir = "generated"
config.service_impl_dir = "server/service"
config.etcd_host = os.getenv("ETCD_HOST")
config.etcd_port = 2379

config.auth_token_hash = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08" # test
config.grpc_key_path = os.path.join(base_path, "./certs/server.key.pem")
config.grpc_cert_path = os.path.join(base_path,"./certs/server.cert.pem")
config.grpc_ca_path = os.path.join(base_path, "./certs/ca.cert.pem")
