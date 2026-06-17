FROM condaforge/miniforge3:latest

WORKDIR /app

# Worker 后续会承载 torch / mmcv / mmpose / opencv / ffmpeg 等重依赖，
# 因此保留 environment.yml 作为 conda 环境入口，避免污染轻量 FastAPI 后端。
# 当前空骨架按 environment.yml 创建 hakka-worker，保证 Docker 和本地开发使用同一份
# conda 环境定义。后续接 MMPose 时继续在这个文件里扩展重依赖。
COPY environment.yml .
RUN conda config --set remote_connect_timeout_secs 60 \
    && conda config --set remote_read_timeout_secs 1000 \
    && mamba env create -f environment.yml \
    && conda clean -afy

COPY app ./app

# 当前只是空服务骨架：启动一个常驻 worker 进程，后续再接 Redis 队列和 AI/媒体任务。
CMD ["conda", "run", "--no-capture-output", "-n", "hakka-worker", "python", "-m", "app.main"]
