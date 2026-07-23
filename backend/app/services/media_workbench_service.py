from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MediaWorkbenchConfig, WorkflowTemplate, WorkflowTemplateVersion


DEFAULT_WORKBENCHES = {
    "audio-clone": {
        "display_name": "克隆音频",
        "description": "上传参考音色与情绪音频，输入文本后生成克隆语音。",
        "provider": "runninghub",
        "capability": "audio",
        "model": "",
        "provider_api_mode": "workflow",
        "default_parameters": {},
        "input_config": {
            "prompt": {"label": "合成文本", "help_text": "输入需要用克隆音色朗读的内容", "required": True, "target_parameter_key": ""},
            "primary_asset": {"label": "参考音色", "help_text": "建议上传清晰、无背景音乐的人声音频", "required": True, "media_type": "audio", "target_parameter_key": ""},
            "secondary_asset": {"label": "情绪参考", "help_text": "可选；用于参考语气和情绪", "required": False, "media_type": "audio", "target_parameter_key": ""},
            "exposed_parameter_keys": [],
        },
    },
    "image-to-image": {
        "display_name": "图生图",
        "description": "上传一张或多张参考图片并描述合成要求，生成一张新的图片。",
        "provider": "grsai",
        "capability": "image",
        "model": "nano-banana-fast",
        "provider_api_mode": "unified",
        "default_parameters": {"aspectRatio": "auto", "imageSize": "1K"},
        "input_config": {
            "prompt": {"label": "修改要求", "help_text": "说明希望保留和改变的内容", "required": True, "target_parameter_key": ""},
            "primary_asset": {"label": "参考图片", "help_text": "支持 JPG、PNG、JPEG、WEBP，单张不超过 12MB，最多 10 张", "required": True, "media_type": "image", "target_parameter_key": "source_image"},
            "exposed_parameter_keys": ["aspectRatio", "imageSize"],
        },
    },
}


def ensure_default_workbenches(db: Session) -> list[MediaWorkbenchConfig]:
    """幂等创建两个首批工作台，让全新数据库启动后立即有清晰入口。"""

    existing = {record.slug: record for record in db.scalars(select(MediaWorkbenchConfig)).all()}
    changed = False
    for slug, defaults in DEFAULT_WORKBENCHES.items():
        if slug not in existing:
            record = MediaWorkbenchConfig(slug=slug, **defaults)
            db.add(record)
            existing[slug] = record
            changed = True
    if changed:
        db.commit()
    return [existing[slug] for slug in DEFAULT_WORKBENCHES]


def get_workbench(db: Session, slug: str) -> MediaWorkbenchConfig | None:
    ensure_default_workbenches(db)
    return db.scalar(select(MediaWorkbenchConfig).where(MediaWorkbenchConfig.slug == slug))


def validate_workbench_configuration(
    db: Session,
    record: MediaWorkbenchConfig,
    grsai_configured: bool,
    runninghub_configured: bool,
    mock_mode: bool,
) -> list[str]:
    """返回用户可读的配置缺口，工作台据此决定是否允许提交。"""

    issues: list[str] = []
    input_config = record.input_config or {}
    if not record.enabled:
        issues.append("工作台已停用")
    if record.slug == "audio-clone":
        version = db.get(WorkflowTemplateVersion, record.workflow_version_id) if record.workflow_version_id else None
        if version is None or version.status != "published":
            issues.append("尚未绑定已发布的 RunningHub 工作流版本")
        elif not mock_mode:
            template = db.get(WorkflowTemplate, version.template_id)
            if template is None or not template.external_workflow_id:
                issues.append("所选工作流尚未配置 RunningHub workflowId")
        if not mock_mode and not runninghub_configured:
            issues.append("服务端尚未配置 RUNNINGHUB_API_KEY")
        for key in ("prompt", "primary_asset"):
            if not input_config.get(key, {}).get("target_parameter_key"):
                issues.append(f"尚未映射{input_config.get(key, {}).get('label', key)}字段")
    elif record.slug == "image-to-image":
        if not record.model:
            issues.append("尚未配置 GRS AI 模型")
        if record.provider_api_mode != "unified":
            issues.append("图生图工作台必须使用 GRS AI unified 接口")
        if not mock_mode and not grsai_configured:
            issues.append("服务端尚未配置 GRSAI_API_KEY")
    else:
        issues.append("未知工作台类型")
    return issues


def validate_workflow_mapping(db: Session, workflow_version_id: UUID | None, input_config: dict) -> None:
    """保存配置前验证逻辑字段确实指向所选工作流中的参数。"""

    if workflow_version_id is None:
        raise ValueError("克隆音频工作台必须选择工作流版本")
    version = db.get(WorkflowTemplateVersion, workflow_version_id)
    if version is None or version.status != "published":
        raise ValueError("只能绑定已发布的工作流版本")
    parameters = {item.get("key"): item for item in version.parameter_config}
    prompt_key = input_config.get("prompt", {}).get("target_parameter_key")
    if prompt_key not in parameters or parameters[prompt_key].get("value_type") != "text":
        raise ValueError("合成文本必须映射到工作流文本参数")
    for config_key in ("primary_asset", "secondary_asset"):
        binding = input_config.get(config_key)
        if not binding:
            continue
        target_key = binding.get("target_parameter_key")
        if binding.get("required") or target_key:
            if target_key not in parameters or parameters[target_key].get("value_type") != "file":
                raise ValueError(f"{binding.get('label', config_key)}必须映射到工作流文件参数")
    mapped_file_keys = {
        input_config.get(config_key, {}).get("target_parameter_key")
        for config_key in ("primary_asset", "secondary_asset")
        if input_config.get(config_key)
    }
    unmapped_required_files = [
        item.get("label") or key
        for key, item in parameters.items()
        if item.get("value_type") == "file" and item.get("required") and key not in mapped_file_keys
    ]
    if unmapped_required_files:
        raise ValueError(f"仍有必填文件节点未绑定：{', '.join(unmapped_required_files)}")
    exposed = input_config.get("exposed_parameter_keys", [])
    if any(key not in parameters for key in exposed):
        raise ValueError("附加参数包含工作流中不存在的字段")
    unsupported = [
        key for key in exposed
        if parameters[key].get("value_type") not in {"text", "number", "boolean", "select"}
    ]
    if unsupported:
        raise ValueError("用户侧高级参数只支持文本、数字、开关或选项；文件参数必须绑定到上传控件")
