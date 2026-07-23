import hashlib
import json
import re
from typing import Any


class WorkflowAnalysisError(ValueError):
    """ComfyUI API 工作流结构不合法。"""


FILE_NODE_TYPES = {"LoadImage": "image", "LoadAudio": "audio", "LoadVideo": "video"}
OUTPUT_MEDIA_HINTS = {"audio": "audio", "image": "image", "video": "video"}
PRIMITIVE_TYPES = {"PrimitiveString", "PrimitiveStringMultiline"}
HIDDEN_FIELDS = {"audioUI", "imageUI", "videoUI", "filename_prefix", "custom_cuda_kernel", "deepspeed", "unload_model"}
BASIC_FIELDS = {
    "text",
    "prompt",
    "negative_prompt",
    "emo_alpha",
    "emo_text",
    "use_emo_text",
    "start_time",
    "end_time",
}


def parse_workflow_json(raw: bytes) -> dict[str, Any]:
    """解析并验证 ComfyUI API 格式 JSON，而不是浏览器导出的 UI 格式。"""

    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkflowAnalysisError("文件不是有效的 UTF-8 JSON") from exc
    if not isinstance(payload, dict) or not payload:
        raise WorkflowAnalysisError("工作流必须是以节点 ID 为键的非空 JSON 对象")
    for node_id, node in payload.items():
        if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
            raise WorkflowAnalysisError(f"节点 {node_id} 缺少 class_type 或 inputs；请导出 ComfyUI API 格式")
    return payload


def workflow_sha256(workflow: dict[str, Any]) -> str:
    """用规范 JSON 计算版本哈希，避免键顺序造成假变更。"""

    canonical = json.dumps(workflow, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_link(value: Any, node_ids: set[str]) -> bool:
    """识别 ComfyUI 的 ``[node_id, output_index]`` 连线，防止误暴露成用户参数。"""

    return isinstance(value, list) and len(value) == 2 and str(value[0]) in node_ids and isinstance(value[1], int)


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def _infer_output_media(class_type: str) -> str | None:
    lowered = class_type.lower()
    for hint, media_type in OUTPUT_MEDIA_HINTS.items():
        if hint in lowered and ("save" in lowered or "preview" in lowered):
            return media_type
    return None


def analyze_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
    """启发式识别输入字段、文件节点、参数和输出节点。

    识别结果只是可编辑草稿；复杂自定义节点仍由二次配置页面确认，避免把猜测直接带入生产任务。
    """

    node_ids = {str(node_id) for node_id in workflow}
    parameters: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    warnings: list[str] = []
    class_type_counts: dict[str, int] = {}

    for node_id, node in workflow.items():
        node_id = str(node_id)
        class_type = node["class_type"]
        class_type_counts[class_type] = class_type_counts.get(class_type, 0) + 1
        title = str(node.get("_meta", {}).get("title") or class_type)

        if class_type in FILE_NODE_TYPES:
            media_type = FILE_NODE_TYPES[class_type]
            field_name = next((name for name in node["inputs"] if name.lower() in {media_type, "file"}), media_type)
            parameters.append(
                {
                    "key": f"{media_type}_{node_id}", "node_id": node_id, "field_name": field_name,
                    "label": title, "value_type": "file", "required": True, "default": None,
                    "minimum": None, "maximum": None, "options": [], "visibility": "basic",
                    "asset_role": f"{media_type}_{node_id}", "order": len(parameters),
                    "description": f"上传后由 Worker 转交给 {class_type} 节点",
                }
            )

        for field_name, value in node["inputs"].items():
            if _is_link(value, node_ids) or field_name in HIDDEN_FIELDS or class_type in FILE_NODE_TYPES:
                continue
            if isinstance(value, bool):
                value_type = "boolean"
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                value_type = "number"
            elif isinstance(value, str):
                value_type = "text"
            else:
                continue
            visibility = "basic" if field_name.lower() in BASIC_FIELDS or class_type in PRIMITIVE_TYPES else "advanced"
            label = title if class_type in PRIMITIVE_TYPES else field_name.replace("_", " ")
            parameters.append(
                {
                    "key": _slug(f"{field_name}_{node_id}"), "node_id": node_id, "field_name": field_name,
                    "label": label, "value_type": value_type, "required": class_type in PRIMITIVE_TYPES,
                    "default": value, "minimum": None, "maximum": None, "options": [],
                    "visibility": visibility, "asset_role": None, "order": len(parameters),
                    "description": f"{class_type} 节点参数",
                }
            )

        output_media_type = _infer_output_media(class_type)
        if output_media_type:
            deprecated = "deprecated" in title.lower() or "deprecated" in class_type.lower()
            outputs.append(
                {
                    "node_id": node_id, "class_type": class_type, "label": title,
                    "media_type": output_media_type, "enabled": not deprecated,
                    "primary": not deprecated and not any(item["primary"] for item in outputs),
                }
            )

    if not outputs:
        warnings.append("未识别到 Save/Preview 输出节点，请在二次配置中手工指定输出")
    if not any(item["value_type"] == "file" for item in parameters):
        warnings.append("未识别到 LoadImage/LoadAudio/LoadVideo 文件输入节点")
    return {
        "format": "comfyui_api",
        "node_count": len(workflow),
        "class_type_counts": class_type_counts,
        "parameters": parameters,
        "outputs": outputs,
        "warnings": warnings,
    }
