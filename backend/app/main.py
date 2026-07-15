from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.services.account_bootstrap import ensure_bootstrap_account

settings = get_settings()


def _split_cors_origins(raw_value: str | None) -> list[str]:
    """把逗号分隔的 CORS 配置转成列表，兼容本地和 Docker 两种启动方式。"""

    if not raw_value:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def _local_dev_cors_regex() -> str:
    """允许本地开发常见来源访问 API。

    Vite 用 --host 0.0.0.0 启动后，浏览器可能通过 localhost、127.0.0.1
    或局域网 / Docker / WSL 网段 IP 访问前端。这里仅放开这些私有地址段，
    方便小组联调；正式部署时应改为明确域名白名单。
    """

    return (
        r"^https?://("
        r"localhost|"
        r"127\.0\.0\.1|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|"
        r"192\.168\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?$"
    )


app = FastAPI(
    title="客韵智演 API",
    description="AI 歌舞剧教学与排演辅助系统的 FastAPI 服务，提供账号鉴权、教案生成、课堂互动、创编排练、示范材料和课后练习等接口。",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_split_cors_origins(settings.cors_origins),
    allow_origin_regex=_local_dev_cors_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# T06 练习视频仍保存在开发期本地目录，并通过 /uploads 暴露给前端预览和回填。
# M08 排练复盘视频已单独使用 MinIO 私有桶和后端代理接口，两条链路暂不混改。
upload_dir = Path(settings.practice_upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

app.include_router(api_router)


@app.on_event("startup")
def startup() -> None:
    """服务启动时初始化开发期数据表，并按需创建首个登录账号。"""

    init_db()
    ensure_bootstrap_account()
