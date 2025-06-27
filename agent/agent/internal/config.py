import contextlib
import json
import os
import tempfile
from functools import cache

from cryptography.utils import cached_property
from filelock import FileLock

from generated.extras_pb2 import ClusterConfig as ClusterConfigProtobufMessage
from generated.extras_pb2 import ClusterNodeConfig, ClusterNodeStatus, ClusterNodeType
from agent.internal.etcd_client import Etcd3Client


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
    etcd_monitor_commands_redis_channel:str = "etcd_monitor_commands"

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
    kv_cluster_prefix:str = "/clusters/{cluster_id}"
    kv_cluster_config_key:str = "/clusters/{cluster_id}/config"
    kv_cluster_current_master_key:str = "/clusters/{cluster_id}/master"
    kv_cluster_election_lock_key:str = "/clusters/{cluster_id}/election/lock"
    kv_cluster_node_status_key:str = "/clusters/{cluster_id}/nodes/{node_id}/status"
    kv_cluster_node_cluster_state_key:str = "/clusters/{cluster_id}/nodes/{node_id}/state"

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
            self.__setattr__(k, v, store_in_file=False)

    def __setattr__(self, key, value, store_in_file=True):
        if key.startswith('_'):
            super().__setattr__(key, value)
            return

        if not store_in_file:
            super().__setattr__(key, value)
            return

        with FileLock(self._config_file_lock):
            self._config[key] = value
            super().__setattr__(key, value)
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                json.dump(self._config, f, indent=4)
                f.flush()
                os.replace(f.name, self._config_file)

    def __delattr__(self, item):
        if item.startswith('_'):
            return

        with FileLock(self._config_file_lock):
            del self._config[item]
            super().__delattr__(item)
            with open(self._config_file, 'w') as f:
                json.dump(self._config, f, indent=4)



class ClusterConfig:
    """
    It's a wrapper around ClusterConfig Protobuf Message
    To add additional functionality
    """
    def __init__(self, etcd_client:Etcd3Client|None, cluster_id:str):
        self.cluster_id = cluster_id
        self.etcd_client = etcd_client
        self._proto:ClusterConfigProtobufMessage = ClusterConfigProtobufMessage()
        self.version = None
        if self.etcd_client:
            self._load()

    def __getattr__(self, name):
        # Delegate attribute access to the protobuf instance
        return getattr(self._proto, name)

    def __dir__(self):
        # Combine ClusterConfig and protobuf attributes for better autocomplete
        return list(set(list(super().__dir__()) + list(dir(self._proto))))

    @classmethod
    def from_base(cls, base_obj: ClusterConfigProtobufMessage, cluster_id:str) -> 'ClusterConfig':
        """
        Creates a ClusterConfig instance from a base protobuf object.
        :param base_obj: The base protobuf object to copy from.
        :param cluster_id: The cluster ID for this configuration.
        :return: A new ClusterConfig instance.
        """
        obj = cls(etcd_client=None, cluster_id=cluster_id)
        obj._proto = base_obj
        return obj

    @classmethod
    def from_serialized_string(cls, serialized_str: bytes, cluster_id:str) -> 'ClusterConfig':
        """
        Creates a ClusterConfig instance from a serialized string.
        :param serialized_str: The serialized protobuf string.
        :param cluster_id: The cluster ID for this configuration.
        :return: A new ClusterConfig instance.
        """
        obj = cls(etcd_client=None, cluster_id=cluster_id)
        obj._proto.ParseFromString(serialized_str)
        return obj


    def reload(self):
        """Reloads the cluster configuration from etcd."""
        self._load()
        self._filter_nodes.cache_clear()

    def get_node(self, node_id:str) -> ClusterNodeConfig:
        if node_id not in self.nodes:
            raise ValueError(f"Node with id {node_id} not found in cluster config")
        return self.nodes[node_id]

    @property
    def node_ids(self) -> list[str]:
        return list(self.nodes.keys())

    @property
    def online_master_node_ids(self) -> list[str]:
        """Returns a list of online master node IDs."""
        return self._filter_nodes(ClusterNodeType.MASTER, ClusterNodeStatus.ONLINE)

    @property
    def offline_master_node_ids(self) -> list[str]:
        """Returns a list of offline master node IDs."""
        return self._filter_nodes(ClusterNodeType.MASTER, ClusterNodeStatus.OFFLINE)

    @property
    def online_replica_node_ids(self) -> list[str]:
        """Returns a list of online replica node IDs."""
        return self._filter_nodes(ClusterNodeType.REPLICA, ClusterNodeStatus.ONLINE)

    @property
    def offline_replica_node_ids(self) -> list[str]:
        return self._filter_nodes(ClusterNodeType.REPLICA, ClusterNodeStatus.OFFLINE)

    @property
    def online_read_only_node_ids(self) -> list[str]:
        """Returns a list of online read-only node IDs."""
        return self._filter_nodes(ClusterNodeType.READ_ONLY, ClusterNodeStatus.ONLINE)

    @property
    def offline_read_only_node_ids(self) -> list[str]:
        """Returns a list of offline read-only node IDs."""
        return self._filter_nodes(ClusterNodeType.READ_ONLY, ClusterNodeStatus.OFFLINE)

    @property
    def online_standby_node_ids(self) -> list[str]:
        """Returns a list of online standby node IDs."""
        return self._filter_nodes(ClusterNodeType.STANDBY, ClusterNodeStatus.ONLINE)

    @property
    def offline_standby_node_ids(self) -> list[str]:
        """Returns a list of offline standby node IDs."""
        return self._filter_nodes(ClusterNodeType.STANDBY, ClusterNodeStatus.OFFLINE)

    def copy_and_mark_node_as_offline(self, node_id:str) -> ClusterConfigProtobufMessage:
        msg = ClusterConfigProtobufMessage()
        msg.CopyFrom(self._proto)
        msg.nodes[node_id].status = ClusterNodeStatus.OFFLINE
        return msg

    def copy_and_mark_node_as_online(self, node_id:str) -> ClusterConfigProtobufMessage:
        """
        Creates a copy of the current configuration and marks the specified node as online.
        :param node_id: The ID of the node to mark as online.
        :return: A new ClusterConfigProtobufMessage with the updated status.
        """
        msg = ClusterConfigProtobufMessage()
        msg.CopyFrom(self._proto)
        if node_id in msg.nodes:
            msg.nodes[node_id].status = ClusterNodeStatus.ONLINE
        return msg

    def copy_and_switch_master_replica(self, new_master:str, new_replica:str) -> ClusterConfigProtobufMessage:
        """
        Creates a copy of the current configuration and switches the roles of the specified nodes.
        :param new_master: The ID of the node to be promoted to master.
        :param new_replica: The ID of the node to be demoted to replica.
        :return: A new ClusterConfigProtobufMessage with the updated roles.
        """
        msg = ClusterConfigProtobufMessage()
        msg.CopyFrom(self._proto)
        if new_master in msg.nodes:
            msg.nodes[new_master].type = ClusterNodeType.MASTER
        if new_master in msg.nodes:
            msg.nodes[new_replica].type = ClusterNodeType.REPLICA
        return msg



    @cache
    def _filter_nodes(self, node_type:ClusterNodeType, status:ClusterNodeStatus) -> list[str]:
        """
        Returns a list of node IDs filtered by type and status.
        :param node_type: The type of the node (MASTER or REPLICA).
        :param status: The status of the node (ONLINE or OFFLINE).
        :return: List of node IDs matching the criteria.
        """
        return [
            node_id for node_id in self.nodes if
            self.nodes[node_id].type == node_type and
            self.nodes[node_id].status == status
        ]

    def _load(self):
        if not self.etcd_client:
            raise ValueError("Failed To load.\nEtcd client is not initialized.\nPossible Reason - Instance created from ClusterConfigProtobufMessage object")

        value = self.etcd_client.get(self.kv_cluster_config_key)
        if not value:
            raise ValueError(f"Cluster config not found for cluster_id: {self.cluster_id}")
        data, meta = value
        self._proto.ParseFromString(data)
        self.version = meta.version

    @cached_property
    def kv_cluster_config_key(self) -> str:
        return ServerConfig().kv_cluster_config_key.format(cluster_id=self.cluster_id)

    def __del__(self):
        with contextlib.suppress(Exception):
            self.etcd_client.close()
