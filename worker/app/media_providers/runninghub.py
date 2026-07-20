from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import WorkerSettings
from app.media_providers.base import MediaProvider, ProviderOutput, QueryResult, SubmitResult
from app.media_storage import WorkerMediaStorage
from app.models import MediaAsset, MediaGeneration, WorkflowTemplate, WorkflowTemplateVersion


class RunningHubProvider(MediaProvider):
    """RunningHub ComfyUI 工作流适配器，输出 URL 不转存 MinIO。"""

    name = "runninghub"

    def __init__(self, settings: WorkerSettings, storage: WorkerMediaStorage) -> None:
        if not settings.runninghub_api_key:
            raise RuntimeError("未配置 RUNNINGHUB_API_KEY")
        self.api_key = settings.runninghub_api_key
        self.base_url = settings.runninghub_base_url.rstrip("/")
        self.timeout = settings.media_http_timeout_seconds
        self.storage = storage

    @property
    def bearer_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def submit(
        self,
        db: Session,
        generation: MediaGeneration,
        input_assets: dict[str, MediaAsset],
        workflow_version: WorkflowTemplateVersion | None,
        workflow_template: WorkflowTemplate | None,
    ) -> SubmitResult:
        if workflow_version is None or workflow_template is None:
            raise RuntimeError("RunningHub 任务缺少工作流版本")
        if not workflow_template.external_workflow_id:
            raise RuntimeError("工作流未配置 RunningHub 平台 workflowId")

        values = dict(generation.request_parameters or {})
        optional_file_keys = {str(key) for key in values.get("_optional_file_keys", [])}
        if generation.prompt:
            # 自动识别的 PrimitiveString 字段通常是主文本；若调用方未显式传值则注入 prompt。
            first_text = next(
                (item for item in workflow_version.parameter_config if item.get("value_type") == "text" and item.get("visibility") == "basic"),
                None,
            )
            if first_text and first_text.get("key") not in values:
                values[first_text["key"]] = generation.prompt

        node_info_list: list[dict[str, Any]] = []
        for parameter in sorted(workflow_version.parameter_config, key=lambda item: item.get("order", 0)):
            if parameter.get("visibility") == "hidden":
                continue
            key = parameter["key"]
            if parameter.get("value_type") == "file":
                asset = input_assets.get(key) or input_assets.get(parameter.get("asset_role", ""))
                if asset is None:
                    if parameter.get("required") and key not in optional_file_keys:
                        raise RuntimeError(f"缺少工作流文件输入：{parameter.get('label') or key}")
                    continue
                value = self._upload_asset(asset)
            else:
                value = values.get(key, parameter.get("default"))
                if value is None and parameter.get("required"):
                    raise RuntimeError(f"缺少工作流参数：{parameter.get('label') or key}")
                if value is None:
                    continue
            node_info_list.append({"nodeId": str(parameter["node_id"]), "fieldName": parameter["field_name"], "fieldValue": value})

        payload: dict[str, Any] = {
            "apiKey": self.api_key,
            "workflowId": workflow_template.external_workflow_id,
            "nodeInfoList": node_info_list,
        }
        retain_seconds = values.get("retainSeconds")
        if retain_seconds is not None:
            payload["retainSeconds"] = int(retain_seconds)
        response = httpx.post(f"{self.base_url}/task/openapi/create", json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        _raise_provider_error(data, "RunningHub 创建任务失败")
        task_id = _extract_task_id(data)
        if not task_id:
            raise RuntimeError(f"RunningHub 未返回任务 ID：{data.get('msg') or data.get('message') or 'unknown'}")
        # 运行记录中不落 apiKey，避免密钥进入数据库快照。
        safe_payload = {key: value for key, value in payload.items() if key != "apiKey"}
        body = data.get("data") if isinstance(data.get("data"), dict) else {}
        provider_status = str(body.get("taskStatus") or "QUEUED").upper()
        if provider_status in {"FAILED", "FAILURE", "ERROR", "CANCELLED", "CANCELED"}:
            detail = (
                body.get("promptTips")
                or body.get("errorMessage")
                or data.get("msg")
                or "任务提交后立即失败"
            )
            raise RuntimeError(f"RunningHub 创建任务失败：{detail}")
        # 极快完成的任务仍需进入一次查询，以便统一解析 results 并登记媒体资产。
        if provider_status == "SUCCESS":
            provider_status = "SUBMITTED"
        return SubmitResult(task_id, provider_status, safe_payload, data)

    def _upload_asset(self, asset: MediaAsset) -> str:
        if asset.storage_mode != "managed" or not asset.object_key:
            raise RuntimeError("RunningHub 文件输入必须是已上传到 MinIO 的受管资产")
        # 先把 MinIO 网络流分块暂存为可 seek 文件。不要把网络响应直接交给 httpx，
        # 否则 multipart 可能根据 socket 的 fileno 算出错误 Content-Length。
        with self.storage.staged_upload(asset.object_key, asset.size_bytes) as (upload_file, _actual_size):
            response = httpx.post(
                f"{self.base_url}/openapi/v2/media/upload/binary",
                headers=self.bearer_headers,
                files={
                    "file": (
                        asset.original_file_name or Path(asset.object_key).name,
                        upload_file,
                        asset.content_type,
                    )
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            _raise_provider_error(data, "RunningHub 文件上传失败")
        body = data.get("data") if isinstance(data, dict) else None
        filename = body.get("fileName") if isinstance(body, dict) else None
        if not filename:
            raise RuntimeError("RunningHub 上传成功但未返回 fileName")
        return str(filename)

    def query(self, task_id: str, generation: MediaGeneration) -> QueryResult:
        response = httpx.post(
            f"{self.base_url}/openapi/v2/query", headers={**self.bearer_headers, "Content-Type": "application/json"},
            json={"taskId": task_id}, timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("RunningHub 查询响应格式异常")
        code = data.get("code")
        if code not in {None, 0, "0"}:
            message = str(data.get("msg") or data.get("message") or data.get("errorMessage") or "查询失败")
            return QueryResult(
                "failed",
                "ERROR",
                data,
                error_code=f"RUNNINGHUB_{code}",
                error_message=f"RunningHub 查询任务失败：{message}",
            )
        raw_status = str(data.get("status") or "RUNNING").upper()
        if raw_status == "SUCCESS":
            outputs: list[ProviderOutput] = []
            enabled_output_nodes = {
                str(node_id) for node_id in (generation.request_parameters or {}).get("_enabled_output_nodes", [])
            }
            for result in data.get("results") or []:
                if not isinstance(result, dict) or not result.get("url"):
                    continue
                result_node_id = str(result.get("nodeId") or result.get("node_id") or "")
                # RunningHub 某些响应会返回节点 ID；有节点信息时遵循教师在版本中启用的输出选择。
                # 旧响应不带节点 ID 时保留全部结果，避免因平台字段差异误丢输出。
                if enabled_output_nodes and result_node_id and result_node_id not in enabled_output_nodes:
                    continue
                output_type = str(result.get("outputType") or "").lower()
                media_type = _media_type_from_output(output_type, generation.capability)
                outputs.append(ProviderOutput(str(result["url"]), media_type, metadata=result))
            if not outputs:
                return QueryResult("failed", raw_status, data, error_code="EMPTY_RESULT", error_message="RunningHub 成功但未返回结果 URL")
            return QueryResult("succeeded", raw_status, data, outputs=outputs)
        if raw_status in {"FAILED", "ERROR", "FAILURE"}:
            return QueryResult(
                "failed", raw_status, data, error_code=str(data.get("errorCode") or "PROVIDER_FAILED"),
                error_message=str(data.get("errorMessage") or data.get("message") or "RunningHub 任务失败"),
            )
        if raw_status in {"CANCELLED", "CANCELED"}:
            return QueryResult("cancelled", raw_status, data)
        return QueryResult("running", raw_status, data)

    def cancel(self, task_id: str) -> None:
        response = httpx.post(
            f"{self.base_url}/task/openapi/cancel", json={"apiKey": self.api_key, "taskId": task_id}, timeout=self.timeout
        )
        response.raise_for_status()
        _raise_provider_error(response.json(), "RunningHub 取消任务失败")


def _extract_task_id(data: dict[str, Any]) -> str:
    body = data.get("data")
    candidates = [data.get("taskId"), data.get("id")]
    if isinstance(body, dict):
        candidates.extend([body.get("taskId"), body.get("id")])
    elif isinstance(body, str):
        candidates.append(body)
    return next((str(value) for value in candidates if value), "")


def _raise_provider_error(data: Any, context: str) -> None:
    """RunningHub 业务错误通常使用 HTTP 200 + 非零 code，需要显式转换为任务错误。"""

    if not isinstance(data, dict):
        raise RuntimeError(f"{context}：响应不是 JSON 对象")
    code = data.get("code")
    if code not in {None, 0, "0"}:
        message = data.get("msg") or data.get("message") or data.get("errorMessage") or "未知错误"
        raise RuntimeError(f"{context}（{code}）：{message}")


def _media_type_from_output(output_type: str, fallback: str) -> str:
    if output_type in {"png", "jpg", "jpeg", "webp", "gif"}:
        return "image"
    if output_type in {"mp3", "wav", "flac", "m4a", "aac", "ogg"}:
        return "audio"
    if output_type in {"mp4", "mov", "webm", "avi", "mkv"}:
        return "video"
    return fallback
