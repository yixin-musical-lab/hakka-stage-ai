from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.workspace_overview import WorkspaceOverviewResponse
from app.services.workspace_overview_service import build_workspace_overview


router = APIRouter(prefix="/api/workspace", tags=["workspace"])


@router.get(
    "/overview",
    response_model=WorkspaceOverviewResponse,
    summary="查询轻量工作空间概览",
    description="返回九个业务模块的记录数量和最近一条基础摘要，不返回正文、编辑稿或模型原始信息。",
)
def get_workspace_overview(db: Session = Depends(get_db)) -> WorkspaceOverviewResponse:
    """为工作中心首页提供一次请求即可读取的轻量概览。"""

    return build_workspace_overview(db)
