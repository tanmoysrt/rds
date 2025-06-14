import contextlib
import time

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.message import DecodeError

from generated.job_pb2 import JobIdRequest, JobResponse, JobStatusResponse
from generated.job_pb2_grpc import JobServiceServicer
from server import ServerConfig
from server.internal.bg_job.job import get_redis_client
from server.internal.bg_job.utils import (
    acknowledge_job,
    cancel_job,
    get_job,
    get_job_status,
    get_non_acknowledged_jobs,
    schedule_job,
)


def get_job_or_404(job_id: int, context):
    job = get_job(job_id)
    if not job:
        context.abort(grpc.StatusCode.NOT_FOUND, f"Job with ID {job_id} not found.")
    return job

class JobService(JobServiceServicer):
    def Listen(self, request, context):
        config = ServerConfig()
        redis = get_redis_client()

        # Fetch and yield all non-acknowledged jobs initially
        for message in get_non_acknowledged_jobs():
            yield message

        pubsub = redis.pubsub()
        pubsub.subscribe(config.job_update_stream_redis_channel)

        try:
            while context.is_active():
                message = pubsub.get_message(ignore_subscribe_messages=True)
                if message and message["type"] == "message":
                    with contextlib.suppress(DecodeError):
                        response = JobResponse()
                        response.ParseFromString(message["data"])
                        yield response

                time.sleep(0.1)
        finally:
            pubsub.unsubscribe(config.job_update_stream_redis_channel)
            pubsub.close()

    def GetJob(self, request:JobIdRequest, context) -> JobResponse:
        job = get_job_or_404(request.id, context)
        return job.grpc_job_response

    def GetStatus(self, request:JobIdRequest, context) -> JobStatusResponse:
        status = get_job_status(request.id)
        if not status:
            context.abort(grpc.StatusCode.NOT_FOUND, f"Job with ID {request.id} not found.")
            return Empty()
        return JobStatusResponse(status=status.name)

    def Schedule(self, request:JobIdRequest, context) -> JobStatusResponse:
        job = get_job_or_404(request.id, context)
        return JobStatusResponse(status=schedule_job(job).name)

    def Cancel(self, request:JobIdRequest, context) -> JobStatusResponse:
        job = get_job_or_404(request.id, context)
        return JobStatusResponse(status=cancel_job(job).name)

    def Acknowledge(self, request:JobIdRequest, context) -> Empty:
        acknowledge_job(request.id)
        return Empty()
