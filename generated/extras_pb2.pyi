from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DBType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN_DB_TYPE: _ClassVar[DBType]
    MYSQL: _ClassVar[DBType]
    MARIADB: _ClassVar[DBType]

class ClusterNodeType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN_CLUSTER_NODE_TYPE: _ClassVar[ClusterNodeType]
    MASTER: _ClassVar[ClusterNodeType]
    REPLICA: _ClassVar[ClusterNodeType]
    READ_ONLY: _ClassVar[ClusterNodeType]
    STANDBY: _ClassVar[ClusterNodeType]
UNKNOWN_DB_TYPE: DBType
MYSQL: DBType
MARIADB: DBType
UNKNOWN_CLUSTER_NODE_TYPE: ClusterNodeType
MASTER: ClusterNodeType
REPLICA: ClusterNodeType
READ_ONLY: ClusterNodeType
STANDBY: ClusterNodeType

class DBHealthStatus(_message.Message):
    __slots__ = ("db_type", "reported_at", "global_transaction_id")
    DB_TYPE_FIELD_NUMBER: _ClassVar[int]
    REPORTED_AT_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    db_type: DBType
    reported_at: int
    global_transaction_id: str
    def __init__(self, db_type: _Optional[_Union[DBType, str]] = ..., reported_at: _Optional[int] = ..., global_transaction_id: _Optional[str] = ...) -> None: ...

class ClusterNodeConfig(_message.Message):
    __slots__ = ("type", "ip", "agent_port", "db_port")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    IP_FIELD_NUMBER: _ClassVar[int]
    AGENT_PORT_FIELD_NUMBER: _ClassVar[int]
    DB_PORT_FIELD_NUMBER: _ClassVar[int]
    type: ClusterNodeType
    ip: str
    agent_port: int
    db_port: int
    def __init__(self, type: _Optional[_Union[ClusterNodeType, str]] = ..., ip: _Optional[str] = ..., agent_port: _Optional[int] = ..., db_port: _Optional[int] = ...) -> None: ...

class ClusterProxyConfig(_message.Message):
    __slots__ = ("ip", "agent_port", "read_port", "read_write_port", "monitor_user", "monitor_password_hash")
    IP_FIELD_NUMBER: _ClassVar[int]
    AGENT_PORT_FIELD_NUMBER: _ClassVar[int]
    READ_PORT_FIELD_NUMBER: _ClassVar[int]
    READ_WRITE_PORT_FIELD_NUMBER: _ClassVar[int]
    MONITOR_USER_FIELD_NUMBER: _ClassVar[int]
    MONITOR_PASSWORD_HASH_FIELD_NUMBER: _ClassVar[int]
    ip: str
    agent_port: int
    read_port: int
    read_write_port: int
    monitor_user: str
    monitor_password_hash: str
    def __init__(self, ip: _Optional[str] = ..., agent_port: _Optional[int] = ..., read_port: _Optional[int] = ..., read_write_port: _Optional[int] = ..., monitor_user: _Optional[str] = ..., monitor_password_hash: _Optional[str] = ...) -> None: ...

class ClusterConfig(_message.Message):
    __slots__ = ("version", "current_master", "desired_master", "promoted_by", "replica_count", "min_replication_lag_ms", "failover_cooldown_ms", "last_failover_timestamp", "nodes", "proxy", "shared_token")
    class NodesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ClusterNodeConfig
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ClusterNodeConfig, _Mapping]] = ...) -> None: ...
    VERSION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_MASTER_FIELD_NUMBER: _ClassVar[int]
    DESIRED_MASTER_FIELD_NUMBER: _ClassVar[int]
    PROMOTED_BY_FIELD_NUMBER: _ClassVar[int]
    REPLICA_COUNT_FIELD_NUMBER: _ClassVar[int]
    MIN_REPLICATION_LAG_MS_FIELD_NUMBER: _ClassVar[int]
    FAILOVER_COOLDOWN_MS_FIELD_NUMBER: _ClassVar[int]
    LAST_FAILOVER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    NODES_FIELD_NUMBER: _ClassVar[int]
    PROXY_FIELD_NUMBER: _ClassVar[int]
    SHARED_TOKEN_FIELD_NUMBER: _ClassVar[int]
    version: int
    current_master: str
    desired_master: str
    promoted_by: str
    replica_count: int
    min_replication_lag_ms: int
    failover_cooldown_ms: int
    last_failover_timestamp: int
    nodes: _containers.MessageMap[str, ClusterNodeConfig]
    proxy: ClusterProxyConfig
    shared_token: str
    def __init__(self, version: _Optional[int] = ..., current_master: _Optional[str] = ..., desired_master: _Optional[str] = ..., promoted_by: _Optional[str] = ..., replica_count: _Optional[int] = ..., min_replication_lag_ms: _Optional[int] = ..., failover_cooldown_ms: _Optional[int] = ..., last_failover_timestamp: _Optional[int] = ..., nodes: _Optional[_Mapping[str, ClusterNodeConfig]] = ..., proxy: _Optional[_Union[ClusterProxyConfig, _Mapping]] = ..., shared_token: _Optional[str] = ...) -> None: ...
