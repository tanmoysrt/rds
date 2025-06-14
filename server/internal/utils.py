from redis import Redis

from server import ServerConfig


def get_redis_client():
    return Redis(port=ServerConfig().redis_port)
