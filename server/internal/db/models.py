from __future__ import annotations

import contextlib
import datetime
import json
from enum import IntEnum

from peewee import BlobField, BooleanField, CharField, DateTimeField, IntegerField, Model, TextField

from generated.common_pb2 import ResponseMetadata
from generated.job_pb2 import JobResponse
from server import ServerConfig
from server.internal.db import local_database
from server.internal.db.utils import wrap_in_job_update_response
from server.internal.proto_utils import discover_protobuf_messages
from server.internal.utils import get_redis_client


class JobStatus(IntEnum):
    DRAFT = 0
    SCHEDULED = 1
    QUEUED = 2
    RUNNING = 3
    SUCCESS = 4
    FAILURE = 5
    CANCELLED = 6

class JobModel(Model):
    id = IntegerField(primary_key=True)
    ref = CharField(max_length=500, null=True, default=None)
    status = IntegerField(
        choices=[(status.value, status.name) for status in JobStatus],
        default=JobStatus.DRAFT.value,
    )

    timeout = IntegerField()

    service = CharField(max_length=256, null=True, default="")
    method = CharField(max_length=256, null=True, default="")

    request_type = CharField(max_length=256, null=True, default="")
    request_data = BlobField(null=True, default=b"")
    response_type = CharField(max_length=256, null=True, default="")
    response_data = BlobField(null=True, default=b"")

    error_message = TextField(null=True, default="")
    traceback = TextField(null=True, default="")

    created_at = DateTimeField(default=datetime.datetime.now)
    scheduled_at = DateTimeField(null=True)
    enqueued_at = DateTimeField(null=True)
    started_at = DateTimeField(null=True)
    ended_at = DateTimeField(null=True)

    acknowledged = BooleanField(default=False)

    class Meta:
        database = local_database
        table_name = "job"

    def save(self, force_insert=False, only=None, publish_update=True):
        return_value = super().save(force_insert=force_insert, only=only)
        if publish_update:
            with contextlib.suppress(Exception):
                # Publish the job update to the Redis stream
                redis = get_redis_client()
                config = ServerConfig()
                redis.publish(config.job_update_stream_redis_channel, self.grpc_job_response.SerializeToString())
        return return_value

    @property
    def response_metadata(self) -> ResponseMetadata:
        return ResponseMetadata(
            job_id=self.id,
            ref=self.ref,
            status=JobStatus(self.status).name,
            created_at=self.created_at,
            scheduled_at=self.scheduled_at if self.scheduled_at else None,
            started_at=self.started_at if self.started_at else None,
            ended_at=self.ended_at if self.ended_at else None,
            error_message=self.error_message if self.error_message else None,
            traceback=self.traceback if self.traceback else None,
        )

    @property
    def grpc_request(self):
        request = discover_protobuf_messages()[self.request_type]()
        request.ParseFromString(self.request_data)
        return request

    @property
    def grpc_response(self):
        response = discover_protobuf_messages()[self.response_type]()
        if self.response_data:
            response.ParseFromString(self.response_data)
        response.meta.CopyFrom(self.response_metadata)
        return response

    @property
    def grpc_job_response(self) -> JobResponse:
        return wrap_in_job_update_response(self.grpc_response)

    def acknowledge(self):
        self.acknowledged = True
        self.save(only=[JobModel.acknowledged])

class SystemdServiceModel(Model):
    id = TextField(primary_key=True)
    service = TextField(null=True, default="")
    image = TextField(null=True, default="")
    tag = TextField(null=True, default="")
    environment_variables = TextField(null=True, default="{}")
    mounts = TextField(null=True, default="{}")
    podman_args = TextField(null=True, default="[]")
    metadata = TextField(null=True, default="{}")
    cluster_id = TextField(null=True, default="")
    etcd_username = TextField(null=True, default="")
    etcd_password = TextField(null=True, default="")

    class Meta:
        database = local_database
        table_name = "systemd_service"

    @classmethod
    def create(cls, **kwargs):
        # If the json parameters are provided as dicts, convert them to JSON strings and set to corresponding fields
        if 'environment_variables_json' in kwargs:
            kwargs['environment_variables'] = json.dumps(kwargs.pop('environment_variables_json', {}))
        if 'mounts_json' in kwargs:
            kwargs['mounts'] = json.dumps(kwargs.pop('mounts_json', {}))
        if 'podman_args_json' in kwargs:
            kwargs['podman_args'] = json.dumps(kwargs.pop('podman_args_json', []))
        if 'metadata_json' in kwargs:
            kwargs['metadata'] = json.dumps(kwargs.pop('metadata_json', {}))
        return super().create(**kwargs)


    @property
    def environment_variables_json(self) -> dict[str, str]:
        return json.loads(self.environment_variables or '{}')

    @environment_variables_json.setter
    def environment_variables_json(self, values):
        self.environment_variables = json.dumps(values or {})

    @property
    def mounts_json(self) -> dict[str, str]:
        return json.loads(self.mounts or '{}')

    @mounts_json.setter
    def mounts_json(self, values):
        self.mounts = json.dumps(values or {})

    @property
    def podman_args_json(self) -> list[str]:
        return json.loads(self.podman_args or '[]')

    @podman_args_json.setter
    def podman_args_json(self, values):
        self.podman_args = json.dumps(values or [])

    @property
    def metadata_json(self) -> dict[str, str]:
        return json.loads(self.metadata or '{}')

    @metadata_json.setter
    def metadata_json(self, values):
        self.metadata = json.dumps(values or {})

