from datetime import datetime

from rq.command import send_stop_job_command
from rq.job import Job as RQJob

from server.internal.bg_job.job import execute_job, queue
from server.internal.db.models import JobModel, JobStatus
from server.internal.utils import get_redis_client


def get_job(job_id: int) -> JobModel | None:
    try:
        return JobModel.get_by_id(job_id)
    except JobModel.DoesNotExist:
        return None

def get_job_status(job_id:int) -> JobStatus|None:
    status = JobModel.select(JobModel.status).where(JobModel.id == job_id).scalar()
    return JobStatus(status)

def get_non_acknowledged_jobs():
    """
    Yields all jobs that have been not acknowledged yet.
    """
    for job in JobModel.select().where(JobModel.acknowledged == False):
        yield job.grpc_job_response

def create_job(service:str, method:str, request_type:str, request_data:bytes, response_type:str, ref:str|None=None, timeout:int|None=None, scheduled_at:datetime|None=None) -> JobModel:
    return JobModel.create(
        ref=ref,
        timeout=timeout if timeout else 3600,  # Default timeout is 1 hour
        scheduled_at=scheduled_at,
        status=JobStatus.DRAFT.value,
        service=service,
        method=method,
        request_type=request_type,
        request_data=request_data,
        response_type=response_type,
    )


def schedule_job(job: JobModel) -> JobStatus:
    if job.status != JobStatus.DRAFT.value:
        return JobStatus(job.status)
    try:
        if job.scheduled_at:
            job.status = JobStatus.SCHEDULED.value
        else:
            job.scheduled_at = datetime.now()
            job.status = JobStatus.QUEUED.value
        job.save()

        if job.status == JobStatus.QUEUED.value:
            job.enqueued_at = datetime.now()
            queue().enqueue_call(
                execute_job,
                args=(job.id,),
                timeout=job.timeout,
                job_id=str(job.id),
                result_ttl=48 * 3600
            )

    except Exception:
        job.status = JobStatus.DRAFT.value
        job.save()
    return JobStatus(job.status)


def cancel_job(job: JobModel) -> JobStatus:
    if job.status in (JobStatus.SUCCESS.value, JobStatus.FAILURE.value, JobStatus.CANCELLED.value):
        return JobStatus(job.status)

    if job.status in (JobStatus.RUNNING.value, JobStatus.QUEUED.value):
        rq_job = RQJob.fetch(str(job.id), connection=get_redis_client())
        if rq_job:
            if rq_job.is_started:
                send_stop_job_command(get_redis_client(), rq_job.id)
            else:
                rq_job.cancel()

    job.status = JobStatus.CANCELLED.value
    job.ended_at = datetime.now()
    job.save()
    return JobStatus(job.status)

def acknowledge_job(job_id:int) -> None:
    JobModel.update(acknowledged=1).where(JobModel.id == job_id).execute()

