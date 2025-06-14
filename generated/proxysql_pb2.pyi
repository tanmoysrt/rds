import common_pb2 as _common_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProxySQLInitRequest(_message.Message):
    __slots__ = ("meta", "hostname", "port", "username", "password")
    META_FIELD_NUMBER: _ClassVar[int]
    HOSTNAME_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.RequestMetadata
    hostname: str
    port: int
    username: str
    password: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.RequestMetadata, _Mapping]] = ..., hostname: _Optional[str] = ..., port: _Optional[int] = ..., username: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class ProxySQLInitResponse(_message.Message):
    __slots__ = ("meta", "success", "message")
    META_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    meta: _common_pb2.ResponseMetadata
    success: bool
    message: str
    def __init__(self, meta: _Optional[_Union[_common_pb2.ResponseMetadata, _Mapping]] = ..., success: bool = ..., message: _Optional[str] = ...) -> None: ...
