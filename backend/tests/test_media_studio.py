import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from urllib.parse import unquote, urlparse
from uuid import uuid4

from app.core.config import Settings
from app.main import app
from app.services.grsai_veo import (
    VeoInputImage,
    create_public_input_url,
    create_veo_options,
    open_public_input,
    public_task_record,
    refresh_task,
    submit_task,
)


def _record() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": str(uuid4()),
        "provider_task_id": "",
        "owner_id": str(uuid4()),
        "status": "submitting",
        "progress": 0,
        "model": "veo3.1-fast",
        "prompt": "演员完成水袖转身，镜头缓慢推近",
        "aspect_ratio": "16:9",
        "source_file_name": "first.png",
        "source_mode": "upload",
        "has_last_frame": False,
        "video_url": "",
        "failure_reason": "",
        "error_message": "",
        "input_object_keys": [],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=2)).isoformat(),
    }


class VeoOptionsTests(unittest.TestCase):
    """选项接口只公开能力状态，不泄露密钥或内部节点。"""

    def test_options_only_expose_documented_models_and_ratios(self):
        options = create_veo_options(Settings(grsai_api_key="secret"))

        self.assertTrue(options["configured"])
        self.assertEqual([item["code"] for item in options["models"]], ["veo3.1-fast", "veo3.1-pro"])
        self.assertEqual(options["aspect_ratios"], ["16:9", "9:16"])
        self.assertNotIn("api_key", options)
        self.assertNotIn("base_url", options)


class VeoProviderTests(unittest.TestCase):
    """验证 GRS AI 请求字段与结果归一化，测试不会发起真实计费调用。"""

    @patch("app.services.grsai_veo.save_task_record")
    @patch("app.services.grsai_veo._request_json")
    def test_submit_uses_polling_mode_and_keeps_provider_id_private(self, request_json: Mock, save: Mock):
        request_json.return_value = {"code": 0, "msg": "success", "data": {"id": "provider-task-1"}}
        record = _record()
        settings = Settings(grsai_api_key="secret", grsai_base_url="https://grs.example")

        result = submit_task(record, "https://cdn.example/first.png", settings=settings)

        self.assertEqual(result["provider_task_id"], "provider-task-1")
        payload = request_json.call_args.args[1]
        self.assertEqual(payload["webHook"], "-1")
        self.assertTrue(payload["shutProgress"])
        self.assertEqual(payload["firstFrameUrl"], "https://cdn.example/first.png")
        self.assertNotIn("provider_task_id", public_task_record(result))
        save.assert_called_once()

    @patch("app.services.grsai_veo.save_task_record")
    @patch("app.services.grsai_veo._request_json")
    def test_refresh_maps_success_and_failure(self, request_json: Mock, save: Mock):
        record = _record()
        record.update(provider_task_id="provider-task-2", status="running")
        settings = Settings(grsai_api_key="secret")
        request_json.return_value = {
            "code": 0,
            "data": {
                "id": "provider-task-2",
                "url": "https://cdn.example/result.mp4",
                "progress": 100,
                "status": "succeeded",
            },
        }

        succeeded = refresh_task(record, settings)

        self.assertEqual(succeeded["status"], "succeeded")
        self.assertEqual(succeeded["video_url"], "https://cdn.example/result.mp4")

        failed_record = _record()
        failed_record.update(provider_task_id="provider-task-3", status="running")
        request_json.return_value = {
            "code": 0,
            "data": {"status": "failed", "progress": 100, "failure_reason": "input_moderation"},
        }
        failed = refresh_task(failed_record, settings)
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["failure_reason"], "input_moderation")
        self.assertEqual(save.call_count, 2)


class VeoInputTokenTests(unittest.TestCase):
    """上传图片只通过有签名、有目录限制、有过期时间的短链公开。"""

    @patch("app.services.grsai_veo._minio_client")
    def test_signed_input_url_round_trip(self, minio_factory: Mock):
        minio_response = object()
        minio_factory.return_value.get_object.return_value = minio_response
        settings = Settings(
            auth_secret_key="unit-test-secret-at-least-32-bytes",
            grsai_public_base_url="https://api.example.com",
        )
        image = VeoInputImage(
            object_key="media-studio/veo-inputs/abc.png",
            original_file_name="first.png",
            content_type="image/png",
            size_bytes=128,
        )

        public_url = create_public_input_url(image, settings)
        token = unquote(urlparse(public_url).path.rsplit("/", 1)[-1])
        response, content_type = open_public_input(token, settings)

        self.assertEqual(response, minio_response)
        self.assertEqual(content_type, "image/png")
        minio_factory.return_value.get_object.assert_called_once_with(
            settings.minio_bucket,
            image.object_key,
        )


class VeoOpenApiTests(unittest.TestCase):
    """新增中文业务接口必须注册到 FastAPI，同时临时素材路由不进入公开文档。"""

    def test_media_studio_routes_are_registered(self):
        schema = app.openapi()
        self.assertIn("/api/media-studio/veo/options", schema["paths"])
        self.assertIn("/api/media-studio/veo/tasks", schema["paths"])
        self.assertIn("/api/media-studio/veo/tasks/{task_id}", schema["paths"])
        self.assertNotIn("/api/public/media-studio/veo-inputs/{token}", schema["paths"])


if __name__ == "__main__":
    unittest.main()
