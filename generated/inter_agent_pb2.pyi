from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class RequestRsyncAccessRequest(_message.Message):
    __slots__ = ("cluster_id", "node_id")
    CLUSTER_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    cluster_id: str
    node_id: str
    def __init__(self, cluster_id: _Optional[str] = ..., node_id: _Optional[str] = ...) -> None: ...

class RequestRsyncAccessResponse(_message.Message):
    __slots__ = ("instance_id", "port", "username", "password", "src_path")
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    SRC_PATH_FIELD_NUMBER: _ClassVar[int]
    instance_id: str
    port: int
    username: str
    password: str
    src_path: str
    def __init__(self, instance_id: _Optional[str] = ..., port: _Optional[int] = ..., username: _Optional[str] = ..., password: _Optional[str] = ..., src_path: _Optional[str] = ...) -> None: ...

class RevokeRsyncAccessRequest(_message.Message):
    __slots__ = ("cluster_id", "instance_id")
    CLUSTER_ID_FIELD_NUMBER: _ClassVar[int]
    INSTANCE_ID_FIELD_NUMBER: _ClassVar[int]
    cluster_id: str
    instance_id: str
    def __init__(self, cluster_id: _Optional[str] = ..., instance_id: _Optional[str] = ...) -> None: ...
