import base64
from uuid import uuid4

from sqlalchemy.orm import Session

from app.media_providers.base import MediaProvider, ProviderOutput, QueryResult, SubmitResult
from app.models import MediaAsset, MediaGeneration, WorkflowTemplate, WorkflowTemplateVersion


# 1x1 PNG；Mock 模式仍会真正完成“轮询 -> MinIO 转存”，因此能验证基础设施而不产生供应商费用。
MOCK_PNG = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
).decode("ascii")


class MockMediaProvider(MediaProvider):
    """不访问外网的确定性供应商，用于本地完整链路和自动化测试。"""

    def __init__(self, provider_name: str) -> None:
        self.name = provider_name

    def submit(
        self,
        db: Session,
        generation: MediaGeneration,
        input_assets: dict[str, MediaAsset],
        workflow_version: WorkflowTemplateVersion | None,
        workflow_template: WorkflowTemplate | None,
    ) -> SubmitResult:
        payload = {"provider": self.name, "capability": generation.capability, "mock": True}
        return SubmitResult(f"mock-{self.name}-{uuid4().hex}", "MOCK_QUEUED", payload, {"mock": True})

    def query(self, task_id: str, generation: MediaGeneration) -> QueryResult:
        if self.name == "grsai":
            output = ProviderOutput(f"data:image/png;base64,{MOCK_PNG}", "image", "image/png", {"mock": True})
        else:
            extension = {"audio": "wav", "video": "mp4", "image": "png"}.get(generation.capability, "bin")
            output = ProviderOutput(
                f"https://www.runninghub.cn/mock-results/{task_id}.{extension}", generation.capability,
                metadata={"mock": True, "note": "Mock URL 仅验证 external 存储策略"},
            )
        return QueryResult("succeeded", "MOCK_SUCCESS", {"mock": True, "taskId": task_id}, [output])

    def cancel(self, task_id: str) -> None:
        return None
