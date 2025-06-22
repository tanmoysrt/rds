import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProxyIdRequest(_message.Message):
    __slots__ = ("meta", "id")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.RequestMetadata
    id: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ..., id: _Optional[str] = ...) -> None: ...

class ProxyCreateRequest(_message.Message):
    __slots__ = ("meta", "id", "cluster_id", "image", "tag", "db_readwrite_port", "db_readonly_port", "base_path", "etcd_username", "etcd_password")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    CLUSTER_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    DB_READWRITE_PORT_FIELD_NUMBER: _ClassVar[int]
    DB_READONLY_PORT_FIELD_NUMBER: _ClassVar[int]
    BASE_PATH_FIELD_NUMBER: _ClassVar[int]
    ETCD_USERNAME_FIELD_NUMBER: _ClassVar[int]
    ETCD_PASSWORD_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.RequestMetadata
    id: str
    cluster_id: str
    image: str
    tag: str
    db_readwrite_port: int
    db_readonly_port: int
    base_path: str
    etcd_username: str
    etcd_password: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ..., id: _Optional[str] = ..., cluster_id: _Optional[str] = ..., image: _Optional[str] = ..., tag: _Optional[str] = ..., db_readwrite_port: _Optional[int] = ..., db_readonly_port: _Optional[int] = ..., base_path: _Optional[str] = ..., etcd_username: _Optional[str] = ..., etcd_password: _Optional[str] = ...) -> None: ...

class ProxyUpgradeRequest(_message.Message):
    __slots__ = ("meta", "id", "image", "tag")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.RequestMetadata
    id: str
    image: str
    tag: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ..., id: _Optional[str] = ..., image: _Optional[str] = ..., tag: _Optional[str] = ...) -> None: ...

class ProxyInfoResponse(_message.Message):
    __slots__ = ("meta", "id", "cluster_id", "image", "tag", "db_readwrite_port", "db_readonly_port", "base_path", "status")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    CLUSTER_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    DB_READWRITE_PORT_FIELD_NUMBER: _ClassVar[int]
    DB_READONLY_PORT_FIELD_NUMBER: _ClassVar[int]
    BASE_PATH_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    id: str
    cluster_id: str
    image: str
    tag: str
    db_readwrite_port: int
    db_readonly_port: int
    base_path: str
    status: _common_pb2.SystemdServiceStatus
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., id: _Optional[str] = ..., cluster_id: _Optional[str] = ..., image: _Optional[str] = ..., tag: _Optional[str] = ..., db_readwrite_port: _Optional[int] = ..., db_readonly_port: _Optional[int] = ..., base_path: _Optional[str] = ..., status: _Optional[_Union[_common_pb2.SystemdServiceStatus, str]] = ...) -> None: ...

class ProxyStatusResponse(_message.Message):
    __slots__ = ("meta", "status")
    META_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    status: _common_pb2.SystemdServiceStatus
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., status: _Optional[_Union[_common_pb2.SystemdServiceStatus, str]] = ...) -> None: ...

class ProxyMonitorCredentialResponse(_message.Message):
    __slots__ = ("meta", "username", "password")
    META_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    username: str
    password: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., username: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class ProxyDeleteResponse(_message.Message):
    __slots__ = ("meta", "deleted")
    META_FIELD_NUMBER: _ClassVar[int]
    DELETED_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    deleted: bool
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., deleted: bool = ...) -> None: ...

class ProxySyncUsersRequest(_message.Message):
    __slots__ = ("meta", "id", "exclude_users", "users_to_sync")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    EXCLUDE_USERS_FIELD_NUMBER: _ClassVar[int]
    USERS_TO_SYNC_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.RequestMetadata
    id: str
    exclude_users: _containers.RepeatedScalarFieldContainer[str]
    users_to_sync: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, meta: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ..., id: _Optional[str] = ..., exclude_users: _Optional[_Iterable[str]] = ..., users_to_sync: _Optional[_Iterable[str]] = ...) -> None: ...

class ProxySyncUsersResponse(_message.Message):
    __slots__ = ("meta", "added_users", "removed_users", "updated_users")
    META_FIELD_NUMBER: _ClassVar[int]
    ADDED_USERS_FIELD_NUMBER: _ClassVar[int]
    REMOVED_USERS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_USERS_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    added_users: _containers.RepeatedScalarFieldContainer[str]
    removed_users: _containers.RepeatedScalarFieldContainer[str]
    updated_users: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., added_users: _Optional[_Iterable[str]] = ..., removed_users: _Optional[_Iterable[str]] = ..., updated_users: _Optional[_Iterable[str]] = ...) -> None: ...
