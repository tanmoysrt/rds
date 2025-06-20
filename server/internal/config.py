import json
import os

from filelock import FileLock


class ServerConfig:
    _instance = None

    _config_file = "config.json"
    _config_file_lock = "config.lock"
    _base_path:str

    redis_port:int
    generated_protobuf_dir:str
    service_impl_dir:str

    # grpc related
    auth_token_hash:str
    grpc_port:int
    grpc_ca_path:str = None
    grpc_cert_path:str = None
    grpc_key_path:str = None

    # pubsub channels
    job_update_stream_redis_channel:str = "job_update_stream"
    mysql_monitor_commands_redis_channel:str = "mysql_monitor_commands"

    db_healthcheck_interval_ms:int = 250 # Healthcheck interval in milliseconds
    db_healthcheck_minimum_interval_ms:int = 100

    # default docker images
    rsync_image:str = "tanmoysrt/sshd:latest"
    rsync_default_uid:int = 1000
    rsync_default_gid:int = 1000

    # etcd cluster information
    etcd_host:str
    etcd_port:int = 2379
    cluster_shared_token:dict = {} # cluster_id -> token mapping

    # kv keys
    kv_cluster_config_key:str = "/cluster/{cluster_id}/config"
    kv_cluster_current_master_key:str = "/cluster/{cluster_id}/master"
    kv_cluster_election_lock_key:str = "/cluster/{cluster_id}/election/lock"
    kv_cluster_node_status_key:str = "/cluster/{cluster_id}/node/{node_id}/status"
    kv_cluster_node_cluster_state_key:str = "/cluster/{cluster_id}/node/{node_id}/state"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return  # Prevent re-initialization on multiple calls
        self._initialized = True
        self._base_path = os.getcwd()
        self._load_config()

    def _load_config(self):
        if os.path.exists(self._config_file):
            with open(self._config_file, 'r') as f:
                self._config = json.load(f)
        else:
            self._config = {}

        # Apply loaded config to attributes
        for k, v in self._config.items():
            setattr(self, k, v)

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super().__setattr__(key, value)
            return

        with FileLock(self._config_file_lock):
            self._config[key] = value
            super().__setattr__(key, value)
            with open(self._config_file, 'w') as f:
                json.dump(self._config, f, indent=4)

    def __delattr__(self, item):
        if item.startswith('_'):
            return

        with FileLock(self._config_file_lock):
            del self._config[item]
            super().__delattr__(item)
            with open(self._config_file, 'w') as f:
                json.dump(self._config, f, indent=4)
