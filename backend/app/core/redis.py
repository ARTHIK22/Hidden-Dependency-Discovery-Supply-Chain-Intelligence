# backend/app/core/redis.py

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def check_redis_connection() -> bool:
    try:
        return bool(redis_client.ping())
    except RedisError as exc:
        logger.warning("Redis unavailable: %s", exc)
        return False
