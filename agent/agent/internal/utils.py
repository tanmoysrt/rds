from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from agent import ServerConfig


def get_redis_client(async_client=False):
    cls_type = AsyncRedis if async_client else Redis
    return cls_type(port=ServerConfig().redis_port)
