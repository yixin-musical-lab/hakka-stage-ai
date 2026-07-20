from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import WorkerSettings
from app.media_providers.base import MediaProvider, ProviderOutput, QueryResult, SubmitResult
from app.media_storage import WorkerMediaStorage
from app.models import MediaAsset, MediaGeneration, WorkflowTemplate, WorkflowTemplateVersion


class GrsaiProvider(MediaProvider):
    """GRS AI Nano Banana 适配器。

    供应商字段全部封装在本类；上层只处理统一状态和输出，后续接入其他 GRS 模型时不会污染任务表。
    """

    name = "grsai"

    def __init__(self, settings: WorkerSettings, storage: WorkerMediaStorage) -> None:
        if not settings.grsai_api_key:
            raise RuntimeError("未配置 GRSAI_API_KEY")
        self.api_key = settings.grsai_api_key
        self.base_url = settings.grsai_base_url.rstrip("/")
        self.timeout = settings.media_http_timeout_seconds
        self.storage = storage

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def submit(
        self,
        db: Session,
        generation: MediaGeneration,
        input_assets: dict[str, MediaAsset],
        workflow_version: WorkflowTemplateVersion | None,
        workflow_template: WorkflowTemplate | None,
    ) -> SubmitResult:
        parameters = generation.request_parameters or {}
        api_mode = str(parameters.get("_api_mode") or "legacy")
        if api_mode == "unified":
            return self._submit_unified(generation, input_assets, parameters)
        if input_assets:
            raise RuntimeError("GRS AI 旧版接口的图生图只接受公网 URL；请改用 unified 接口")
        payload: dict[str, Any] = {
            "model": generation.model or "nano-banana-fast",
            "prompt": generation.prompt,
            "aspectRatio": parameters.get("aspectRatio", "auto"),
            "imageSize": parameters.get("imageSize", "1K"),
            "urls": parameters.get("urls", []),
            "webHook": "-1",
            "shutProgress": bool(parameters.get("shutProgress", True)),
        }
        response = httpx.post(
            f"{self.base_url}/v1/draw/nano-banana", headers=self.headers, json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("GRS AI 提交响应格式异常")
        task_id = _extract_task_id(data)
        if not task_id:
            raise RuntimeError(f"GRS AI 未返回任务 ID：{data.get('msg') or data.get('message') or 'unknown'}")
        return SubmitResult(task_id, "RUNNING", payload, data)

    def _submit_unified(
        self,
        generation: MediaGeneration,
        input_assets: dict[str, MediaAsset],
        parameters: dict[str, Any],
    ) -> SubmitResult:
        """使用 GRS AI Unified async 接口提交图生图。

        Unified API 同时支持 json、stream 和 async。json 会在原 POST 连接中直接返回
        最终结果，不能再拿其任务 ID 调用异步查询接口；本项目已有独立 Worker 轮询器，
        因此固定使用 async，并避免把 Base64 原文写入运行记录。
        """

        images: list[str] = []
        safe_images: list[dict[str, Any]] = []
        for binding_key, asset in input_assets.items():
            if asset.media_type != "image" or asset.storage_mode != "managed" or not asset.object_key:
                raise RuntimeError(f"GRS AI 输入 {binding_key} 必须是 MinIO 中的受管图片")
            images.append(self.storage.read_data_url(asset.object_key, asset.content_type))
            safe_images.append(
                {
                    "binding": binding_key,
                    "asset_id": str(asset.id),
                    "content_type": asset.content_type,
                    "size_bytes": asset.size_bytes,
                }
            )
        if not images:
            raise RuntimeError("图生图工作台至少需要一张参考图片")
        payload: dict[str, Any] = {
            "model": generation.model or "nano-banana-fast",
            "prompt": generation.prompt,
            "images": images,
            "aspectRatio": parameters.get("aspectRatio", "auto"),
            "imageSize": parameters.get("imageSize", "1K"),
            "replyType": "async",
        }
        response = httpx.post(
            f"{self.base_url}/v1/api/generate", headers=self.headers, json=payload, timeout=self.timeout
        )
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise RuntimeError("GRS AI unified 提交响应不是有效 JSON")
        if not isinstance(data, dict):
            raise RuntimeError("GRS AI unified 提交响应格式异常")
        raw_status = str(data.get("status") or "running").lower()
        if raw_status in {"failed", "failure", "error", "violation"}:
            raise RuntimeError(f"GRS AI unified 创建任务失败：{_extract_error_message(data)}")
        # 供应商可能用 HTTP 400 返回带 status/error 的结构化失败，上面优先保留了
        # 可读业务错误；其余非 2xx 响应仍按 HTTP 异常处理。
        response.raise_for_status()
        task_id = _extract_task_id(data)
        if not task_id:
            raise RuntimeError(f"GRS AI unified 未返回任务 ID：{data.get('message') or 'unknown'}")
        safe_payload = {key: value for key, value in payload.items() if key != "images"}
        safe_payload["images"] = safe_images
        # async 正常返回 running。若供应商极快地返回 succeeded，也仍标记为 SUBMITTED，
        # 让统一编排器至少查询一次 /v1/api/result 并执行 MinIO 转存，避免再次漏存结果。
        provider_status = (
            "SUBMITTED"
            if raw_status in {"success", "succeeded", "completed", "finish", "finished"}
            else raw_status.upper()
        )
        if provider_status not in {"CREATED", "QUEUED", "RUNNING", "PENDING", "SUBMITTED"}:
            provider_status = "SUBMITTED"
        return SubmitResult(task_id, provider_status, safe_payload, data)

    def query(self, task_id: str, generation: MediaGeneration) -> QueryResult:
        api_mode = str((generation.request_parameters or {}).get("_api_mode") or "legacy")
        if api_mode == "unified":
            response = httpx.get(
                f"{self.base_url}/v1/api/result", headers=self.headers, params={"id": task_id}, timeout=self.timeout
            )
        else:
            response = httpx.post(
                f"{self.base_url}/v1/draw/result", headers=self.headers, json={"id": task_id}, timeout=self.timeout
            )
        try:
            parsed_data = response.json()
        except ValueError:
            parsed_data = None
        data = parsed_data if isinstance(parsed_data, dict) else {}

        # 异步结果只保留有限时间。把 404 转换为明确终态，避免上层只看到模糊的
        # HTTPStatusError 和完整请求 URL。
        if response.status_code == 404:
            not_found_data = data or {"error": "result not found"}
            return QueryResult(
                "failed", "NOT_FOUND", not_found_data,
                error_code="GRSAI_RESULT_NOT_FOUND",
                error_message=f"GRS AI 异步结果不存在或已过期：{_extract_error_message(not_found_data)}",
            )
        if parsed_data is not None and not isinstance(parsed_data, dict):
            raise RuntimeError("GRS AI 查询响应格式异常")
        body = data.get("data") if isinstance(data.get("data"), dict) else data
        raw_status = str(body.get("status") or data.get("status") or "running").lower()
        if raw_status in {"failed", "failure", "error", "violation"}:
            error_code = "GRSAI_VIOLATION" if raw_status == "violation" else str(
                body.get("errorCode") or data.get("code") or "PROVIDER_FAILED"
            )
            return QueryResult(
                "failed", raw_status, data,
                error_code=error_code,
                error_message=_extract_error_message(data, fallback="GRS AI 任务失败"),
            )
        # 与提交接口相同，HTTP 400 可能已在上面转换为结构化业务失败；其余未识别的
        # 非 2xx 响应继续交给 httpx，避免把网关异常误认为 running。
        response.raise_for_status()
        if raw_status in {"success", "succeeded", "completed", "finish", "finished"}:
            outputs = _extract_outputs(body)
            if not outputs:
                return QueryResult(
                    "failed", raw_status, data,
                    error_code="EMPTY_RESULT",
                    error_message="GRS AI 成功但未返回图片 URL",
                )
            return QueryResult("succeeded", raw_status, data, outputs=outputs)
        if raw_status in {"cancelled", "canceled"}:
            return QueryResult("cancelled", raw_status, data)
        return QueryResult("running", raw_status, data)

    def cancel(self, task_id: str) -> None:
        # 旧版 Nano Banana 文档未公开取消接口；本地取消后停止轮询即可。
        return None


def _extract_task_id(data: dict[str, Any]) -> str:
    body = data.get("data")
    candidates = [data.get("id"), data.get("taskId"), data.get("task_id")]
    if isinstance(body, dict):
        candidates.extend([body.get("id"), body.get("taskId"), body.get("task_id")])
    elif isinstance(body, str):
        candidates.append(body)
    return next((str(value) for value in candidates if value), "")


def _extract_outputs(body: dict[str, Any]) -> list[ProviderOutput]:
    raw_results = body.get("results") or body.get("result") or body.get("urls") or []
    if isinstance(raw_results, (str, dict)):
        raw_results = [raw_results]
    outputs: list[ProviderOutput] = []
    for result in raw_results if isinstance(raw_results, list) else []:
        if isinstance(result, str):
            outputs.append(ProviderOutput(result, "image"))
        elif isinstance(result, dict):
            url = result.get("url") or result.get("imageUrl") or result.get("downloadUrl")
            if url:
                outputs.append(ProviderOutput(str(url), "image", metadata={key: value for key, value in result.items() if key != "url"}))
    return outputs


def _extract_error_message(data: dict[str, Any], fallback: str = "未知错误") -> str:
    """兼容 GRS AI 不同接口的错误字段，且只返回适合落库的简短文本。"""

    nested = data.get("data") if isinstance(data.get("data"), dict) else {}
    return str(
        data.get("error")
        or data.get("message")
        or data.get("msg")
        or nested.get("error")
        or nested.get("message")
        or nested.get("msg")
        or fallback
    )[:500]
