from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DBType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MYSQL: _ClassVar[DBType]
    MARIADB: _ClassVar[DBType]
MYSQL: DBType
MARIADB: DBType

class DBHealthStatus(_message.Message):
    __slots__ = ("db_type", "reported_at", "global_transaction_id")
    DB_TYPE_FIELD_NUMBER: _ClassVar[int]
    REPORTED_AT_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_TRANSACTION_ID_FIELD_NUMBER: _ClassVar[int]
    db_type: DBType
    reported_at: int
    global_transaction_id: str
    def __init__(self, db_type: _Optional[_Union[DBType, str]] = ..., reported_at: _Optional[int] = ..., global_transaction_id: _Optional[str] = ...) -> None: ...
