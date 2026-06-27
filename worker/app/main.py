import signal
import time
from datetime import datetime
import json
import re
from uuid import UUID

import redis

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.llm_client import LLMClient
from app.models import AiTask, LessonPlan

running = True
LESSON_PLAN_QUEUE = "ai:lesson_plan"


def _handle_shutdown(signum: int, _frame: object) -> None:
    """接收 Docker 停止信号，保证 worker 能平滑退出。"""

    global running
    print(f"收到停止信号 {signum}，worker 准备退出。", flush=True)
    running = False


def main() -> None:
    """Python Worker 服务入口，消费 Redis 中的教案生成任务。"""

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    settings = get_settings()
    init_db()
    redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    llm_client = LLMClient(settings)
    print(
        f"{settings.project_name} worker 已启动，正在监听队列 {LESSON_PLAN_QUEUE}。"
        f"默认 LLM={settings.llm_default_provider}:{settings.llm_default_model}/{settings.llm_default_reasoning_level}",
        flush=True,
    )

    while running:
        try:
            item = redis_client.blpop(LESSON_PLAN_QUEUE, timeout=5)
        except redis.RedisError as exc:
            print(f"Redis 读取失败，5 秒后重试：{exc}", flush=True)
            time.sleep(5)
            continue

        if item is None:
            continue

        _, raw_payload = item
        try:
            payload = json.loads(raw_payload)
            _process_lesson_plan_task(payload, llm_client)
        except Exception as exc:  # noqa: BLE001 - Worker 顶层兜底，避免单个任务拖垮进程。
            print(f"任务处理失败：{type(exc).__name__}: {_safe_error_message(exc)}", flush=True)

    print("worker 已退出。", flush=True)


def _process_lesson_plan_task(payload: dict, llm_client: LLMClient) -> None:
    """处理单个教案生成任务。"""

    task_id = UUID(payload["task_id"])
    lesson_plan_id = UUID(payload["lesson_plan_id"])

    with SessionLocal() as db:
        task = db.get(AiTask, task_id)
        lesson_plan = db.get(LessonPlan, lesson_plan_id)
        if task is None or lesson_plan is None:
            raise RuntimeError("任务或教案记录不存在，无法继续处理。")

        task.status = "RUNNING"
        task.progress = 20
        task.started_at = datetime.utcnow()
        lesson_plan.status = "generating"
        db.commit()

        try:
            content, model_info = llm_client.generate_lesson_plan(task.input_snapshot)
            lesson_plan.content = content
            lesson_plan.title = content["title"]
            lesson_plan.raw_model_info = model_info
            lesson_plan.status = "generated"
            lesson_plan.updated_at = datetime.utcnow()
            task.status = "SUCCESS"
            task.progress = 100
            task.result_id = lesson_plan.id
            task.finished_at = datetime.utcnow()
            db.commit()
            print(f"教案任务完成：task={task_id} lesson_plan={lesson_plan_id}", flush=True)
        except Exception as exc:
            db.rollback()
            task = db.get(AiTask, task_id)
            lesson_plan = db.get(LessonPlan, lesson_plan_id)
            if task is not None:
                task.status = "FAILED"
                task.progress = 100
                task.error_code = type(exc).__name__
                task.error_message = _safe_error_message(exc)
                task.finished_at = datetime.utcnow()
            if lesson_plan is not None:
                lesson_plan.status = "failed"
                lesson_plan.updated_at = datetime.utcnow()
            db.commit()
            raise


def _safe_error_message(exc: Exception) -> str:
    """生成不包含密钥的错误摘要。"""

    message = str(exc).replace("\n", " ").strip()
    if "api key" in message.lower() or "authorization" in message.lower():
        return "大模型鉴权失败，请检查对应供应商 API Key 是否正确，或临时启用 LLM_MOCK_MODE=true 做演示。"
    message = re.sub(r"sk-[A-Za-z0-9_.-]+", "sk-***", message)
    if len(message) > 500:
        message = message[:497] + "..."
    return message or type(exc).__name__


if __name__ == "__main__":
    main()
