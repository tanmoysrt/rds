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
    grpc_port:int

    job_update_stream_redis_channel:str

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
