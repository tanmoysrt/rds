from google.protobuf import empty_pb2 as _empty_pb2
import common_pb2 as _common_pb2
import proxy_pb2 as _proxy_pb2
import mysql_pb2 as _mysql_pb2
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
    __slots__ = ("proxy_create_request", "proxy_info_response", "proxy_id_request", "proxy_status_response", "proxy_monitor_credential_response", "proxy_upgrade_request", "proxy_delete_response", "my_sql_id_request", "my_sql_create_request", "my_sql_upgrade_request", "my_sql_info_response", "my_sql_status_response", "my_sql_delete_response")
    PROXY_CREATE_REQUEST_FIELD_NUMBER: _ClassVar[int]
    PROXY_INFO_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    PROXY_ID_REQUEST_FIELD_NUMBER: _ClassVar[int]
    PROXY_STATUS_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    PROXY_MONITOR_CREDENTIAL_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    PROXY_UPGRADE_REQUEST_FIELD_NUMBER: _ClassVar[int]
    PROXY_DELETE_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    MY_SQL_ID_REQUEST_FIELD_NUMBER: _ClassVar[int]
    MY_SQL_CREATE_REQUEST_FIELD_NUMBER: _ClassVar[int]
    MY_SQL_UPGRADE_REQUEST_FIELD_NUMBER: _ClassVar[int]
    MY_SQL_INFO_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    MY_SQL_STATUS_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    MY_SQL_DELETE_RESPONSE_FIELD_NUMBER: _ClassVar[int]
    proxy_create_request: _proxy_pb2.ProxyCreateRequest
    proxy_info_response: _proxy_pb2.ProxyInfoResponse
    proxy_id_request: _proxy_pb2.ProxyIdRequest
    proxy_status_response: _proxy_pb2.ProxyStatusResponse
    proxy_monitor_credential_response: _proxy_pb2.ProxyMonitorCredentialResponse
    proxy_upgrade_request: _proxy_pb2.ProxyUpgradeRequest
    proxy_delete_response: _proxy_pb2.ProxyDeleteResponse
    my_sql_id_request: _mysql_pb2.MySQLIdRequest
    my_sql_create_request: _mysql_pb2.MySQLCreateRequest
    my_sql_upgrade_request: _mysql_pb2.MySQLUpgradeRequest
    my_sql_info_response: _mysql_pb2.MySQLInfoResponse
    my_sql_status_response: _mysql_pb2.MySQLStatusResponse
    my_sql_delete_response: _mysql_pb2.MySQLDeleteResponse
    def __init__(self, proxy_create_request: _Optional[_Union[_proxy_pb2.ProxyCreateRequest, _Mapping]] = ..., proxy_info_response: _Optional[_Union[_proxy_pb2.ProxyInfoResponse, _Mapping]] = ..., proxy_id_request: _Optional[_Union[_proxy_pb2.ProxyIdRequest, _Mapping]] = ..., proxy_status_response: _Optional[_Union[_proxy_pb2.ProxyStatusResponse, _Mapping]] = ..., proxy_monitor_credential_response: _Optional[_Union[_proxy_pb2.ProxyMonitorCredentialResponse, _Mapping]] = ..., proxy_upgrade_request: _Optional[_Union[_proxy_pb2.ProxyUpgradeRequest, _Mapping]] = ..., proxy_delete_response: _Optional[_Union[_proxy_pb2.ProxyDeleteResponse, _Mapping]] = ..., my_sql_id_request: _Optional[_Union[_mysql_pb2.MySQLIdRequest, _Mapping]] = ..., my_sql_create_request: _Optional[_Union[_mysql_pb2.MySQLCreateRequest, _Mapping]] = ..., my_sql_upgrade_request: _Optional[_Union[_mysql_pb2.MySQLUpgradeRequest, _Mapping]] = ..., my_sql_info_response: _Optional[_Union[_mysql_pb2.MySQLInfoResponse, _Mapping]] = ..., my_sql_status_response: _Optional[_Union[_mysql_pb2.MySQLStatusResponse, _Mapping]] = ..., my_sql_delete_response: _Optional[_Union[_mysql_pb2.MySQLDeleteResponse, _Mapping]] = ...) -> None: ...
