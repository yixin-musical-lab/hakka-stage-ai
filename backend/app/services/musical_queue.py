import json
from uuid import UUID

import redis

from app.core.config import get_settings


MUSICAL_SCRIPT_QUEUE = "ai:musical_script"
SONG_ADAPTATION_QUEUE = "ai:song_adaptation"
ROLE_TRAINING_QUEUE = "ai:role_training"


class QueueUnavailableError(RuntimeError):
    """Redis 队列不可用。"""


def _json_default(value: object) -> str:
    """把 UUID 等对象转换成可写入 Redis 的字符串。"""

    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def enqueue_musical_script_task(payload: dict) -> None:
    """把剧本生成任务写入 Redis 队列。"""

    _enqueue(MUSICAL_SCRIPT_QUEUE, payload, "剧本生成任务")


def enqueue_song_adaptation_task(payload: dict) -> None:
    """把唱段适配任务写入 Redis 队列。"""

    _enqueue(SONG_ADAPTATION_QUEUE, payload, "唱段适配任务")


def enqueue_role_training_task(payload: dict) -> None:
    """把分角色训练计划任务写入 Redis 队列。"""

    _enqueue(ROLE_TRAINING_QUEUE, payload, "分角色训练计划任务")


def _enqueue(queue_name: str, payload: dict, task_name: str) -> None:
    """统一写入 Redis 队列，并把 Redis 异常转成业务可读错误。"""

    settings = get_settings()
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        client.rpush(queue_name, json.dumps(payload, ensure_ascii=False, default=_json_default))
    except redis.RedisError as exc:
        raise QueueUnavailableError(f"Redis 队列暂不可用，{task_name}未能入队。") from exc
