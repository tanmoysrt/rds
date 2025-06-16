import common_pb2 as _common_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MySQLIdRequest(_message.Message):
    __slots__ = ("meta", "id")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.RequestMetadata
    id: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ..., id: _Optional[str] = ...) -> None: ...

class MySQLCreateRequest(_message.Message):
    __slots__ = ("meta", "id", "image", "tag", "server_id", "db_port", "service", "base_path")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    SERVER_ID_FIELD_NUMBER: _ClassVar[int]
    DB_PORT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    BASE_PATH_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.RequestMetadata
    id: str
    image: str
    tag: str
    server_id: int
    db_port: int
    service: str
    base_path: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ..., id: _Optional[str] = ..., image: _Optional[str] = ..., tag: _Optional[str] = ..., server_id: _Optional[int] = ..., db_port: _Optional[int] = ..., service: _Optional[str] = ..., base_path: _Optional[str] = ...) -> None: ...

class MySQLUpgradeRequest(_message.Message):
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

class MySQLInfoResponse(_message.Message):
    __slots__ = ("meta", "id", "image", "tag", "server_id", "db_port", "service", "base_path", "status")
    META_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    TAG_FIELD_NUMBER: _ClassVar[int]
    SERVER_ID_FIELD_NUMBER: _ClassVar[int]
    DB_PORT_FIELD_NUMBER: _ClassVar[int]
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    BASE_PATH_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    id: str
    image: str
    tag: str
    server_id: int
    db_port: int
    service: str
    base_path: str
    status: _common_pb2.SystemdServiceStatus
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., id: _Optional[str] = ..., image: _Optional[str] = ..., tag: _Optional[str] = ..., server_id: _Optional[int] = ..., db_port: _Optional[int] = ..., service: _Optional[str] = ..., base_path: _Optional[str] = ..., status: _Optional[_Union[_common_pb2.SystemdServiceStatus, str]] = ...) -> None: ...

class MySQLStatusResponse(_message.Message):
    __slots__ = ("meta", "status")
    META_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    status: _common_pb2.SystemdServiceStatus
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., status: _Optional[_Union[_common_pb2.SystemdServiceStatus, str]] = ...) -> None: ...

class MySQLDeleteResponse(_message.Message):
    __slots__ = ("meta", "deleted")
    META_FIELD_NUMBER: _ClassVar[int]
    DELETED_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    deleted: bool
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., deleted: bool = ...) -> None: ...
