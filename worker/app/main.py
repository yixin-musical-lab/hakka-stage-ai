import signal
import time
from os import getenv


running = True


def _handle_shutdown(signum: int, _frame: object) -> None:
    """接收 Docker 停止信号，保证 worker 能平滑退出。"""

    global running
    print(f"收到停止信号 {signum}，worker 准备退出。", flush=True)
    running = False


def main() -> None:
    """Python Worker 空服务入口。

    这个进程暂时不消费任务，只负责证明 conda 管理的 worker 服务可以随
    Docker Compose 启动。后续会在这里接入 Redis 队列、大模型调用、媒体处理、
    动作生成、练习纠错和 AI 报告生成。
    """

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    project_name = getenv("PROJECT_NAME", "hakka-stage-ai")
    redis_host = getenv("REDIS_HOST", "redis")
    print(f"{project_name} worker 已启动，等待后续接入任务队列。Redis={redis_host}", flush=True)

    while running:
        time.sleep(30)
        print("worker heartbeat: idle", flush=True)

    print("worker 已退出。", flush=True)


if __name__ == "__main__":
    main()
