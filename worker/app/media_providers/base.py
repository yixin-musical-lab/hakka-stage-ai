from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import MediaAsset, MediaGeneration, WorkflowTemplate, WorkflowTemplateVersion


@dataclass(frozen=True)
class ProviderOutput:
    """归一化后的供应商输出。"""

    url: str
    media_type: str
    content_type: str = "application/octet-stream"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SubmitResult:
    task_id: str
    provider_status: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]


@dataclass(frozen=True)
class QueryResult:
    """status 只允许 running/succeeded/failed/cancelled，业务层不感知平台枚举。"""

    status: str
    provider_status: str
    response_payload: dict[str, Any]
    outputs: list[ProviderOutput] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None


class MediaProvider(ABC):
    """所有图片、视频和音频供应商必须实现的最小协议。"""

    name: str

    @abstractmethod
    def submit(
        self,
        db: Session,
        generation: MediaGeneration,
        input_assets: dict[str, MediaAsset],
        workflow_version: WorkflowTemplateVersion | None,
        workflow_template: WorkflowTemplate | None,
    ) -> SubmitResult:
        raise NotImplementedError

    @abstractmethod
    def query(self, task_id: str, generation: MediaGeneration) -> QueryResult:
        raise NotImplementedError

    @abstractmethod
    def cancel(self, task_id: str) -> None:
        raise NotImplementedError
