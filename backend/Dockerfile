FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS uv-bin

FROM python:3.11-slim

WORKDIR /app

# 后端依赖统一由 uv + pyproject.toml + uv.lock 管理。
# 这里从官方 uv 镜像复制 uv 二进制，再用锁文件同步依赖，保证 Docker 构建和本地开发尽量一致。
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=uv-bin /usr/local/bin/uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 8000

# 当前阶段只启动最小 FastAPI 服务，不启动 worker 或业务任务。
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
