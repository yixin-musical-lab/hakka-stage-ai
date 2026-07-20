from typing import Any

from sqlalchemy import func, literal, select, union_all
from sqlalchemy.orm import Session

from app.models import (
    ClassInteraction,
    LessonPlan,
    MovementGuide,
    MusicalFusionPlan,
    MusicalScript,
    PracticeSubmission,
    RehearsalReview,
    RoleTrainingPlan,
    SongAdaptation,
)
from app.schemas.workspace_overview import (
    WorkspaceLatestItem,
    WorkspaceModuleOverview,
    WorkspaceOverviewResponse,
)


# 首页需要的九类资源都只读取基础摘要列。这里集中声明映射，后续新增模块时可以在同一处补齐，
# 避免路由层复制查询或误把 content、edited_content 等大字段加载到内存。
_MODULE_COLUMNS = (
    ("lesson_plans", LessonPlan.id, LessonPlan.title, LessonPlan.status, LessonPlan.updated_at),
    (
        "class_interactions",
        ClassInteraction.id,
        ClassInteraction.title,
        ClassInteraction.status,
        ClassInteraction.updated_at,
    ),
    ("musical_scripts", MusicalScript.id, MusicalScript.title, MusicalScript.status, MusicalScript.updated_at),
    (
        "song_adaptations",
        SongAdaptation.id,
        SongAdaptation.title,
        SongAdaptation.status,
        SongAdaptation.updated_at,
    ),
    (
        "musical_fusion_plans",
        MusicalFusionPlan.id,
        MusicalFusionPlan.title,
        MusicalFusionPlan.status,
        MusicalFusionPlan.updated_at,
    ),
    (
        "role_training_plans",
        RoleTrainingPlan.id,
        RoleTrainingPlan.title,
        RoleTrainingPlan.status,
        RoleTrainingPlan.updated_at,
    ),
    ("movement_guides", MovementGuide.id, MovementGuide.title, MovementGuide.status, MovementGuide.updated_at),
    (
        "practice_submissions",
        PracticeSubmission.id,
        PracticeSubmission.task_title,
        PracticeSubmission.status,
        PracticeSubmission.updated_at,
    ),
    (
        "rehearsal_reviews",
        RehearsalReview.id,
        RehearsalReview.title,
        RehearsalReview.status,
        RehearsalReview.updated_at,
    ),
)


def build_workspace_overview(db: Session) -> WorkspaceOverviewResponse:
    """查询九个业务模块的总数和最近一条基础摘要。

    所有模块通过一条 UNION ALL SQL 返回，减少首页接口的数据库往返次数。每个模块内部
    使用窗口计数，并在排序后只保留最新一条；查询不会选择结构化正文或模型原始信息。
    """

    # 空表在 UNION 结果中不会产生行，因此先为全部模块准备明确的空状态。
    overviews = {
        module_name: WorkspaceModuleOverview(count=0, latest=None)
        for module_name, *_columns in _MODULE_COLUMNS
    }

    rows = db.execute(_build_workspace_overview_statement()).mappings().all()
    for row in rows:
        module_name = row["module"]
        overviews[module_name] = WorkspaceModuleOverview(
            count=int(row["total_count"]),
            latest=WorkspaceLatestItem(
                id=row["id"],
                title=row["title"],
                status=row["status"],
                updated_at=row["updated_at"],
            ),
        )

    return WorkspaceOverviewResponse(**overviews)


def _build_workspace_overview_statement():
    """构造单次执行的概览查询，独立函数便于验证查询不会带出大字段。"""

    module_selects = [
        _build_module_latest_select(module_name, id_column, title_column, status_column, updated_at_column)
        for module_name, id_column, title_column, status_column, updated_at_column in _MODULE_COLUMNS
    ]
    return union_all(*module_selects)


def _build_module_latest_select(
    module_name: str,
    id_column: Any,
    title_column: Any,
    status_column: Any,
    updated_at_column: Any,
):
    """为一个模块生成“总数 + 最新一条”的子查询。"""

    latest_row = (
        select(
            id_column.label("id"),
            title_column.label("title"),
            status_column.label("status"),
            updated_at_column.label("updated_at"),
            func.count(id_column).over().label("total_count"),
        )
        # 更新时间相同时使用 UUID 作为稳定排序条件，避免连续刷新时最新条目来回变化。
        .order_by(updated_at_column.desc(), id_column.desc())
        .limit(1)
        .subquery(f"{module_name}_latest")
    )

    return select(
        literal(module_name).label("module"),
        latest_row.c.total_count,
        latest_row.c.id,
        latest_row.c.title,
        latest_row.c.status,
        latest_row.c.updated_at,
    )
