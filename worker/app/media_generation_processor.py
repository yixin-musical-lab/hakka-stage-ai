import re
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.config import WorkerSettings
from app.database import SessionLocal
from app.media_providers import GrsaiProvider, MediaProvider, MockMediaProvider, RunningHubProvider
from app.media_storage import WorkerMediaStorage
from app.models import (
    AiTask, MediaAsset, MediaGeneration, ProviderTaskRun, WorkflowTemplate, WorkflowTemplateVersion,
)


ACTIVE_PROVIDER_STATUSES = {"CREATED", "QUEUED", "RUNNING", "PENDING", "MOCK_QUEUED", "SUBMITTED"}


def normalize_provider_status(value: str | None) -> str:
    """统一数据库中的供应商状态，避免大小写差异让到期扫描漏掉任务。"""

    normalized = str(value or "").strip().upper()
    return normalized or "UNKNOWN"


class MediaGenerationProcessor:
    """统一编排提交、轮询、转存和取消，供应商适配器保持无数据库状态。"""

    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings
        self.storage = WorkerMediaStorage(settings)

    def _provider(self, name: str) -> MediaProvider:
        if self.settings.media_mock_mode:
            return MockMediaProvider(name)
        if name == "grsai":
            return GrsaiProvider(self.settings, self.storage)
        if name == "runninghub":
            return RunningHubProvider(self.settings, self.storage)
        raise RuntimeError(f"不支持的媒体供应商：{name}")

    def submit(self, generation_id: UUID, task_id: UUID | None = None) -> None:
        with SessionLocal() as db:
            generation = db.get(MediaGeneration, generation_id)
            run = db.scalar(select(ProviderTaskRun).where(ProviderTaskRun.generation_id == generation_id))
            task = db.get(AiTask, task_id) if task_id else db.scalar(
                select(AiTask).where(AiTask.business_id == generation_id, AiTask.task_type == "media_generation.run")
            )
            if generation is None or run is None:
                raise RuntimeError("媒体任务或供应商运行记录不存在")
            if generation.status not in {"PENDING", "RETRYING"}:
                return
            now = datetime.utcnow()
            generation.status = "SUBMITTING"
            run.provider_status = "SUBMITTING"
            run.started_at = now
            if task:
                task.status = "RUNNING"
                task.progress = 5
                task.started_at = now
            db.commit()
            try:
                inputs = self._input_assets(db, generation)
                version, template = self._workflow(db, generation)
                result = self._provider(generation.provider).submit(db, generation, inputs, version, template)
                run.external_task_id = result.task_id
                # 供应商原始响应仍完整保存在 response_payload；调度字段统一使用大写状态，
                # 否则 GRS AI 的 `running` 会与 RunningHub 的 `RUNNING` 形成两套枚举。
                run.provider_status = normalize_provider_status(result.provider_status)
                run.request_payload = result.request_payload
                run.response_payload = result.response_payload
                poll_interval, _poll_max_count = self._poll_policy(generation.provider)
                run.next_poll_at = now + timedelta(seconds=poll_interval)
                generation.status = "RUNNING"
                if task:
                    task.progress = 15
                db.commit()
            except Exception as exc:  # noqa: BLE001 - 供应商异常统一落库后继续服务其他任务。
                self._fail(db, generation, run, task, "SUBMIT_FAILED", exc)

    def poll(self, generation_id: UUID) -> None:
        with SessionLocal() as db:
            generation = db.get(MediaGeneration, generation_id)
            run = db.scalar(select(ProviderTaskRun).where(ProviderTaskRun.generation_id == generation_id))
            task = db.scalar(select(AiTask).where(AiTask.business_id == generation_id, AiTask.task_type == "media_generation.run"))
            if generation is None or run is None or not run.external_task_id:
                return
            if generation.status not in {"RUNNING", "SUBMITTED"}:
                return
            try:
                result = self._provider(generation.provider).query(run.external_task_id, generation)
                now = datetime.utcnow()
                run.poll_count += 1
                run.last_polled_at = now
                run.provider_status = normalize_provider_status(result.provider_status)
                run.response_payload = result.response_payload
                if result.status == "running":
                    poll_interval, poll_max_count = self._poll_policy(generation.provider)
                    if run.poll_count >= poll_max_count:
                        raise RuntimeError("供应商任务轮询超过上限")
                    run.next_poll_at = now + timedelta(seconds=poll_interval)
                    if task:
                        task.progress = min(90, 15 + run.poll_count)
                    db.commit()
                    return
                if result.status == "succeeded":
                    self._save_outputs(db, generation, run, result.outputs)
                    generation.status = "SUCCEEDED"
                    generation.finished_at = now
                    run.finished_at = now
                    run.next_poll_at = None
                    if task:
                        task.status = "SUCCESS"
                        task.progress = 100
                        task.result_id = generation.id
                        task.finished_at = now
                    db.commit()
                    return
                if result.status == "cancelled":
                    generation.status = "CANCELLED"
                    run.finished_at = generation.finished_at = now
                    if task:
                        task.status = "CANCELLED"
                        task.finished_at = now
                    db.commit()
                    return
                self._fail(db, generation, run, task, result.error_code or "PROVIDER_FAILED", RuntimeError(result.error_message or "供应商任务失败"))
            except Exception as exc:  # noqa: BLE001
                self._fail(db, generation, run, task, "QUERY_FAILED", exc)

    def poll_due(self, limit: int = 10) -> None:
        """短批次扫描到期任务，避免 Redis 无新消息时异步任务永远不更新。"""

        with SessionLocal() as db:
            ids = db.scalars(
                select(ProviderTaskRun.generation_id).where(
                    # 兼容升级前已经保存的小写 GRS AI 状态；新写入状态会统一为大写。
                    func.upper(ProviderTaskRun.provider_status).in_(ACTIVE_PROVIDER_STATUSES),
                    ProviderTaskRun.external_task_id.is_not(None),
                    ProviderTaskRun.next_poll_at <= datetime.utcnow(),
                ).order_by(ProviderTaskRun.next_poll_at).limit(limit)
            ).all()
        for generation_id in ids:
            self.poll(generation_id)

    def _poll_policy(self, provider: str) -> tuple[int, int]:
        """返回供应商独立的轮询间隔和最大次数。

        GRS AI Unified API 的 async 模式经过真实验证，任务可能在 15 秒到数分钟内完成；
        RunningHub 则继续沿用原有通用策略。这里统一兜底到至少 1，避免错误环境变量
        导致零秒忙轮询或任务永远不执行查询。
        """

        if provider == "grsai":
            return (
                max(1, self.settings.grsai_poll_interval_seconds),
                max(1, self.settings.grsai_poll_max_count),
            )
        return (
            max(1, self.settings.media_poll_interval_seconds),
            max(1, self.settings.media_poll_max_count),
        )

    def cancel(self, generation_id: UUID) -> None:
        with SessionLocal() as db:
            generation = db.get(MediaGeneration, generation_id)
            run = db.scalar(select(ProviderTaskRun).where(ProviderTaskRun.generation_id == generation_id))
            task = db.scalar(select(AiTask).where(AiTask.business_id == generation_id, AiTask.task_type == "media_generation.run"))
            if generation is None or run is None:
                return
            try:
                if run.external_task_id:
                    self._provider(generation.provider).cancel(run.external_task_id)
            finally:
                now = datetime.utcnow()
                generation.status = "CANCELLED"
                generation.finished_at = now
                run.provider_status = "CANCELLED"
                run.finished_at = now
                run.next_poll_at = None
                if task:
                    task.status = "CANCELLED"
                    task.finished_at = now
                db.commit()

    @staticmethod
    def _input_assets(db, generation: MediaGeneration) -> dict[str, MediaAsset]:
        assets: dict[str, MediaAsset] = {}
        for key, raw_id in (generation.input_bindings or {}).items():
            asset = db.get(MediaAsset, UUID(str(raw_id)))
            if asset is None or asset.owner_id != generation.owner_id:
                raise RuntimeError(f"输入资产 {key} 不存在或无权访问")
            assets[key] = asset
        return assets

    @staticmethod
    def _workflow(db, generation: MediaGeneration) -> tuple[WorkflowTemplateVersion | None, WorkflowTemplate | None]:
        if generation.workflow_version_id is None:
            return None, None
        version = db.get(WorkflowTemplateVersion, generation.workflow_version_id)
        if version is None or version.status != "published":
            raise RuntimeError("工作流版本不存在或未发布")
        return version, db.get(WorkflowTemplate, version.template_id)

    def _save_outputs(self, db, generation: MediaGeneration, run: ProviderTaskRun, outputs) -> None:
        existing = db.scalar(select(MediaAsset.id).where(MediaAsset.provider_task_run_id == run.id, MediaAsset.role == "output"))
        if existing:
            return
        for index, output in enumerate(outputs):
            if generation.provider == "grsai":
                object_key, content_type, size, filename = self.storage.transfer_result(output.url, output.media_type, output.content_type)
                asset = MediaAsset(
                    generation_id=generation.id, provider_task_run_id=run.id, role="output",
                    media_type=output.media_type, storage_mode="managed", bucket=self.settings.minio_bucket,
                    object_key=object_key, original_file_name=filename, content_type=content_type,
                    size_bytes=size, provider=generation.provider, provider_output_index=index,
                    asset_metadata=output.metadata, owner_id=generation.owner_id,
                )
            else:
                asset = MediaAsset(
                    generation_id=generation.id, provider_task_run_id=run.id, role="output",
                    media_type=output.media_type, storage_mode="external", external_url=output.url,
                    provider=generation.provider, provider_output_index=index, asset_metadata=output.metadata,
                    owner_id=generation.owner_id,
                )
            db.add(asset)

    @staticmethod
    def _fail(db, generation, run, task, code: str, exc: Exception) -> None:
        now = datetime.utcnow()
        message = re.sub(r"(Bearer\s+|apiKey[=: ]+)[A-Za-z0-9_.-]+", r"\1***", str(exc), flags=re.IGNORECASE)[:1000]
        generation.status = "FAILED"
        generation.finished_at = now
        run.provider_status = "FAILED"
        run.error_code = code
        run.error_message = message
        run.finished_at = now
        run.next_poll_at = None
        if task:
            task.status = "FAILED"
            task.error_code = code
            task.error_message = message
            task.finished_at = now
        db.commit()
