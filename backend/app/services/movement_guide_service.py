from uuid import UUID

from sqlalchemy.orm import Session

from app.models import MovementGuide
from app.schemas import MovementGuideContent, MovementGuideCreateRequest, MovementGuideSummaryResponse


def build_movement_guide_title(request: MovementGuideCreateRequest) -> str:
    """根据动作名称和课程场景构造列表标题。"""

    if request.course_context:
        return f"{request.action_name} · {request.course_context}"
    return f"{request.action_name} · 动作图解"


def build_initial_content(request: MovementGuideCreateRequest) -> dict:
    """根据老师录入信息生成第一版可编辑动作图解。

    这里不是 AI 生成结果，只是帮助老师先获得一份结构化草稿；真正的动作脚本规范化、
    Kimodo 骨骼候选和真人 / 数字人视频生成后续应由 Worker 接入。
    """

    content = MovementGuideContent(
        title=build_movement_guide_title(request),
        action_name=request.action_name,
        action_description=request.action_description,
        course_context=request.course_context,
        beats=request.beats,
        body_direction=request.body_direction,
        difficulty=request.difficulty,
        normalized_motion_script="",
        breakdown_steps=[
            {
                "name": "准备",
                "beats": "开始前",
                "description": request.body_direction or "确认身体朝向、站位和重心。",
                "teacher_cue": "先站稳，再开始动作。",
            },
            {
                "name": request.action_name,
                "beats": request.beats or "按音乐节拍完成",
                "description": request.action_description,
                "teacher_cue": request.teaching_tips or "动作要清楚，节奏要稳定。",
            },
        ],
        rhythm_tips=[request.beats] if request.beats else [],
        common_mistakes=["重心不稳或转身时抢拍。"],
        correction_cues=[request.teaching_tips or "放慢速度，先分解练习，再合音乐。"],
        teaching_tips=[request.teaching_tips] if request.teaching_tips else [],
        media_assets=_initial_media_assets(request),
        teacher_review_notes="第一阶段先保存文字拆解和材料链接；骨骼动画、真人 / 数字人视频需要后续接入 Worker 和云端 GPU 生成。",
    )
    return content.model_dump()


def movement_guide_summary(movement_guide: MovementGuide) -> MovementGuideSummaryResponse:
    """把 ORM 示范材料记录转成列表摘要。"""

    content = movement_guide.edited_content or movement_guide.content or {}
    media_assets = content.get("media_assets", [])
    if not isinstance(media_assets, list):
        media_assets = []
    confirmed_count = sum(1 for item in media_assets if isinstance(item, dict) and item.get("status") == "confirmed")
    return MovementGuideSummaryResponse(
        id=movement_guide.id,
        title=movement_guide.title,
        action_name=movement_guide.action_name,
        course_context=movement_guide.course_context,
        status=movement_guide.status,
        asset_count=len(media_assets),
        confirmed_asset_count=confirmed_count,
        created_at=movement_guide.created_at,
        updated_at=movement_guide.updated_at,
    )


def render_movement_guide_markdown(movement_guide: MovementGuide) -> str | None:
    """把动作图解 / 示范材料渲染成 Markdown 文本。"""

    content = movement_guide.edited_content or movement_guide.content
    if not content:
        return None

    return "\n\n".join(
        [
            f"# {content.get('title', movement_guide.title)}",
            "## 动作说明\n" + _movement_overview_markdown(content),
            "## 动作步骤拆解\n" + _steps_markdown(content.get("breakdown_steps", [])),
            "## 节奏提示\n" + _markdown_list(content.get("rhythm_tips", [])),
            "## 常见错误\n" + _markdown_list(content.get("common_mistakes", [])),
            "## 纠正话术\n" + _markdown_list(content.get("correction_cues", [])),
            "## 教学提示\n" + _markdown_list(content.get("teaching_tips", [])),
            "## 示范材料\n" + _media_assets_markdown(content.get("media_assets", [])),
            "## 老师复核说明\n" + str(content.get("teacher_review_notes", "")),
            "---\n\n生成说明：第一阶段仅保存动作图解和材料链接；AI 动作生成链路待 Worker / 云端 GPU 接入。",
        ]
    )


def delete_movement_guide_with_related_data(db: Session, movement_guide_id: UUID) -> bool:
    """删除动作图解记录。

    当前版本未创建独立文件表，后续接入 MinIO 后再在这里补对象存储清理逻辑。
    """

    movement_guide = db.get(MovementGuide, movement_guide_id)
    if movement_guide is None:
        return False

    db.query(MovementGuide).filter(MovementGuide.id == movement_guide_id).delete(synchronize_session=False)
    db.commit()
    return True


def _initial_media_assets(request: MovementGuideCreateRequest) -> list[dict]:
    """把老师提供的参考材料链接转成统一媒体结构。"""

    assets: list[dict] = []
    if request.reference_video_url:
        assets.append(
            {
                "asset_type": "reference_video",
                "title": "老师参考视频",
                "url": request.reference_video_url,
                "status": "draft",
                "notes": "老师录制或外部提供的动作参考，暂不作为系统确认的标准骨骼示范。",
            }
        )
    if request.digital_human_image_url:
        assets.append(
            {
                "asset_type": "image",
                "title": "数字人形象图",
                "url": request.digital_human_image_url,
                "status": "draft",
                "notes": "后续真人 / 数字人视频生成可复用的形象参考。",
            }
        )
    return assets


def _movement_overview_markdown(content: dict) -> str:
    """渲染动作基础信息。"""

    lines = [
        f"- 动作名称：{content.get('action_name', '')}",
        f"- 动作描述：{content.get('action_description', '')}",
        f"- 适用课程：{content.get('course_context', '') or '未填写'}",
        f"- 动作节拍：{content.get('beats', '') or '未填写'}",
        f"- 身体方向：{content.get('body_direction', '') or '未填写'}",
        f"- 难度要求：{content.get('difficulty', '') or '未填写'}",
    ]
    normalized_motion_script = content.get("normalized_motion_script", "")
    if normalized_motion_script:
        lines.append(f"- 规范动作脚本：{normalized_motion_script}")
    return "\n".join(lines)


def _steps_markdown(items: list[dict]) -> str:
    """渲染动作步骤拆解。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('name', '未命名步骤')}**（{item.get('beats', '') or '未填写节拍'}）")
        lines.append(f"  - 说明：{item.get('description', '')}")
        lines.append(f"  - 口令：{item.get('teacher_cue', '')}")
    return "\n".join(lines)


def _media_assets_markdown(items: list[dict]) -> str:
    """渲染示范视频、骨骼动画和图片材料。"""

    if not items:
        return "- 暂无"
    lines: list[str] = []
    for item in items:
        lines.append(f"- **{item.get('title', '未命名材料')}**（{item.get('asset_type', '')} / {item.get('status', '')}）")
        lines.append(f"  - 地址：{item.get('url', '') or '未填写'}")
        lines.append(f"  - 备注：{item.get('notes', '')}")
    return "\n".join(lines)


def _markdown_list(items: list[str]) -> str:
    """把字符串列表渲染成 Markdown 列表。"""

    if not items:
        return "- 暂无"
    return "\n".join(f"- {item}" for item in items)
