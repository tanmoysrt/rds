from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[Status]
    DRAFT: _ClassVar[Status]
    SCHEDULED: _ClassVar[Status]
    QUEUED: _ClassVar[Status]
    RUNNING: _ClassVar[Status]
    FAILURE: _ClassVar[Status]
    SUCCESS: _ClassVar[Status]
    CANCELLED: _ClassVar[Status]
UNKNOWN: Status
DRAFT: Status
SCHEDULED: Status
QUEUED: Status
RUNNING: Status
FAILURE: Status
SUCCESS: Status
CANCELLED: Status

class RequestMetadata(_message.Message):
    __slots__ = ("is_async", "ref", "timeout", "scheduled_at")
    IS_ASYNC_FIELD_NUMBER: _ClassVar[int]
    REF_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_AT_FIELD_NUMBER: _ClassVar[int]
    is_async: bool
    ref: str
    timeout: int
    scheduled_at: _timestamp_pb2.Timestamp
    def __init__(self, is_async: bool = ..., ref: _Optional[str] = ..., timeout: _Optional[int] = ..., scheduled_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ResponseMetadata(_message.Message):
    __slots__ = ("job_id", "ref", "status", "created_at", "scheduled_at", "started_at", "ended_at", "error_message", "traceback")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    REF_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_AT_FIELD_NUMBER: _ClassVar[int]
    STARTED_AT_FIELD_NUMBER: _ClassVar[int]
    ENDED_AT_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TRACEBACK_FIELD_NUMBER: _ClassVar[int]
    job_id: int
    ref: str
    status: Status
    created_at: _timestamp_pb2.Timestamp
    scheduled_at: _timestamp_pb2.Timestamp
    started_at: _timestamp_pb2.Timestamp
    ended_at: _timestamp_pb2.Timestamp
    error_message: str
    traceback: str
    def __init__(self, job_id: _Optional[int] = ..., ref: _Optional[str] = ..., status: _Optional[_Union[Status, str]] = ..., created_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., scheduled_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., started_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., ended_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., error_message: _Optional[str] = ..., traceback: _Optional[str] = ...) -> None: ...

class UnknownError(_message.Message):
    __slots__ = ("error_message", "traceback")
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TRACEBACK_FIELD_NUMBER: _ClassVar[int]
    error_message: str
    traceback: str
    def __init__(self, error_message: _Optional[str] = ..., traceback: _Optional[str] = ...) -> None: ...
