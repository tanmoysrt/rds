from rq_scheduler import Scheduler

from server.internal.utils import get_redis_client

RQScheduler = Scheduler(connection=get_redis_client())

