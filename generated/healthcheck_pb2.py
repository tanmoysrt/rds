# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: healthcheck.proto
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
    'healthcheck.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x11healthcheck.proto\x12\x03rds\x1a\x1bgoogle/protobuf/empty.proto\"\x1f\n\x0cPingResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x32G\n\x12HealthCheckService\x12\x31\n\x04Ping\x12\x16.google.protobuf.Empty\x1a\x11.rds.PingResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'healthcheck_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_PINGRESPONSE']._serialized_start=55
  _globals['_PINGRESPONSE']._serialized_end=86
  _globals['_HEALTHCHECKSERVICE']._serialized_start=88
  _globals['_HEALTHCHECKSERVICE']._serialized_end=159
# @@protoc_insertion_point(module_scope)
