import contextlib
import traceback
from datetime import datetime

from rq import Queue

from generated.common_pb2 import Status as ResponseMetadataStatus
from server.internal.bg_job.rpc_context import DummyRPCContext
from server.internal.db.models import JobModel, JobStatus
from server.internal.proto_utils import (
    discover_protobuf_messages_with_meta,
    get_service_method,
)
from server.internal.utils import get_redis_client


def queue(name:str="default"):
    return Queue(name, connection=get_redis_client())

def execute_job(job_id: int):
    job : JobModel = JobModel.get_by_id(job_id)
    if not job:
        return

    # Update job status to RUNNING
    try:
        job.status = JobStatus.RUNNING.value
        if not job.enqueued_at:
            job.enqueued_at = datetime.now()
        job.started_at = datetime.now()
        job.save()
    except:
        print("Failed to update job status to RUNNING")
        with contextlib.suppress(Exception):
            job.status = JobStatus.FAILURE.value
            job.ended_at = datetime.now()
            job.error_message = "Failed to update job status to RUNNING"
            job.traceback = traceback.format_exc()
            job.save()
        return

    # Execute the job
    try:
        func = get_service_method(job.service, job.method)

        if not func:
            raise Exception(f"Service method {job.service}.{job.method}  not found")

        if job.request_type not in discover_protobuf_messages_with_meta():
            raise Exception(f"Request type {job.request_type} not found in protobuf messages registry (with metadata support)")

        # Execute the function with the request and context
        context = DummyRPCContext()
        response = func(job.grpc_request, context)

        # Set response data and type in the job
        job.response_data = response.SerializeToString()
        job.response_type = response.__class__.__module__ + "." + response.__class__.__name__

        # Sync metadata
        job.status = JobStatus[ResponseMetadataStatus.Name(response.meta.status)].value

    except Exception as e:
        job.status = JobStatus.FAILURE.value
        job.error_message = str(e)
        job.traceback = traceback.format_exc()

    finally:
        job.ended_at = datetime.now()
        job.save()
