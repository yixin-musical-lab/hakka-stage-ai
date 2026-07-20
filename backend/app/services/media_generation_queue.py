import json
from datetime import date, datetime
from uuid import UUID

import redis

from app.core.config import get_settings


MEDIA_GENERATION_QUEUE = "ai:media_generation"


class QueueUnavailableError(RuntimeError):
    """Redis 不可用时转换成稳定的业务异常。"""


def _json_default(value: object) -> str:
    if isinstance(value, (datetime, date, UUID)):
        return str(value)
    raise TypeError(f"无法序列化 {type(value).__name__}")


def enqueue_media_task(payload: dict) -> None:
    """将媒体提交、取消或刷新动作写入统一队列。"""

    settings = get_settings()
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.rpush(MEDIA_GENERATION_QUEUE, json.dumps(payload, ensure_ascii=False, default=_json_default))
    except redis.RedisError as exc:
        raise QueueUnavailableError("Redis 队列暂不可用，媒体任务未能入队") from exc
