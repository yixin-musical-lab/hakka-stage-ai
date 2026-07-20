from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser
from app.core.config import get_settings
from app.core.database import get_db
from app.models import (
    AiTask,
    MediaAsset,
    MediaGeneration,
    MediaWorkbenchConfig,
    ProviderTaskRun,
    WorkflowTemplate,
    WorkflowTemplateVersion,
)
from app.schemas.media_generation import (
    MediaAssetResponse,
    MediaAssetUploadResponse,
    MediaGenerationCreateRequest,
    MediaGenerationResponse,
    MediaProviderOption,
    MediaProviderOptionsResponse,
    MediaWorkbenchConfigResponse,
    MediaWorkbenchConfigUpdateRequest,
    MediaWorkbenchInputConfig,
    MediaWorkbenchRunRequest,
    ProviderTaskRunResponse,
    WorkflowTemplateResponse,
    WorkflowTemplateUpdateRequest,
    WorkflowVersionConfigureRequest,
    WorkflowVersionResponse,
)
from app.services.media_generation_queue import QueueUnavailableError, enqueue_media_task
from app.services.media_workbench_service import (
    ensure_default_workbenches,
    get_workbench,
    validate_workbench_configuration,
    validate_workflow_mapping,
)
from app.services.media_storage import (
    MediaStorageError,
    iter_media_object,
    open_media_object,
    save_media_upload,
    stat_media_object,
)
from app.services.workflow_analyzer import (
    WorkflowAnalysisError,
    analyze_workflow,
    parse_workflow_json,
    workflow_sha256,
)


router = APIRouter(prefix="/api", tags=["媒体生成与供应商"])


def _asset_response(asset: MediaAsset) -> MediaAssetResponse:
    url = asset.external_url if asset.storage_mode == "external" else f"/api/media-assets/{asset.id}/content"
    return MediaAssetResponse(
        id=asset.id, role=asset.role, media_type=asset.media_type, storage_mode=asset.storage_mode,
        url=url, original_file_name=asset.original_file_name, content_type=asset.content_type,
        size_bytes=asset.size_bytes, provider=asset.provider, status=asset.status, created_at=asset.created_at,
    )


def _generation_response(db: Session, record: MediaGeneration) -> MediaGenerationResponse:
    runs = db.scalars(
        select(ProviderTaskRun).where(ProviderTaskRun.generation_id == record.id).order_by(ProviderTaskRun.created_at)
    ).all()
    assets = db.scalars(
        select(MediaAsset).where(MediaAsset.generation_id == record.id).order_by(MediaAsset.created_at)
    ).all()
    task = db.scalar(
        select(AiTask).where(AiTask.business_id == record.id, AiTask.task_type == "media_generation.run")
    )
    return MediaGenerationResponse(
        id=record.id, task_id=task.id if task else None, title=record.title,
        workbench_slug=record.workbench_slug, provider=record.provider,
        capability=record.capability, model=record.model, workflow_version_id=record.workflow_version_id,
        status=record.status, prompt=record.prompt, parameters=record.request_parameters,
        input_asset_ids={key: UUID(value) for key, value in record.input_bindings.items()},
        runs=[ProviderTaskRunResponse.model_validate(item) for item in runs],
        assets=[_asset_response(item) for item in assets], created_at=record.created_at,
        updated_at=record.updated_at, finished_at=record.finished_at,
    )


def _get_generation(db: Session, generation_id: UUID, owner_id: UUID) -> MediaGeneration:
    record = db.scalar(
        select(MediaGeneration).where(MediaGeneration.id == generation_id, MediaGeneration.owner_id == owner_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail="媒体任务不存在")
    return record


def _require_teacher(current_user) -> None:
    """工作台和供应商配置会影响全平台用户，只允许教师修改。"""

    if current_user.role != "teacher":
        raise HTTPException(status_code=403, detail="只有教师账号可以修改媒体工作台配置")


def _validate_runninghub_audio_asset(asset: MediaAsset, label: str) -> None:
    """在任务入队前拦截 RunningHub 上传接口不支持的音频格式。

    通用媒体资产允许保存更多音频格式，但 RunningHub 当前文件上传文档只列出 MP3、WAV、FLAC。
    把校验放在 API 层可以立即给用户明确提示，避免等到 Worker 异步提交后才显示供应商错误。
    """

    suffix = Path(asset.original_file_name).suffix.lower()
    if suffix not in {".mp3", ".wav", ".flac"}:
        raise HTTPException(status_code=400, detail=f"{label}仅支持 MP3、WAV 或 FLAC 格式")


def _create_generation_record(
    db: Session,
    request: MediaGenerationCreateRequest,
    owner_id: UUID,
    workbench_slug: str = "",
) -> MediaGenerationResponse:
    """统一创建数据库记录和 Redis 任务，供通用接口与专注工作台复用。"""

    if request.client_request_id:
        existing = db.scalar(
            select(MediaGeneration).where(
                MediaGeneration.owner_id == owner_id,
                MediaGeneration.client_request_id == request.client_request_id,
            )
        )
        if existing:
            return _generation_response(db, existing)

    bindings: dict[str, str] = {}
    for key, asset_id in request.input_asset_ids.items():
        asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.owner_id == owner_id))
        if asset is None or asset.status != "AVAILABLE":
            raise HTTPException(status_code=400, detail=f"输入资产 {key} 不存在或不可用")
        bindings[key] = str(asset_id)

    generation = MediaGeneration(
        title=request.title or (request.prompt[:40] if request.prompt else "媒体生成任务"),
        workbench_slug=workbench_slug, provider=request.provider, capability=request.capability, model=request.model,
        workflow_version_id=request.workflow_version_id, prompt=request.prompt,
        request_parameters=request.parameters, input_bindings=bindings,
        client_request_id=request.client_request_id, owner_id=owner_id,
    )
    db.add(generation)
    db.flush()
    run = ProviderTaskRun(generation_id=generation.id, provider=request.provider)
    snapshot = request.model_dump(mode="json")
    snapshot["workbench_slug"] = workbench_slug
    task = AiTask(
        task_type="media_generation.run", business_id=generation.id, input_snapshot=snapshot,
        created_by=str(owner_id), max_retries=1,
    )
    db.add_all([run, task])
    db.commit()
    try:
        enqueue_media_task({"task_type": "media_generation.run", "task_id": task.id, "generation_id": generation.id})
    except QueueUnavailableError as exc:
        generation.status = task.status = "FAILED"
        run.provider_status = "FAILED"
        run.error_code = task.error_code = "QUEUE_UNAVAILABLE"
        run.error_message = task.error_message = str(exc)
        generation.finished_at = task.finished_at = run.finished_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _generation_response(db, generation)


@router.get(
    "/media-providers", response_model=MediaProviderOptionsResponse,
    summary="查询媒体生成供应商与可用能力",
)
def get_media_provider_options() -> MediaProviderOptionsResponse:
    settings = get_settings()
    return MediaProviderOptionsResponse(
        mock_mode=settings.media_mock_mode,
        providers=[
            MediaProviderOption(
                key="grsai", label="GRS AI", configured=bool(settings.grsai_api_key) or settings.media_mock_mode,
                capabilities=["image"], storage_policy="生成结果转存 MinIO",
                models=["nano-banana-fast", "nano-banana-2-lite", "nano-banana-2", "nano-banana-pro"],
            ),
            MediaProviderOption(
                key="runninghub", label="RunningHub", configured=bool(settings.runninghub_api_key) or settings.media_mock_mode,
                capabilities=["image", "video", "audio"], storage_policy="沿用供应商结果 URL",
            ),
        ],
    )


def _workbench_response(db: Session, record: MediaWorkbenchConfig) -> MediaWorkbenchConfigResponse:
    settings = get_settings()
    provider_configured = bool(
        settings.grsai_api_key if record.provider == "grsai" else settings.runninghub_api_key
    )
    issues = validate_workbench_configuration(
        db,
        record,
        grsai_configured=bool(settings.grsai_api_key),
        runninghub_configured=bool(settings.runninghub_api_key),
        mock_mode=settings.media_mock_mode,
    )
    workflow_parameters = []
    if record.workflow_version_id:
        version = db.get(WorkflowTemplateVersion, record.workflow_version_id)
        if version:
            workflow_parameters = version.parameter_config
    return MediaWorkbenchConfigResponse(
        id=record.id,
        slug=record.slug,
        display_name=record.display_name,
        description=record.description,
        provider=record.provider,
        capability=record.capability,
        workflow_version_id=record.workflow_version_id,
        model=record.model,
        provider_api_mode=record.provider_api_mode,
        default_parameters=record.default_parameters,
        input_config=MediaWorkbenchInputConfig.model_validate(record.input_config),
        enabled=record.enabled,
        provider_configured=provider_configured,
        configured=not issues,
        configuration_issues=issues,
        workflow_parameters=workflow_parameters,
        updated_at=record.updated_at,
    )


@router.get(
    "/media-workbenches",
    response_model=list[MediaWorkbenchConfigResponse],
    summary="查询面向用户的媒体工作台",
    description="返回克隆音频和图生图两个专注工作台及其配置状态，不返回任何 API Key。",
)
def list_media_workbenches(db: Session = Depends(get_db)) -> list[MediaWorkbenchConfigResponse]:
    return [_workbench_response(db, record) for record in ensure_default_workbenches(db)]


@router.get(
    "/media-workbenches/{slug}",
    response_model=MediaWorkbenchConfigResponse,
    summary="查询单个媒体工作台的运行表单配置",
)
def get_media_workbench(slug: str, db: Session = Depends(get_db)) -> MediaWorkbenchConfigResponse:
    record = get_workbench(db, slug)
    if record is None:
        raise HTTPException(status_code=404, detail="媒体工作台不存在")
    return _workbench_response(db, record)


@router.put(
    "/media-workbenches/{slug}/configuration",
    response_model=MediaWorkbenchConfigResponse,
    summary="配置媒体工作台绑定的工作流或 GRS AI 模型",
    description="仅教师可修改；API Key 仍由服务端环境变量管理。",
)
def update_media_workbench_configuration(
    slug: str,
    request: MediaWorkbenchConfigUpdateRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> MediaWorkbenchConfigResponse:
    _require_teacher(current_user)
    record = get_workbench(db, slug)
    if record is None:
        raise HTTPException(status_code=404, detail="媒体工作台不存在")
    input_config = request.input_config.model_dump(mode="json")
    try:
        if slug == "audio-clone":
            if request.provider_api_mode != "workflow":
                raise ValueError("克隆音频工作台必须使用 RunningHub workflow 模式")
            validate_workflow_mapping(db, request.workflow_version_id, input_config)
        elif slug == "image-to-image":
            if request.provider_api_mode != "unified":
                raise ValueError("图生图工作台必须使用 GRS AI unified 接口")
            if not request.model:
                raise ValueError("请选择 GRS AI 模型")
            if input_config["primary_asset"].get("media_type") != "image":
                raise ValueError("图生图主输入必须是图片")
            input_config["primary_asset"]["target_parameter_key"] = "source_image"
        else:
            raise ValueError("未知工作台类型")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record.display_name = request.display_name
    record.description = request.description
    record.workflow_version_id = request.workflow_version_id if slug == "audio-clone" else None
    record.model = request.model if slug == "image-to-image" else ""
    record.provider_api_mode = request.provider_api_mode
    record.default_parameters = request.default_parameters
    record.input_config = input_config
    record.enabled = request.enabled
    record.updated_by = current_user.id
    db.commit()
    db.refresh(record)
    return _workbench_response(db, record)


@router.post(
    "/media-workbenches/{slug}/runs",
    response_model=MediaGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="从专注工作台创建媒体任务",
    description="根据教师已保存的绑定配置组装供应商参数，用户无需理解模型或工作流节点。",
)
def run_media_workbench(
    slug: str,
    request: MediaWorkbenchRunRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> MediaGenerationResponse:
    record = get_workbench(db, slug)
    if record is None:
        raise HTTPException(status_code=404, detail="媒体工作台不存在")
    response = _workbench_response(db, record)
    if not response.configured:
        raise HTTPException(status_code=409, detail="；".join(response.configuration_issues))

    input_config = record.input_config
    primary_config = input_config["primary_asset"]
    primary_asset = db.scalar(
        select(MediaAsset).where(MediaAsset.id == request.primary_asset_id, MediaAsset.owner_id == current_user.id)
    )
    if primary_asset is None or primary_asset.media_type != primary_config.get("media_type"):
        raise HTTPException(status_code=400, detail=f"请上传有效的{primary_config.get('label', '主输入文件')}")
    if slug == "audio-clone":
        _validate_runninghub_audio_asset(primary_asset, primary_config.get("label", "参考音频"))
    if slug == "image-to-image" and (primary_asset.size_bytes or 0) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="GRS AI 图生图参考图片不能超过 12MB")

    allowed_keys = set(input_config.get("exposed_parameter_keys", []))
    unknown_keys = set(request.parameters) - allowed_keys
    if unknown_keys:
        raise HTTPException(status_code=400, detail=f"包含未开放参数：{', '.join(sorted(unknown_keys))}")
    parameters = dict(record.default_parameters or {})
    parameters.update(request.parameters)
    bindings: dict[str, UUID] = {}

    if slug == "audio-clone":
        prompt_key = input_config["prompt"]["target_parameter_key"]
        primary_key = primary_config["target_parameter_key"]
        parameters[prompt_key] = request.prompt
        bindings[primary_key] = request.primary_asset_id
        version = db.get(WorkflowTemplateVersion, record.workflow_version_id)
        if version:
            # 把已发布版本的输出选择固化进任务，后续教师修改工作台不会改变历史任务语义。
            parameters["_enabled_output_nodes"] = [
                str(item["node_id"]) for item in version.output_config if item.get("enabled")
            ]
        secondary_config = input_config.get("secondary_asset")
        if secondary_config:
            secondary_key = secondary_config.get("target_parameter_key")
            if secondary_key and not secondary_config.get("required"):
                # 已映射但非必填的文件节点在 Worker 中允许缺省，此时 RunningHub 沿用工作流平台默认值。
                parameters["_optional_file_keys"] = [secondary_key]
            if secondary_config.get("required") and request.secondary_asset_id is None:
                raise HTTPException(status_code=400, detail=f"请上传{secondary_config.get('label', '第二输入文件')}")
            if request.secondary_asset_id:
                secondary_asset = db.scalar(
                    select(MediaAsset).where(
                        MediaAsset.id == request.secondary_asset_id,
                        MediaAsset.owner_id == current_user.id,
                    )
                )
                if secondary_asset is None or secondary_asset.media_type != secondary_config.get("media_type"):
                    raise HTTPException(status_code=400, detail=f"请上传有效的{secondary_config.get('label', '第二输入文件')}")
                _validate_runninghub_audio_asset(secondary_asset, secondary_config.get("label", "第二输入音频"))
                if not secondary_key:
                    raise HTTPException(status_code=409, detail="情绪参考尚未映射到工作流字段")
                bindings[secondary_key] = request.secondary_asset_id
    else:
        bindings[primary_config["target_parameter_key"]] = request.primary_asset_id
        parameters["_api_mode"] = record.provider_api_mode

    generation_request = MediaGenerationCreateRequest(
        title=f"{record.display_name} · {request.prompt[:32]}",
        provider=record.provider,
        capability=record.capability,
        model=record.model,
        workflow_version_id=record.workflow_version_id,
        prompt=request.prompt,
        parameters=parameters,
        input_asset_ids=bindings,
        client_request_id=request.client_request_id,
    )
    return _create_generation_record(db, generation_request, current_user.id, workbench_slug=slug)


@router.post(
    "/media-assets/upload", response_model=MediaAssetUploadResponse, status_code=status.HTTP_201_CREATED,
    summary="上传媒体输入到 MinIO",
    description="上传图片、音频或视频，返回可绑定到 GRS AI / RunningHub 任务的媒体资产 ID。",
)
def upload_media_asset(
    current_user: CurrentUser, file: UploadFile = File(..., description="图片、音频或视频文件"),
    db: Session = Depends(get_db),
) -> MediaAssetUploadResponse:
    settings = get_settings()
    try:
        stored = save_media_upload(file, settings)
    except MediaStorageError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    asset = MediaAsset(
        role="input", media_type=stored.media_type, storage_mode="managed", bucket=settings.minio_bucket,
        object_key=stored.object_key, original_file_name=stored.original_file_name,
        content_type=stored.content_type, size_bytes=stored.size_bytes, owner_id=current_user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return MediaAssetUploadResponse(asset=_asset_response(asset))


@router.get("/media-assets/{asset_id}/content", summary="读取受管媒体内容")
def get_media_asset_content(
    asset_id: UUID, request: Request, current_user: CurrentUser, db: Session = Depends(get_db),
):
    asset = db.scalar(select(MediaAsset).where(MediaAsset.id == asset_id, MediaAsset.owner_id == current_user.id))
    if asset is None:
        raise HTTPException(status_code=404, detail="媒体资产不存在")
    if asset.storage_mode == "external":
        if not asset.external_url:
            raise HTTPException(status_code=404, detail="供应商结果 URL 为空")
        return RedirectResponse(asset.external_url, status_code=307)
    settings = get_settings()
    try:
        size, content_type = stat_media_object(asset.object_key, settings)
        range_header = request.headers.get("range")
        if range_header and range_header.startswith("bytes=") and "," not in range_header:
            start_text, end_text = range_header.removeprefix("bytes=").split("-", 1)
            start = int(start_text) if start_text else 0
            end = min(int(end_text) if end_text else size - 1, size - 1)
            if start < 0 or end < start or start >= size:
                raise ValueError
            response = open_media_object(asset.object_key, settings, start, end - start + 1)
            return StreamingResponse(
                iter_media_object(response), status_code=206, media_type=content_type,
                headers={"Accept-Ranges": "bytes", "Content-Range": f"bytes {start}-{end}/{size}", "Content-Length": str(end-start+1)},
            )
        response = open_media_object(asset.object_key, settings)
        return StreamingResponse(
            iter_media_object(response), media_type=content_type,
            headers={"Accept-Ranges": "bytes", "Content-Length": str(size)},
        )
    except (MediaStorageError, ValueError) as exc:
        code = exc.status_code if isinstance(exc, MediaStorageError) else 416
        raise HTTPException(status_code=code, detail=str(exc) or "字节范围无效") from exc


@router.post(
    "/media-generations", response_model=MediaGenerationResponse, status_code=status.HTTP_202_ACCEPTED,
    summary="创建统一媒体生成任务",
    description="写入本地任务与供应商运行记录后异步提交；不会在 HTTP 请求中长时间等待供应商。",
)
def create_media_generation(
    request: MediaGenerationCreateRequest, current_user: CurrentUser, db: Session = Depends(get_db),
) -> MediaGenerationResponse:
    if request.provider == "runninghub":
        version = db.scalar(
            select(WorkflowTemplateVersion).where(
                WorkflowTemplateVersion.id == request.workflow_version_id,
                WorkflowTemplateVersion.owner_id == current_user.id,
                WorkflowTemplateVersion.status == "published",
            )
        )
        if version is None:
            raise HTTPException(status_code=400, detail="RunningHub 工作流版本不存在、未发布或无权使用")
    return _create_generation_record(db, request, current_user.id)


@router.get("/media-generations", response_model=list[MediaGenerationResponse], summary="查询当前账号的媒体任务")
def list_media_generations(
    current_user: CurrentUser,
    workbench_slug: str | None = None,
    db: Session = Depends(get_db),
) -> list[MediaGenerationResponse]:
    query = select(MediaGeneration).where(MediaGeneration.owner_id == current_user.id)
    if workbench_slug:
        query = query.where(MediaGeneration.workbench_slug == workbench_slug)
    records = db.scalars(query.order_by(MediaGeneration.created_at.desc()).limit(100)).all()
    return [_generation_response(db, item) for item in records]


@router.get("/media-generations/{generation_id}", response_model=MediaGenerationResponse, summary="查询媒体任务详情")
def get_media_generation(generation_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)) -> MediaGenerationResponse:
    return _generation_response(db, _get_generation(db, generation_id, current_user.id))


@router.post("/media-generations/{generation_id}/cancel", response_model=MediaGenerationResponse, summary="取消媒体生成任务")
def cancel_media_generation(generation_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)) -> MediaGenerationResponse:
    record = _get_generation(db, generation_id, current_user.id)
    if record.status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
        return _generation_response(db, record)
    record.status = "CANCEL_REQUESTED"
    run = db.scalar(select(ProviderTaskRun).where(ProviderTaskRun.generation_id == record.id))
    if run:
        run.provider_status = "CANCEL_REQUESTED"
    db.commit()
    enqueue_media_task({"task_type": "media_generation.cancel", "generation_id": record.id})
    return _generation_response(db, record)


@router.post("/media-generations/{generation_id}/refresh", response_model=MediaGenerationResponse, summary="立即刷新供应商任务结果")
def refresh_media_generation(generation_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)) -> MediaGenerationResponse:
    record = _get_generation(db, generation_id, current_user.id)
    run = db.scalar(select(ProviderTaskRun).where(ProviderTaskRun.generation_id == record.id))
    if run and record.status not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
        run.next_poll_at = datetime.utcnow()
        db.commit()
        enqueue_media_task({"task_type": "media_generation.poll", "generation_id": record.id})
    return _generation_response(db, record)


def _version_response(version: WorkflowTemplateVersion) -> WorkflowVersionResponse:
    return WorkflowVersionResponse(
        id=version.id, template_id=version.template_id, version_number=version.version_number,
        source_filename=version.source_filename, workflow_hash=version.workflow_hash, analysis=version.analysis,
        parameters=version.parameter_config, outputs=version.output_config, status=version.status,
        created_at=version.created_at, published_at=version.published_at,
    )


def _template_response(db: Session, template: WorkflowTemplate) -> WorkflowTemplateResponse:
    versions = db.scalars(
        select(WorkflowTemplateVersion).where(WorkflowTemplateVersion.template_id == template.id).order_by(WorkflowTemplateVersion.version_number.desc())
    ).all()
    return WorkflowTemplateResponse(
        id=template.id, name=template.name, description=template.description, provider=template.provider,
        external_workflow_id=template.external_workflow_id,
        media_type=template.media_type, status=template.status, versions=[_version_response(item) for item in versions],
        created_at=template.created_at, updated_at=template.updated_at,
    )


@router.post(
    "/runninghub/workflows/import", response_model=WorkflowTemplateResponse, status_code=status.HTTP_201_CREATED,
    summary="导入并自动识别 RunningHub ComfyUI API 工作流",
    description="保存原始 JSON 为不可变版本，并生成可人工修订的输入参数与输出节点草稿。",
)
async def import_runninghub_workflow(
    current_user: CurrentUser,
    file: UploadFile = File(..., description="ComfyUI 的 API 格式 JSON 文件"),
    name: str = Form(""), description: str = Form(""), media_type: str = Form("audio"),
    runninghub_workflow_id: str = Form("", description="RunningHub 平台工作流 ID；真实模式提交任务时必填"),
    template_id: UUID | None = Form(None, description="上传新版本时填写已有模板 ID"),
    db: Session = Depends(get_db),
) -> WorkflowTemplateResponse:
    _require_teacher(current_user)
    if not (file.filename or "").lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="工作流文件必须是 JSON")
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="工作流 JSON 不能超过 5MB")
    try:
        workflow = parse_workflow_json(raw)
        analysis = analyze_workflow(workflow)
    except WorkflowAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if template_id:
        template = db.scalar(
            select(WorkflowTemplate).where(WorkflowTemplate.id == template_id, WorkflowTemplate.owner_id == current_user.id)
        )
        if template is None:
            raise HTTPException(status_code=404, detail="工作流模板不存在")
        if runninghub_workflow_id.strip():
            template.external_workflow_id = runninghub_workflow_id.strip()
    else:
        template = WorkflowTemplate(
            name=name.strip() or (file.filename or "工作流").rsplit(".", 1)[0],
            description=description.strip(), media_type=media_type, owner_id=current_user.id,
            external_workflow_id=runninghub_workflow_id.strip(),
        )
        db.add(template)
        db.flush()
    digest = workflow_sha256(workflow)
    existing = db.scalar(
        select(WorkflowTemplateVersion).where(
            WorkflowTemplateVersion.template_id == template.id,
            WorkflowTemplateVersion.workflow_hash == digest,
        )
    )
    if existing:
        return _template_response(db, template)
    next_version = (db.scalar(select(func.max(WorkflowTemplateVersion.version_number)).where(WorkflowTemplateVersion.template_id == template.id)) or 0) + 1
    version = WorkflowTemplateVersion(
        template_id=template.id, version_number=next_version, source_filename=file.filename or "workflow.json",
        workflow_hash=digest, workflow_json=workflow, analysis=analysis,
        parameter_config=analysis["parameters"], output_config=analysis["outputs"], owner_id=current_user.id,
    )
    db.add(version)
    db.commit()
    db.refresh(template)
    return _template_response(db, template)


@router.get("/runninghub/workflows", response_model=list[WorkflowTemplateResponse], summary="查询 RunningHub 工作流模板")
def list_runninghub_workflows(current_user: CurrentUser, db: Session = Depends(get_db)) -> list[WorkflowTemplateResponse]:
    templates = db.scalars(
        select(WorkflowTemplate).where(WorkflowTemplate.owner_id == current_user.id).order_by(WorkflowTemplate.updated_at.desc())
    ).all()
    return [_template_response(db, item) for item in templates]


@router.put("/runninghub/workflows/{template_id}", response_model=WorkflowTemplateResponse, summary="更新 RunningHub 工作流模板信息")
def update_runninghub_workflow(
    template_id: UUID, request: WorkflowTemplateUpdateRequest, current_user: CurrentUser, db: Session = Depends(get_db),
) -> WorkflowTemplateResponse:
    """补录平台 workflowId 或修改显示信息；版本中的原始 JSON 保持不可变。"""

    _require_teacher(current_user)
    template = db.scalar(
        select(WorkflowTemplate).where(WorkflowTemplate.id == template_id, WorkflowTemplate.owner_id == current_user.id)
    )
    if template is None:
        raise HTTPException(status_code=404, detail="工作流模板不存在")
    template.name = request.name
    template.description = request.description
    template.external_workflow_id = request.external_workflow_id.strip()
    template.media_type = request.media_type
    db.commit()
    db.refresh(template)
    return _template_response(db, template)


@router.put("/runninghub/workflow-versions/{version_id}/configuration", response_model=WorkflowVersionResponse, summary="二次配置工作流输入与输出")
def configure_runninghub_workflow(
    version_id: UUID, request: WorkflowVersionConfigureRequest, current_user: CurrentUser, db: Session = Depends(get_db),
) -> WorkflowVersionResponse:
    _require_teacher(current_user)
    version = db.scalar(
        select(WorkflowTemplateVersion).where(WorkflowTemplateVersion.id == version_id, WorkflowTemplateVersion.owner_id == current_user.id)
    )
    if version is None:
        raise HTTPException(status_code=404, detail="工作流版本不存在")
    if version.status == "published":
        raise HTTPException(status_code=409, detail="已发布版本不可覆盖，请重新导入为新版本")
    nodes = {str(key): value for key, value in version.workflow_json.items()}
    for item in request.parameters:
        if item.node_id not in nodes or item.field_name not in nodes[item.node_id]["inputs"]:
            raise HTTPException(status_code=400, detail=f"参数 {item.key} 指向不存在的节点字段")
    for output in request.outputs:
        if output.node_id not in nodes:
            raise HTTPException(status_code=400, detail=f"输出节点 {output.node_id} 不存在")
    version.parameter_config = [item.model_dump(mode="json") for item in request.parameters]
    version.output_config = [item.model_dump(mode="json") for item in request.outputs]
    db.commit()
    db.refresh(version)
    return _version_response(version)


@router.post("/runninghub/workflow-versions/{version_id}/publish", response_model=WorkflowVersionResponse, summary="发布 RunningHub 工作流版本")
def publish_runninghub_workflow(version_id: UUID, current_user: CurrentUser, db: Session = Depends(get_db)) -> WorkflowVersionResponse:
    _require_teacher(current_user)
    version = db.scalar(
        select(WorkflowTemplateVersion).where(WorkflowTemplateVersion.id == version_id, WorkflowTemplateVersion.owner_id == current_user.id)
    )
    if version is None:
        raise HTTPException(status_code=404, detail="工作流版本不存在")
    if not any(item.get("enabled") for item in version.output_config):
        raise HTTPException(status_code=400, detail="至少启用一个输出节点后才能发布")
    version.status = "published"
    version.published_at = datetime.utcnow()
    template = db.get(WorkflowTemplate, version.template_id)
    if template:
        template.status = "published"
    db.commit()
    db.refresh(version)
    return _version_response(version)
