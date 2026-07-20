from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkspaceLatestItem(BaseModel):
    """工作空间中某个模块最近更新的一条基础摘要。"""

    id: UUID = Field(..., description="业务记录 ID，用于前端进入对应详情页")
    title: str = Field(..., description="业务记录标题；练习模块使用练习任务标题")
    status: str = Field(..., description="当前业务状态，例如 generating、generated 或 reviewed")
    updated_at: datetime = Field(..., description="最近更新时间")


class WorkspaceModuleOverview(BaseModel):
    """单个业务模块的轻量统计。"""

    count: int = Field(..., ge=0, description="该模块当前保存的记录总数")
    latest: WorkspaceLatestItem | None = Field(None, description="最近更新的一条记录；模块为空时返回 null")


class WorkspaceOverviewResponse(BaseModel):
    """首页工作空间概览。

    只返回各模块数量和最近一条基础摘要，不携带正文、编辑稿或模型原始信息，
    避免首页为了统计和最近更新列表加载全部业务数据。
    """

    lesson_plans: WorkspaceModuleOverview = Field(..., description="教案模块概览")
    class_interactions: WorkspaceModuleOverview = Field(..., description="课堂互动模块概览")
    musical_scripts: WorkspaceModuleOverview = Field(..., description="歌舞剧剧本模块概览")
    song_adaptations: WorkspaceModuleOverview = Field(..., description="唱段适配模块概览")
    musical_fusion_plans: WorkspaceModuleOverview = Field(..., description="歌舞融合模块概览")
    role_training_plans: WorkspaceModuleOverview = Field(..., description="分角色训练模块概览")
    movement_guides: WorkspaceModuleOverview = Field(..., description="动作图解与示范材料模块概览")
    practice_submissions: WorkspaceModuleOverview = Field(..., description="课后练习提交模块概览")
    rehearsal_reviews: WorkspaceModuleOverview = Field(..., description="排练复盘模块概览")
