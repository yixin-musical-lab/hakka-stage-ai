# Python Worker

本目录是客韵智演的 Python Worker 服务骨架。Worker 后续负责大模型调用、媒体处理、动作生成、练习纠错和 AI 报告生成。

## 依赖管理

Worker 使用 Miniforge / conda 管理依赖，原因是后续会接入 `torch`、`mmcv`、`mmpose`、`opencv`、`ffmpeg` 等重依赖，这类包和 CUDA / 驱动版本强相关，不适合混进轻量 FastAPI 后端。

当前 `environment.yml` 只保留最小 Python 环境：

```powershell
conda env create -f environment.yml
conda activate hakka-worker
python -m app.main
```

后续接入 MMPose 时，再在这个环境中补充 PyTorch、MMEngine、MMCV、MMPose 等依赖，并单独记录 CUDA / PyTorch / MMCV 版本矩阵。

## Docker 骨架说明

当前 Dockerfile 使用 Miniforge 基础镜像，并按 `environment.yml` 创建 `hakka-worker` 命名环境来启动空 worker，占位验证 Docker Compose 服务链路。
