import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from urllib.parse import unquote, urlparse
from uuid import uuid4

from app.core.config import Settings
from app.main import app
from app.services.wan_animate import (
    MotionInputAsset,
    MotionResultInfo,
    MotionTransferError,
    create_motion_public_input_url,
    create_motion_transfer_options,
    get_motion_task_record,
    open_motion_public_input,
    parse_motion_video_range,
    public_motion_task_record,
    refresh_motion_task,
    submit_motion_task,
)


def _record() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": str(uuid4()),
        "provider_task_id": "",
        "owner_id": str(uuid4()),
        "status": "submitting",
        "progress": 0,
        "provider": "dashscope",
        "model": "wan2.2-animate-move",
        "mode": "wan-std",
        "resolution": "720P",
        "watermark": True,
        "person_file_name": "actor.png",
        "motion_file_name": "dance.mp4",
        "motion_duration_seconds": 8.5,
        "input_object_keys": [],
        "result_object_key": "",
        "result_content_type": "",
        "result_size_bytes": 0,
        "result_available": False,
        "result_persisted": False,
        "video_url": "",
        "storage_warning": "",
        "failure_reason": "",
        "error_message": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=24)).isoformat(),
    }


class MotionTransferOptionsTests(unittest.TestCase):
    """选项接口必须如实报告密钥与公网回源地址是否同时就绪。"""

    def test_options_expose_documented_modes_without_secrets(self):
        options = create_motion_transfer_options(
            Settings(
                dashscope_api_key="secret",
                video_public_base_url="https://api.example.com",
            )
        )

        self.assertTrue(options["configured"])
        self.assertEqual(options["model"], "wan2.2-animate-move")
        self.assertEqual([item["code"] for item in options["modes"]], ["wan-std", "wan-pro"])
        self.assertEqual(options["image_max_upload_mb"], 5)
        self.assertEqual(options["video_max_upload_mb"], 200)
        self.assertEqual(options["image_dimension_min_pixels"], 200)
        self.assertEqual(options["image_dimension_max_pixels"], 4096)
        self.assertEqual(options["video_dimension_min_pixels"], 200)
        self.assertEqual(options["video_dimension_max_pixels"], 2048)
        self.assertAlmostEqual(options["aspect_ratio_min"], 1 / 3)
        self.assertEqual(options["aspect_ratio_max"], 3)
        self.assertEqual(options["resolution"], "720P")
        self.assertNotIn("api_key", options)
        self.assertNotIn("base_url", options)

    def test_real_mode_requires_public_input_base_url(self):
        options = create_motion_transfer_options(Settings(dashscope_api_key="secret"))
        self.assertFalse(options["configured"])
        self.assertFalse(options["file_upload_available"])


class MotionTransferProviderTests(unittest.TestCase):
    """验证百炼动作模仿请求与结果转存映射，不发起真实供应商调用。"""

    @patch("app.services.wan_animate.save_motion_task_record")
    @patch("app.services.wan_animate._request_json")
    def test_submit_uses_animate_endpoint_and_expected_payload(self, request_json: Mock, save: Mock):
        request_json.return_value = {"output": {"task_id": "animate-task-1", "task_status": "PENDING"}}
        record = _record()
        settings = Settings(
            dashscope_api_key="secret",
            dashscope_base_url="https://workspace.example.com",
        )

        result = submit_motion_task(
            record,
            "https://cdn.example/actor.png",
            "https://cdn.example/dance.mp4",
            ["media-studio/motion-inputs/actor.png", "media-studio/motion-inputs/dance.mp4"],
            settings,
        )

        url, payload = request_json.call_args.args[:2]
        self.assertEqual(
            url,
            "https://workspace.example.com/api/v1/services/aigc/image2video/video-synthesis",
        )
        self.assertEqual(payload["model"], "wan2.2-animate-move")
        self.assertEqual(payload["input"]["image_url"], "https://cdn.example/actor.png")
        self.assertEqual(payload["input"]["video_url"], "https://cdn.example/dance.mp4")
        self.assertTrue(payload["input"]["watermark"])
        self.assertEqual(payload["parameters"], {"check_image": True, "mode": "wan-std"})
        self.assertEqual(result["provider_task_id"], "animate-task-1")
        self.assertNotIn("provider_task_id", public_motion_task_record(result))
        self.assertNotIn("input_object_keys", public_motion_task_record(result))
        self.assertNotIn("video_url", public_motion_task_record(result))
        save.assert_called_once()

    @patch("app.services.wan_animate.save_motion_task_record")
    @patch("app.services.wan_animate._cleanup_input_objects")
    @patch("app.services.wan_animate.persist_motion_result")
    @patch("app.services.wan_animate._request_json")
    def test_refresh_persists_success_result(
        self,
        request_json: Mock,
        persist_result: Mock,
        cleanup: Mock,
        save: Mock,
    ):
        record = _record()
        record.update(provider_task_id="animate-task-2", status="running")
        request_json.return_value = {
            "output": {
                "task_id": "animate-task-2",
                "task_status": "SUCCEEDED",
                "results": {"video_url": "https://cdn.example/result.mp4"},
            }
        }
        persist_result.return_value = MotionResultInfo(
            object_key=f"media-studio/motion-results/{record['id']}.mp4",
            content_type="video/mp4",
            size_bytes=4096,
        )

        result = refresh_motion_task(record, Settings(dashscope_api_key="secret"))

        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["result_available"])
        self.assertTrue(result["result_persisted"])
        self.assertNotIn("result_object_key", public_motion_task_record(result))
        self.assertNotIn("video_url", public_motion_task_record(result))
        persist_result.assert_called_once()
        self.assertEqual(persist_result.call_args.args[0], "https://cdn.example/result.mp4")
        cleanup.assert_called_once()
        save.assert_called_once()


class MotionTransferInputTokenTests(unittest.TestCase):
    """图片和视频只通过有签名、有目录限制的短链交给百炼读取。"""

    @patch("app.services.wan_animate._minio_client")
    def test_signed_video_input_round_trip(self, minio_factory: Mock):
        response = object()
        minio_factory.return_value.get_object.return_value = response
        minio_factory.return_value.stat_object.return_value.size = 2048
        minio_factory.return_value.stat_object.return_value.content_type = "video/mp4"
        settings = Settings(
            auth_secret_key="unit-test-secret-at-least-32-bytes",
            video_public_base_url="https://api.example.com",
        )
        asset = MotionInputAsset(
            object_key="media-studio/motion-inputs/dance.mp4",
            original_file_name="dance.mp4",
            content_type="video/mp4",
            size_bytes=2048,
            media_kind="video",
        )

        public_url = create_motion_public_input_url(asset, settings)
        token = unquote(urlparse(public_url).path.rsplit("/", 1)[-1])
        opened, content_type, size_bytes = open_motion_public_input(token, settings)

        self.assertEqual(opened, response)
        self.assertEqual(content_type, "video/mp4")
        self.assertEqual(size_bytes, 2048)

    def test_result_range_supports_standard_and_suffix_ranges(self):
        self.assertEqual(parse_motion_video_range("bytes=100-199", 1000).length, 100)
        self.assertEqual(parse_motion_video_range("bytes=-50", 1000).start, 950)


class MotionTransferOwnershipTests(unittest.TestCase):
    """Redis 任务必须按账号读取，未知任务和越权读取统一返回 404。"""

    @patch("app.services.wan_animate._redis_client")
    def test_task_record_rejects_other_owner(self, redis_factory: Mock):
        record = _record()
        redis_factory.return_value.get.return_value = json.dumps(record)

        with self.assertRaises(MotionTransferError) as context:
            get_motion_task_record(record["id"], uuid4(), Settings())

        self.assertEqual(context.exception.status_code, 404)


class MotionTransferOpenApiTests(unittest.TestCase):
    """动作模仿业务接口进入 OpenAPI，供应商回源地址保持隐藏。"""

    def test_motion_transfer_routes_are_registered(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/media-studio/motion-transfer/options", paths)
        self.assertIn("/api/media-studio/motion-transfer/tasks", paths)
        self.assertIn("/api/media-studio/motion-transfer/tasks/{task_id}", paths)
        self.assertIn("/api/media-studio/motion-transfer/tasks/{task_id}/result", paths)
        self.assertNotIn("/api/public/media-studio/motion-inputs/{token}", paths)


if __name__ == "__main__":
    unittest.main()
