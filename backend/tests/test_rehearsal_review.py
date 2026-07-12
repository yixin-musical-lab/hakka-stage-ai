import io
import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import UploadFile
from pydantic import ValidationError
from starlette.datastructures import Headers

from app.core.config import Settings
from app.schemas.rehearsal_review import RehearsalReviewContent, RehearsalReviewGenerateRequest
from app.services.rehearsal_review_service import render_rehearsal_review_markdown
from app.services.rehearsal_storage import (
    RehearsalStorageError,
    parse_video_range,
    save_rehearsal_video_upload,
)


def valid_content() -> dict:
    """返回覆盖 M08 验收字段的最小合法报告。"""

    return {
        "title": "客家山歌小剧场 · 排练复盘",
        "overview": "本次完成第二幕与副歌连接。",
        "highlights": ["主角台词稳定。"],
        "issues": [
            {
                "category": "舞蹈与队形",
                "observation": "副歌展开时队形略散。",
                "possible_cause": "站位终点尚未固定。",
                "improvement_action": "先无音乐走位两次。",
                "priority": "high",
                "next_check": "连续两次停在标记点。",
            }
        ],
        "role_suggestions": [
            {
                "role_name": "群演组",
                "observation": "转场依赖老师提醒。",
                "suggestion": "固定领队和进入信号。",
                "next_tasks": ["慢速走位", "完整连接"],
            }
        ],
        "singing_and_rhythm_advice": "统一副歌进入拍点。",
        "dance_and_formation_advice": "先固定路线和终点。",
        "performance_and_blocking_advice": "转场时保持剧情关系清楚。",
        "next_rehearsal_plan": {
            "goal": "稳定副歌队形。",
            "focus_items": ["队形"],
            "action_steps": ["无音乐走位", "加入音乐连接"],
            "teacher_checkpoints": ["终点一致"],
        },
        "teaching_reflection": "一次只修正一个变量更容易形成稳定改进。",
        "reusable_template": {
            "template_title": "常规排练复盘模板",
            "review_focus": ["队形"],
            "observation_prompts": ["哪里仍需要老师提醒？"],
            "closing_checklist": ["任务落实到角色"],
        },
        "reviewer_notes": ["编导确认现场事实。"],
        "boundary_note": "视频仅供人工查看，AI 未分析视频内容。",
    }


class FakeMinioClient:
    """只实现上传测试需要的最小 MinIO 接口。"""

    def __init__(self) -> None:
        self.bucket_created = False
        self.objects: dict[str, bytes] = {}

    def bucket_exists(self, _bucket_name: str) -> bool:
        return self.bucket_created

    def make_bucket(self, _bucket_name: str) -> None:
        self.bucket_created = True

    def put_object(self, bucket_name: str, object_name: str, data: io.BytesIO, length: int, content_type: str):
        self.objects[f"{bucket_name}/{object_name}"] = data.read(length)
        return SimpleNamespace(object_name=object_name, content_type=content_type)


class FailingMinioClient:
    """模拟 MinIO 连接被拒绝等非 S3 协议错误。"""

    def bucket_exists(self, _bucket_name: str) -> bool:
        raise OSError("connection refused")


class RehearsalReviewSchemaTests(unittest.TestCase):
    """验证附件元数据和报告结构边界。"""

    def test_attachment_metadata_must_be_complete(self):
        with self.assertRaises(ValidationError):
            RehearsalReviewGenerateRequest(
                script_id=uuid4(),
                event_date="2026-07-12",
                rehearsal_content="合排第二幕",
                observation_notes="副歌队形略散",
                review_focus=["队形"],
                next_goal="稳定队形",
                video_object_key=f"rehearsal-reviews/{uuid4().hex}.mp4",
            )

    def test_attachment_key_cannot_escape_m08_prefix(self):
        with self.assertRaises(ValidationError):
            RehearsalReviewGenerateRequest(
                script_id=uuid4(),
                event_date="2026-07-12",
                rehearsal_content="合排第二幕",
                observation_notes="副歌队形略散",
                review_focus=["队形"],
                next_goal="稳定队形",
                video_object_key="../practice/demo.mp4",
                video_original_file_name="demo.mp4",
                video_content_type="video/mp4",
                video_size_bytes=10,
            )

    def test_attachment_key_must_be_generated_by_upload_endpoint(self):
        with self.assertRaises(ValidationError):
            RehearsalReviewGenerateRequest(
                script_id=uuid4(),
                event_date="2026-07-12",
                rehearsal_content="合排第二幕",
                observation_notes="副歌队形略散",
                review_focus=["队形"],
                next_goal="稳定队形",
                video_object_key="rehearsal-reviews/manual-name.mp4",
                video_original_file_name="demo.mp4",
                video_content_type="video/mp4",
                video_size_bytes=10,
            )

    def test_content_requires_problem_and_template(self):
        content = valid_content()
        content["issues"] = []
        with self.assertRaises(ValidationError):
            RehearsalReviewContent.model_validate(content)


class RehearsalStorageTests(unittest.TestCase):
    """验证 M08 上传校验与浏览器 Range 解析。"""

    def test_upload_uses_private_m08_prefix(self):
        client = FakeMinioClient()
        file = UploadFile(
            filename="排练片段.mp4",
            file=io.BytesIO(b"video-bytes"),
            headers=Headers({"content-type": "video/mp4"}),
        )
        result = save_rehearsal_video_upload(file, Settings(), client=client)

        self.assertTrue(result.object_key.startswith("rehearsal-reviews/"))
        self.assertEqual(result.size_bytes, len(b"video-bytes"))
        self.assertTrue(client.bucket_created)
        self.assertIn(f"hakka-stage-ai/{result.object_key}", client.objects)

    def test_upload_rejects_invalid_extension_and_empty_file(self):
        client = FakeMinioClient()
        with self.assertRaises(RehearsalStorageError):
            save_rehearsal_video_upload(
                UploadFile(filename="notes.txt", file=io.BytesIO(b"not-video")),
                Settings(),
                client=client,
            )
        with self.assertRaises(RehearsalStorageError):
            save_rehearsal_video_upload(
                UploadFile(
                    filename="empty.mp4",
                    file=io.BytesIO(b""),
                    headers=Headers({"content-type": "video/mp4"}),
                ),
                Settings(),
                client=client,
            )

    def test_upload_maps_minio_connection_failure_to_503(self):
        file = UploadFile(
            filename="排练片段.mp4",
            file=io.BytesIO(b"video-bytes"),
            headers=Headers({"content-type": "video/mp4"}),
        )
        with self.assertRaises(RehearsalStorageError) as context:
            save_rehearsal_video_upload(file, Settings(), client=FailingMinioClient())
        self.assertEqual(context.exception.status_code, 503)
        self.assertNotIn("connection refused", str(context.exception))

    def test_upload_strips_client_path_and_rejects_long_name(self):
        client = FakeMinioClient()
        file = UploadFile(
            filename=r"C:\fakepath\排练片段.mp4",
            file=io.BytesIO(b"video-bytes"),
            headers=Headers({"content-type": "video/mp4"}),
        )
        result = save_rehearsal_video_upload(file, Settings(), client=client)
        self.assertEqual(result.original_file_name, "排练片段.mp4")

        long_name = "排" * 241 + ".mp4"
        with self.assertRaises(RehearsalStorageError) as context:
            save_rehearsal_video_upload(
                UploadFile(
                    filename=long_name,
                    file=io.BytesIO(b"video-bytes"),
                    headers=Headers({"content-type": "video/mp4"}),
                ),
                Settings(),
                client=client,
            )
        self.assertEqual(context.exception.status_code, 400)

    def test_range_supports_full_open_and_suffix_requests(self):
        self.assertIsNone(parse_video_range(None, 100))
        self.assertEqual((parse_video_range("bytes=10-19", 100).start, parse_video_range("bytes=10-19", 100).end), (10, 19))
        self.assertEqual((parse_video_range("bytes=90-", 100).start, parse_video_range("bytes=90-", 100).end), (90, 99))
        self.assertEqual((parse_video_range("bytes=-10", 100).start, parse_video_range("bytes=-10", 100).end), (90, 99))
        with self.assertRaises(RehearsalStorageError) as context:
            parse_video_range("bytes=100-120", 100)
        self.assertEqual(context.exception.status_code, 416)


class RehearsalReviewServiceTests(unittest.TestCase):
    """验证 Markdown 覆盖问题闭环、下次计划、模板和视频边界。"""

    def test_markdown_contains_acceptance_sections(self):
        review = SimpleNamespace(
            title="排练复盘",
            event_type="rehearsal",
            event_date=SimpleNamespace(isoformat=lambda: "2026-07-12"),
            rehearsal_content="合排第二幕",
            review_focus=["队形"],
            has_video_attachment=True,
            video_original_file_name="排练.mp4",
            content=None,
            edited_content=valid_content(),
            raw_model_info={"provider": "deepseek", "model": "deepseek-v4-flash", "generated_at": "2026-07-12"},
        )
        markdown = render_rehearsal_review_markdown(review)
        self.assertIn("## 问题、原因与改进措施", markdown)
        self.assertIn("## 下一次排练计划", markdown)
        self.assertIn("## 可复用复盘模板", markdown)
        self.assertIn("AI 未分析视频", markdown)


class RehearsalReviewOpenApiTests(unittest.TestCase):
    """确保 M08 完整资源流在 OpenAPI 中可发现。"""

    def test_openapi_exposes_m08_resource_flow(self):
        from app.main import app

        paths = app.openapi()["paths"]
        self.assertIn("post", paths["/api/rehearsal-reviews/upload"])
        self.assertIn("post", paths["/api/rehearsal-reviews/generate"])
        self.assertIn("get", paths["/api/rehearsal-reviews"])
        detail = paths["/api/rehearsal-reviews/{rehearsal_review_id}"]
        for method in ["get", "put", "delete"]:
            self.assertIn(method, detail)
        self.assertIn("get", paths["/api/rehearsal-reviews/{rehearsal_review_id}/markdown"])
        self.assertIn("get", paths["/api/rehearsal-reviews/{rehearsal_review_id}/video"])


if __name__ == "__main__":
    unittest.main()
