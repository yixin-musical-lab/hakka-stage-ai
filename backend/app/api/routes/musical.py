from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.llm_options import is_supported_model, is_supported_reasoning_level, models_for_provider
from app.models import AiTask, MusicalFusionPlan, MusicalProject, MusicalScript, RoleTrainingPlan, SongAdaptation
from app.schemas import (
    MusicalFusionGenerateRequest,
    MusicalFusionGenerateResponse,
    MusicalFusionPlanResponse,
    MusicalFusionPlanSummaryResponse,
    MusicalFusionPlanUpdateRequest,
    MusicalScriptGenerateRequest,
    MusicalScriptGenerateResponse,
    MusicalScriptResponse,
    MusicalScriptSummaryResponse,
    MusicalScriptUpdateRequest,
    RoleTrainingGenerateRequest,
    RoleTrainingGenerateResponse,
    RoleTrainingPlanResponse,
    RoleTrainingPlanSummaryResponse,
    RoleTrainingPlanUpdateRequest,
    SongAdaptationGenerateRequest,
    SongAdaptationGenerateResponse,
    SongAdaptationResponse,
    SongAdaptationSummaryResponse,
    SongAdaptationUpdateRequest,
)
from app.services.musical_queue import (
    QueueUnavailableError,
    enqueue_musical_fusion_task,
    enqueue_musical_script_task,
    enqueue_role_training_task,
    enqueue_song_adaptation_task,
)
from app.services.musical_service import (
    build_project_title,
    delete_musical_fusion_with_related_data,
    delete_musical_script_with_related_data,
    delete_role_training_with_related_data,
    delete_song_adaptation_with_related_data,
    musical_script_summary,
    musical_fusion_summary,
    render_musical_fusion_markdown,
    render_musical_script_markdown,
    render_role_training_markdown,
    render_song_adaptation_markdown,
    role_training_summary,
    song_adaptation_summary,
)
from app.services.rehearsal_storage import RehearsalStorageError

router = APIRouter(prefix="/api", tags=["musical"])


@router.post(
    "/musical-scripts/generate",
    response_model=MusicalScriptGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建歌舞剧剧本生成任务",
)
def generate_musical_script(
    request: MusicalScriptGenerateRequest,
    db: Session = Depends(get_db),
) -> MusicalScriptGenerateResponse:
    """创建剧目草稿、剧本草稿和 M01 AI 异步任务。"""

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
    )

    project = MusicalProject(
        title=build_project_title(request),
        theme=request.theme,
        duration_minutes=request.duration_minutes,
        actor_count=request.actor_count,
        age_group=request.age_group,
        style_requirements=request.style_requirements,
        required_elements=request.required_elements,
        forbidden_content=request.forbidden_content,
    )
    db.add(project)
    db.flush()

    musical_script = MusicalScript(project_id=project.id, title=project.title, status="generating")
    db.add(musical_script)
    db.flush()

    # JSON 模式能确保后续扩展出日期、UUID 等字段时仍可安全写入 JSONB。
    input_snapshot = request.model_dump(mode="json")
    input_snapshot["llm_provider"] = llm_provider
    input_snapshot["llm_model"] = llm_model
    input_snapshot["reasoning_level"] = reasoning_level
    task = AiTask(
        task_type="musical_script.generate",
        status="PENDING",
        progress=5,
        business_id=musical_script.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_musical_script_task(
            {
                "task_id": task.id,
                "musical_script_id": musical_script.id,
                "project_id": project.id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        musical_script.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return MusicalScriptGenerateResponse(
        task_id=task.id,
        musical_script_id=musical_script.id,
        status=task.status,
        message="剧本生成任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get("/musical-scripts", response_model=list[MusicalScriptSummaryResponse], summary="查询已保存剧本列表")
def list_musical_scripts(db: Session = Depends(get_db)) -> list[MusicalScriptSummaryResponse]:
    """按更新时间倒序返回剧本摘要列表。"""

    scripts = db.query(MusicalScript).order_by(desc(MusicalScript.updated_at)).all()
    return [musical_script_summary(script) for script in scripts]


@router.get("/musical-scripts/{musical_script_id}", response_model=MusicalScriptResponse, summary="读取剧本详情")
def get_musical_script(musical_script_id: UUID, db: Session = Depends(get_db)) -> MusicalScriptResponse:
    """返回剧本 AI 初稿和编导编辑稿。"""

    musical_script = db.get(MusicalScript, musical_script_id)
    if musical_script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")
    return musical_script


@router.put("/musical-scripts/{musical_script_id}", response_model=MusicalScriptResponse, summary="保存编导编辑后的剧本")
def update_musical_script(
    musical_script_id: UUID,
    request: MusicalScriptUpdateRequest,
    db: Session = Depends(get_db),
) -> MusicalScriptResponse:
    """保存编导确认或修改后的剧本版本。"""

    musical_script = db.get(MusicalScript, musical_script_id)
    if musical_script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")

    edited_content = request.edited_content.model_dump()
    musical_script.edited_content = edited_content
    musical_script.content = musical_script.content or edited_content
    musical_script.title = request.edited_content.title
    musical_script.status = "reviewed"
    musical_script.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(musical_script)
    return musical_script


@router.get(
    "/musical-scripts/{musical_script_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出剧本 Markdown",
)
def export_musical_script_markdown(musical_script_id: UUID, db: Session = Depends(get_db)) -> PlainTextResponse:
    """导出 Markdown 文本，优先使用编导编辑稿。"""

    musical_script = db.get(MusicalScript, musical_script_id)
    if musical_script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")

    markdown = render_musical_script_markdown(musical_script)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="剧本内容尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.delete(
    "/musical-scripts/{musical_script_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除已保存剧本",
)
def delete_musical_script(musical_script_id: UUID, db: Session = Depends(get_db)) -> Response:
    """删除剧本、关联 AI 任务，并清理无人引用的剧目草稿。"""

    try:
        deleted = delete_musical_script_with_related_data(db, musical_script_id)
    except RehearsalStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/song-adaptations/generate",
    response_model=SongAdaptationGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建唱段适配和歌词改写建议任务",
)
def generate_song_adaptation(
    request: SongAdaptationGenerateRequest,
    db: Session = Depends(get_db),
) -> SongAdaptationGenerateResponse:
    """基于已生成剧本创建 M03-lite 唱段适配任务。"""

    musical_script = db.get(MusicalScript, request.script_id)
    if musical_script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")
    script_content = musical_script.edited_content or musical_script.content
    if not script_content:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="剧本内容尚未生成，无法生成唱段适配建议。")

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
    )

    song_adaptation = SongAdaptation(
        project_id=musical_script.project_id,
        script_id=musical_script.id,
        title=f"{musical_script.title} · 唱段适配建议",
        status="generating",
        source_song=request.source_song,
        related_scene=request.related_scene,
        lyrics_text=request.lyrics_text,
        music_structure=request.music_structure,
        adaptation_goal=request.adaptation_goal,
        singing_roles=request.singing_roles,
        rewrite_intensity=request.rewrite_intensity,
    )
    db.add(song_adaptation)
    db.flush()

    # 把剧本确认稿一并写入任务快照，Worker 无需再次猜测当前剧本上下文。
    input_snapshot = request.model_dump(mode="json")
    input_snapshot["llm_provider"] = llm_provider
    input_snapshot["llm_model"] = llm_model
    input_snapshot["reasoning_level"] = reasoning_level
    input_snapshot["script_title"] = musical_script.title
    input_snapshot["script_content"] = script_content
    task = AiTask(
        task_type="song_adaptation.generate",
        status="PENDING",
        progress=5,
        business_id=song_adaptation.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_song_adaptation_task(
            {
                "task_id": task.id,
                "song_adaptation_id": song_adaptation.id,
                "musical_script_id": musical_script.id,
                "project_id": musical_script.project_id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        song_adaptation.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return SongAdaptationGenerateResponse(
        task_id=task.id,
        song_adaptation_id=song_adaptation.id,
        status=task.status,
        message="唱段适配任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get(
    "/song-adaptations",
    response_model=list[SongAdaptationSummaryResponse],
    summary="查询已保存唱段适配列表",
)
def list_song_adaptations(db: Session = Depends(get_db)) -> list[SongAdaptationSummaryResponse]:
    """按更新时间倒序返回唱段适配摘要列表。"""

    song_adaptations = db.query(SongAdaptation).order_by(desc(SongAdaptation.updated_at)).all()
    return [song_adaptation_summary(song_adaptation) for song_adaptation in song_adaptations]


@router.get(
    "/song-adaptations/{song_adaptation_id}",
    response_model=SongAdaptationResponse,
    summary="读取唱段适配详情",
)
def get_song_adaptation(song_adaptation_id: UUID, db: Session = Depends(get_db)) -> SongAdaptationResponse:
    """返回唱段适配 AI 初稿和音乐负责人编辑稿。"""

    song_adaptation = db.get(SongAdaptation, song_adaptation_id)
    if song_adaptation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="唱段适配不存在。")
    return song_adaptation


@router.put(
    "/song-adaptations/{song_adaptation_id}",
    response_model=SongAdaptationResponse,
    summary="保存编辑后的唱段适配",
)
def update_song_adaptation(
    song_adaptation_id: UUID,
    request: SongAdaptationUpdateRequest,
    db: Session = Depends(get_db),
) -> SongAdaptationResponse:
    """保存音乐负责人或编导确认后的唱段适配版本。"""

    song_adaptation = db.get(SongAdaptation, song_adaptation_id)
    if song_adaptation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="唱段适配不存在。")

    edited_content = request.edited_content.model_dump()
    song_adaptation.edited_content = edited_content
    song_adaptation.content = song_adaptation.content or edited_content
    song_adaptation.title = request.edited_content.title
    song_adaptation.source_song = request.edited_content.source_song
    song_adaptation.related_scene = request.edited_content.related_scene
    song_adaptation.adaptation_goal = request.edited_content.adaptation_goal
    song_adaptation.status = "reviewed"
    song_adaptation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(song_adaptation)
    return song_adaptation


@router.get(
    "/song-adaptations/{song_adaptation_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出唱段适配 Markdown",
)
def export_song_adaptation_markdown(song_adaptation_id: UUID, db: Session = Depends(get_db)) -> PlainTextResponse:
    """导出 Markdown 文本，优先使用编辑确认稿。"""

    song_adaptation = db.get(SongAdaptation, song_adaptation_id)
    if song_adaptation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="唱段适配不存在。")

    markdown = render_song_adaptation_markdown(song_adaptation)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="唱段适配内容尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.delete(
    "/song-adaptations/{song_adaptation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除已保存唱段适配",
)
def delete_song_adaptation(song_adaptation_id: UUID, db: Session = Depends(get_db)) -> Response:
    """删除唱段适配和关联 AI 任务，不删除原始剧本。"""

    deleted = delete_song_adaptation_with_related_data(db, song_adaptation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="唱段适配不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/musical-fusion-plans/generate",
    response_model=MusicalFusionGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建歌舞融合结构建议任务",
)
def generate_musical_fusion_plan(
    request: MusicalFusionGenerateRequest,
    db: Session = Depends(get_db),
) -> MusicalFusionGenerateResponse:
    """基于剧本和 M03 唱段或手工音乐段落创建 M04 异步任务。"""

    musical_script = db.get(MusicalScript, request.script_id)
    if musical_script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")
    script_content = musical_script.edited_content or musical_script.content
    if not script_content:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="剧本内容尚未生成，无法设计歌舞融合结构。")

    musical_project = db.get(MusicalProject, musical_script.project_id)
    if musical_project is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="剧目基础信息不存在，无法设计歌舞融合结构。")

    song_adaptation: SongAdaptation | None = None
    song_adaptation_content: dict | None = None
    source_music_structure = request.manual_music_structure
    source_lyrics_summary = request.manual_lyrics_summary
    music_title = request.manual_music_title.strip() or "手工音乐段落"
    if request.source_mode == "song_adaptation":
        # Schema 已保证 M03 模式一定提供 ID；这里继续校验数据库归属和生成状态。
        song_adaptation = db.get(SongAdaptation, request.song_adaptation_id)
        if song_adaptation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="唱段适配不存在。")
        if song_adaptation.script_id != musical_script.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="唱段适配不属于当前剧本，不能作为本次歌舞融合输入。",
            )
        song_adaptation_content = song_adaptation.edited_content or song_adaptation.content
        if not song_adaptation_content:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="唱段适配内容尚未生成，无法继续。")
        music_title = (
            str(song_adaptation_content.get("source_song") or "").strip()
            or song_adaptation.source_song.strip()
            or song_adaptation.title
        )
        source_music_structure = song_adaptation.music_structure
        source_lyrics_summary = "\n".join(
            str(section.get("adapted_lyrics") or section.get("original_lyrics") or "")
            for section in song_adaptation_content.get("sections", [])
        ).strip()

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
    )

    musical_fusion_plan = MusicalFusionPlan(
        project_id=musical_script.project_id,
        script_id=musical_script.id,
        song_adaptation_id=song_adaptation.id if song_adaptation else None,
        title=f"{musical_script.title} · 歌舞融合建议",
        status="generating",
        source_mode=request.source_mode,
        music_title=music_title,
        related_scene=request.related_scene,
        manual_music_structure=request.manual_music_structure,
        manual_lyrics_summary=request.manual_lyrics_summary,
        actor_count=request.actor_count,
        stage_space=request.stage_space,
        fusion_goal=request.fusion_goal,
        additional_constraints=request.additional_constraints,
    )
    db.add(musical_fusion_plan)
    db.flush()

    # 来源内容在创建任务时冻结，确保老师后续修改剧本或唱段不会改变本次生成语义。
    input_snapshot = request.model_dump(mode="json")
    input_snapshot.update(
        {
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "reasoning_level": reasoning_level,
            "project_title": musical_project.title,
            "project_age_group": musical_project.age_group,
            "script_title": musical_script.title,
            "script_content": script_content,
            "music_title": music_title,
            "source_music_structure": source_music_structure,
            "source_lyrics_summary": source_lyrics_summary,
            "song_adaptation_title": song_adaptation.title if song_adaptation else None,
            "song_adaptation_content": song_adaptation_content,
        }
    )
    task = AiTask(
        task_type="musical_fusion.generate",
        status="PENDING",
        progress=5,
        business_id=musical_fusion_plan.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_musical_fusion_task(
            {
                "task_id": task.id,
                "musical_fusion_plan_id": musical_fusion_plan.id,
                "musical_script_id": musical_script.id,
                "song_adaptation_id": song_adaptation.id if song_adaptation else None,
                "project_id": musical_script.project_id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        musical_fusion_plan.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return MusicalFusionGenerateResponse(
        task_id=task.id,
        musical_fusion_plan_id=musical_fusion_plan.id,
        status=task.status,
        message="歌舞融合任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get(
    "/musical-fusion-plans",
    response_model=list[MusicalFusionPlanSummaryResponse],
    summary="查询已保存歌舞融合方案列表",
)
def list_musical_fusion_plans(db: Session = Depends(get_db)) -> list[MusicalFusionPlanSummaryResponse]:
    """按更新时间倒序返回 M04 摘要列表。"""

    plans = db.query(MusicalFusionPlan).order_by(desc(MusicalFusionPlan.updated_at)).all()
    return [musical_fusion_summary(plan) for plan in plans]


@router.get(
    "/musical-fusion-plans/{musical_fusion_plan_id}",
    response_model=MusicalFusionPlanResponse,
    summary="读取歌舞融合方案详情",
)
def get_musical_fusion_plan(
    musical_fusion_plan_id: UUID,
    db: Session = Depends(get_db),
) -> MusicalFusionPlanResponse:
    """返回 AI 初稿和编导编辑确认稿。"""

    plan = db.get(MusicalFusionPlan, musical_fusion_plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌舞融合方案不存在。")
    return plan


@router.put(
    "/musical-fusion-plans/{musical_fusion_plan_id}",
    response_model=MusicalFusionPlanResponse,
    summary="保存编辑后的歌舞融合方案",
)
def update_musical_fusion_plan(
    musical_fusion_plan_id: UUID,
    request: MusicalFusionPlanUpdateRequest,
    db: Session = Depends(get_db),
) -> MusicalFusionPlanResponse:
    """保存编导确认后的 M04 内容并同步列表摘要字段。"""

    plan = db.get(MusicalFusionPlan, musical_fusion_plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌舞融合方案不存在。")

    edited_content = request.edited_content.model_dump()
    plan.edited_content = edited_content
    plan.content = plan.content or edited_content
    plan.title = request.edited_content.title
    plan.related_scene = request.edited_content.related_scene
    plan.fusion_goal = request.edited_content.fusion_goal
    plan.stage_space = request.edited_content.stage_space
    plan.actor_count = request.edited_content.actor_count
    plan.status = "reviewed"
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


@router.get(
    "/musical-fusion-plans/{musical_fusion_plan_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出歌舞融合方案 Markdown",
)
def export_musical_fusion_markdown(
    musical_fusion_plan_id: UUID,
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    """导出 Markdown 文本，优先使用编导编辑确认稿。"""

    plan = db.get(MusicalFusionPlan, musical_fusion_plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌舞融合方案不存在。")
    markdown = render_musical_fusion_markdown(plan)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="歌舞融合内容尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.delete(
    "/musical-fusion-plans/{musical_fusion_plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除已保存歌舞融合方案",
)
def delete_musical_fusion_plan(
    musical_fusion_plan_id: UUID,
    db: Session = Depends(get_db),
) -> Response:
    """删除 M04 和关联 AI 任务，不删除剧本或唱段适配。"""

    deleted = delete_musical_fusion_with_related_data(db, musical_fusion_plan_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌舞融合方案不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/role-training/generate",
    response_model=RoleTrainingGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="创建分角色训练计划生成任务",
)
def generate_role_training_plan(
    request: RoleTrainingGenerateRequest,
    db: Session = Depends(get_db),
) -> RoleTrainingGenerateResponse:
    """基于已生成剧本创建 M05 分角色训练计划任务。"""

    musical_script = db.get(MusicalScript, request.script_id)
    if musical_script is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="剧本不存在。")
    script_content = musical_script.edited_content or musical_script.content
    if not script_content:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="剧本内容尚未生成，无法生成分角色训练计划。")

    fusion_plan: MusicalFusionPlan | None = None
    fusion_content: dict | None = None
    if request.fusion_plan_id is not None:
        fusion_plan = db.get(MusicalFusionPlan, request.fusion_plan_id)
        if fusion_plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="歌舞融合方案不存在。")
        if fusion_plan.script_id != musical_script.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="歌舞融合方案不属于当前剧本，不能作为训练计划输入。",
            )
        fusion_content = fusion_plan.edited_content or fusion_plan.content
        if not fusion_content:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="歌舞融合内容尚未生成，无法继续。")

    llm_provider, llm_model, reasoning_level = _resolve_llm_options(
        request.llm_provider,
        request.llm_model,
        request.reasoning_level,
    )

    role_training_plan = RoleTrainingPlan(
        project_id=musical_script.project_id,
        script_id=musical_script.id,
        title=f"{musical_script.title} · 分角色训练计划",
        status="generating",
        rehearsal_days=request.rehearsal_days,
        session_minutes=request.session_minutes,
        training_focus=request.training_focus,
        notes=request.notes,
    )
    db.add(role_training_plan)
    db.flush()

    # 使用 JSON 模式把 script_id 这类 UUID 转成字符串，避免写入 PostgreSQL JSONB 时
    # 触发 “Object of type UUID is not JSON serializable”。
    input_snapshot = request.model_dump(mode="json")
    input_snapshot["llm_provider"] = llm_provider
    input_snapshot["llm_model"] = llm_model
    input_snapshot["reasoning_level"] = reasoning_level
    input_snapshot["script_title"] = musical_script.title
    input_snapshot["script_content"] = script_content
    input_snapshot["fusion_plan_title"] = fusion_plan.title if fusion_plan else None
    input_snapshot["fusion_content"] = fusion_content
    task = AiTask(
        task_type="role_training.generate",
        status="PENDING",
        progress=5,
        business_id=role_training_plan.id,
        input_snapshot=input_snapshot,
    )
    db.add(task)
    db.commit()

    try:
        enqueue_role_training_task(
            {
                "task_id": task.id,
                "role_training_plan_id": role_training_plan.id,
                "musical_script_id": musical_script.id,
                "project_id": musical_script.project_id,
                "task_type": task.task_type,
            }
        )
    except QueueUnavailableError as exc:
        task.status = "FAILED"
        task.progress = 100
        task.error_code = "QUEUE_UNAVAILABLE"
        task.error_message = str(exc)
        task.finished_at = datetime.utcnow()
        role_training_plan.status = "failed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return RoleTrainingGenerateResponse(
        task_id=task.id,
        role_training_plan_id=role_training_plan.id,
        status=task.status,
        message="分角色训练计划任务已创建，前端可以通过 task_id 轮询进度。",
    )


@router.get(
    "/role-training-plans",
    response_model=list[RoleTrainingPlanSummaryResponse],
    summary="查询已保存分角色训练计划列表",
)
def list_role_training_plans(db: Session = Depends(get_db)) -> list[RoleTrainingPlanSummaryResponse]:
    """按更新时间倒序返回分角色训练计划摘要列表。"""

    plans = db.query(RoleTrainingPlan).order_by(desc(RoleTrainingPlan.updated_at)).all()
    return [role_training_summary(plan) for plan in plans]


@router.get(
    "/role-training-plans/{role_training_plan_id}",
    response_model=RoleTrainingPlanResponse,
    summary="读取分角色训练计划详情",
)
def get_role_training_plan(role_training_plan_id: UUID, db: Session = Depends(get_db)) -> RoleTrainingPlanResponse:
    """返回分角色训练计划 AI 初稿和老师编辑稿。"""

    role_training_plan = db.get(RoleTrainingPlan, role_training_plan_id)
    if role_training_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分角色训练计划不存在。")
    return role_training_plan


@router.put(
    "/role-training-plans/{role_training_plan_id}",
    response_model=RoleTrainingPlanResponse,
    summary="保存老师编辑后的分角色训练计划",
)
def update_role_training_plan(
    role_training_plan_id: UUID,
    request: RoleTrainingPlanUpdateRequest,
    db: Session = Depends(get_db),
) -> RoleTrainingPlanResponse:
    """保存老师确认或修改后的分角色训练计划。"""

    role_training_plan = db.get(RoleTrainingPlan, role_training_plan_id)
    if role_training_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分角色训练计划不存在。")

    edited_content = request.edited_content.model_dump()
    role_training_plan.edited_content = edited_content
    role_training_plan.content = role_training_plan.content or edited_content
    role_training_plan.title = request.edited_content.title
    role_training_plan.status = "reviewed"
    role_training_plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role_training_plan)
    return role_training_plan


@router.get(
    "/role-training-plans/{role_training_plan_id}/markdown",
    response_class=PlainTextResponse,
    summary="导出分角色训练计划 Markdown",
)
def export_role_training_markdown(role_training_plan_id: UUID, db: Session = Depends(get_db)) -> PlainTextResponse:
    """导出 Markdown 文本，优先使用老师编辑稿。"""

    role_training_plan = db.get(RoleTrainingPlan, role_training_plan_id)
    if role_training_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分角色训练计划不存在。")

    markdown = render_role_training_markdown(role_training_plan)
    if markdown is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="分角色训练计划尚未生成，无法导出。")
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")


@router.delete(
    "/role-training-plans/{role_training_plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除已保存分角色训练计划",
)
def delete_role_training_plan(role_training_plan_id: UUID, db: Session = Depends(get_db)) -> Response:
    """删除分角色训练计划和关联 AI 任务，不删除原始剧本。"""

    deleted = delete_role_training_with_related_data(db, role_training_plan_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分角色训练计划不存在。")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _resolve_llm_options(
    requested_provider: str | None,
    requested_model: str | None,
    requested_reasoning_level: str | None,
) -> tuple[str, str, str]:
    """解析并校验 LLM 供应商、模型和推理强度。"""

    settings = get_settings()
    default_provider = settings.llm_default_provider if settings.llm_default_provider in {"deepseek", "qwen"} else "deepseek"
    llm_provider = requested_provider or default_provider
    if llm_provider not in {"deepseek", "qwen"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的大模型供应商。")

    default_reasoning_level = (
        settings.llm_default_reasoning_level
        if is_supported_reasoning_level(settings.llm_default_reasoning_level)
        else "standard"
    )
    reasoning = requested_reasoning_level or default_reasoning_level
    default_models = models_for_provider(llm_provider)
    default_model = settings.llm_default_model if settings.llm_default_model in default_models else default_models[0]
    llm_model = requested_model or default_model

    if not is_supported_model(llm_provider, llm_model):
        supported_models = "、".join(models_for_provider(llm_provider))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{llm_provider} 不支持模型 {llm_model}，可选模型：{supported_models}。",
        )
    if not is_supported_reasoning_level(reasoning):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的推理强度。")
    return llm_provider, llm_model, reasoning
