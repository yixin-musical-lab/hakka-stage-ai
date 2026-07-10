import json
from uuid import UUID

import redis

from app.core.config import get_settings


CLASS_INTERACTION_QUEUE = "ai:class_interaction"


class QueueUnavailableError(RuntimeError):
    """Redis 队列不可用。"""


def _json_default(value: object) -> str:
    """把 UUID 等对象转换成可写入 Redis 的字符串。"""

    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def enqueue_class_interaction_task(payload: dict) -> None:
    """把课堂互动方案生成任务写入独立 Redis 队列。"""

    settings = get_settings()
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.rpush(CLASS_INTERACTION_QUEUE, json.dumps(payload, ensure_ascii=False, default=_json_default))
    except redis.RedisError as exc:
        raise QueueUnavailableError("Redis 队列暂不可用，课堂互动方案生成任务未能入队。") from exc
