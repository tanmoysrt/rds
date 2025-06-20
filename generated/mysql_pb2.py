# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: mysql.proto
# Protobuf Python Version: 6.31.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    6,
    31,
    0,
    '',
    'mysql.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from . import common_pb2 as common__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0bmysql.proto\x12\x03rds\x1a\x0c\x63ommon.proto\"@\n\x0eMySQLIdRequest\x12\"\n\x04meta\x18\x01 \x01(\x0b\x32\x14.rds.RequestMetadata\x12\n\n\x02id\x18\x02 \x01(\t\"\xcd\x02\n\x12MySQLCreateRequest\x12\"\n\x04meta\x18\x01 \x01(\x0b\x32\x14.rds.RequestMetadata\x12\x0f\n\x02id\x18\x02 \x01(\tH\x00\x88\x01\x01\x12\x12\n\ncluster_id\x18\x03 \x01(\t\x12\x12\n\x05image\x18\x04 \x01(\tH\x01\x88\x01\x01\x12\x10\n\x03tag\x18\x05 \x01(\tH\x02\x88\x01\x01\x12\x16\n\tserver_id\x18\x06 \x01(\rH\x03\x88\x01\x01\x12\x14\n\x07\x64\x62_port\x18\x07 \x01(\rH\x04\x88\x01\x01\x12\x0f\n\x07service\x18\x08 \x01(\t\x12\x11\n\tbase_path\x18\t \x01(\t\x12\x15\n\rroot_password\x18\n \x01(\t\x12\x15\n\retcd_username\x18\x0b \x01(\t\x12\x15\n\retcd_password\x18\x0c \x01(\tB\x05\n\x03_idB\x08\n\x06_imageB\x06\n\x04_tagB\x0c\n\n_server_idB\n\n\x08_db_port\"a\n\x13MySQLUpgradeRequest\x12\"\n\x04meta\x18\x01 \x01(\x0b\x32\x14.rds.RequestMetadata\x12\n\n\x02id\x18\x02 \x01(\t\x12\r\n\x05image\x18\x03 \x01(\t\x12\x0b\n\x03tag\x18\x04 \x01(\t\"\xe7\x01\n\x11MySQLInfoResponse\x12#\n\x04meta\x18\x01 \x01(\x0b\x32\x15.rds.ResponseMetadata\x12\n\n\x02id\x18\x02 \x01(\t\x12\x12\n\ncluster_id\x18\x03 \x01(\t\x12\r\n\x05image\x18\x04 \x01(\t\x12\x0b\n\x03tag\x18\x05 \x01(\t\x12\x11\n\tserver_id\x18\x06 \x01(\r\x12\x0f\n\x07\x64\x62_port\x18\x07 \x01(\r\x12\x0f\n\x07service\x18\x08 \x01(\t\x12\x11\n\tbase_path\x18\t \x01(\t\x12)\n\x06status\x18\n \x01(\x0e\x32\x19.rds.SystemdServiceStatus\"e\n\x13MySQLStatusResponse\x12#\n\x04meta\x18\x01 \x01(\x0b\x32\x15.rds.ResponseMetadata\x12)\n\x06status\x18\x02 \x01(\x0e\x32\x19.rds.SystemdServiceStatus\"K\n\x13MySQLDeleteResponse\x12#\n\x04meta\x18\x01 \x01(\x0b\x32\x15.rds.ResponseMetadata\x12\x0f\n\x07\x64\x65leted\x18\x02 \x01(\x08\x32\xda\x04\n\x0cMySQLService\x12\x39\n\x06\x43reate\x12\x17.rds.MySQLCreateRequest\x1a\x16.rds.MySQLInfoResponse\x12\x32\n\x03Get\x12\x13.rds.MySQLIdRequest\x1a\x16.rds.MySQLInfoResponse\x12\x37\n\x06Status\x12\x13.rds.MySQLIdRequest\x1a\x18.rds.MySQLStatusResponse\x12\x36\n\x05Start\x12\x13.rds.MySQLIdRequest\x1a\x18.rds.MySQLStatusResponse\x12\x35\n\x04Stop\x12\x13.rds.MySQLIdRequest\x1a\x18.rds.MySQLStatusResponse\x12\x38\n\x07Restart\x12\x13.rds.MySQLIdRequest\x1a\x18.rds.MySQLStatusResponse\x12\x37\n\x06\x44\x65lete\x12\x13.rds.MySQLIdRequest\x1a\x18.rds.MySQLDeleteResponse\x12;\n\x07Upgrade\x12\x18.rds.MySQLUpgradeRequest\x1a\x16.rds.MySQLInfoResponse\x12;\n\x0cSetupReplica\x12\x13.rds.MySQLIdRequest\x1a\x16.rds.MySQLInfoResponse\x12\x46\n\x13SyncReplicationUser\x12\x13.rds.MySQLIdRequest\x1a\x1a.rds.EmptyResponseWithMetab\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'mysql_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_MYSQLIDREQUEST']._serialized_start=34
  _globals['_MYSQLIDREQUEST']._serialized_end=98
  _globals['_MYSQLCREATEREQUEST']._serialized_start=101
  _globals['_MYSQLCREATEREQUEST']._serialized_end=434
  _globals['_MYSQLUPGRADEREQUEST']._serialized_start=436
  _globals['_MYSQLUPGRADEREQUEST']._serialized_end=533
  _globals['_MYSQLINFORESPONSE']._serialized_start=536
  _globals['_MYSQLINFORESPONSE']._serialized_end=767
  _globals['_MYSQLSTATUSRESPONSE']._serialized_start=769
  _globals['_MYSQLSTATUSRESPONSE']._serialized_end=870
  _globals['_MYSQLDELETERESPONSE']._serialized_start=872
  _globals['_MYSQLDELETERESPONSE']._serialized_end=947
  _globals['_MYSQLSERVICE']._serialized_start=950
  _globals['_MYSQLSERVICE']._serialized_end=1552
# @@protoc_insertion_point(module_scope)
