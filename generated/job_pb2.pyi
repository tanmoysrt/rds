from google.protobuf import empty_pb2 as _empty_pb2
import common_pb2 as _common_pb2
import proxysql_pb2 as _proxysql_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class JobIdRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class JobStatusResponse(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: _common_pb2.Status
    def __init__(self, status: _Optional[_Union[_common_pb2.Status, str]] = ...) -> None: ...

class JobResponse(_message.Message):
    __slots__ = ("proxy_sql_init_response",)
    PROXY_SQL_INIT_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    proxy_sql_init_response: _proxysql_pb2.ProxySQLInitResponse
    def __init__(self, proxy_sql_init_response: _Optional[_Union[_proxysql_pb2.ProxySQLInitResponse, _Mapping]] = ...) -> None: ...
