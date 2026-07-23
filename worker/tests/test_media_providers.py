import base64
import unittest
from contextlib import contextmanager
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import httpx

from app.media_providers.grsai import GrsaiProvider, _extract_outputs
from app.media_providers.mock import MockMediaProvider
from app.media_providers.runninghub import RunningHubProvider, _media_type_from_output
from app.media_generation_processor import MediaGenerationProcessor, normalize_provider_status
from app.media_storage import WorkerMediaStorage
from app.models import MediaAsset, MediaGeneration


class _FakeObjectResponse(BytesIO):
    def release_conn(self):
        return None


class _FakeMinioClient:
    def __init__(self) -> None:
        self.saved = None
        self.source = b""

    def put_object(self, bucket, object_key, stream, size, content_type):
        self.saved = {
            "bucket": bucket,
            "object_key": object_key,
            "data": stream.read(),
            "size": size,
            "content_type": content_type,
        }

    def stat_object(self, bucket, object_key):
        return SimpleNamespace(size=len(self.source))

    def get_object(self, bucket, object_key):
        return _FakeObjectResponse(self.source)


class MediaProviderNormalizationTests(unittest.TestCase):
    """供应商响应格式只在适配层出现，上层始终得到统一媒体类型和 URL。"""

    def test_grsai_extracts_string_and_object_urls(self):
        outputs = _extract_outputs({"results": ["https://example.com/a.png", {"url": "https://example.com/b.webp"}]})
        self.assertEqual([item.url for item in outputs], ["https://example.com/a.png", "https://example.com/b.webp"])
        self.assertTrue(all(item.media_type == "image" for item in outputs))

    def test_runninghub_maps_audio_extension(self):
        self.assertEqual(_media_type_from_output("wav", "image"), "audio")
        self.assertEqual(_media_type_from_output("unknown", "video"), "video")

    def test_mock_provider_never_calls_external_network(self):
        generation = MediaGeneration(provider="grsai", capability="image", owner_id=uuid4())
        result = MockMediaProvider("grsai").query("mock-task", generation)
        self.assertEqual(result.status, "succeeded")
        self.assertTrue(result.outputs[0].url.startswith("data:image/png;base64,"))

    def test_provider_status_is_normalized_for_database_scheduling(self):
        """GRS AI 的小写状态必须能进入只维护一套枚举的本地调度状态。"""

        self.assertEqual(normalize_provider_status("running"), "RUNNING")
        self.assertEqual(normalize_provider_status(" Pending "), "PENDING")
        self.assertEqual(normalize_provider_status(None), "UNKNOWN")

    @patch("app.media_providers.runninghub.httpx.post")
    def test_runninghub_uses_published_output_node_selection_when_response_has_node_id(self, post: Mock):
        response = Mock()
        response.json.return_value = {
            "status": "SUCCESS",
            "results": [
                {"nodeId": "17", "url": "https://example.com/selected.wav", "outputType": "wav"},
                {"nodeId": "99", "url": "https://example.com/hidden.wav", "outputType": "wav"},
            ],
        }
        post.return_value = response
        settings = SimpleNamespace(
            runninghub_api_key="test-key",
            runninghub_base_url="https://runninghub.example",
            media_http_timeout_seconds=30,
        )
        provider = RunningHubProvider(settings, Mock())
        generation = MediaGeneration(
            provider="runninghub",
            capability="audio",
            request_parameters={"_enabled_output_nodes": ["17"]},
            owner_id=uuid4(),
        )

        result = provider.query("running-task-1", generation)

        self.assertEqual(result.status, "succeeded")
        self.assertEqual([item.url for item in result.outputs], ["https://example.com/selected.wav"])

    @patch("app.media_providers.runninghub.httpx.post")
    def test_runninghub_query_converts_http_200_business_error_to_failed_result(self, post: Mock):
        response = Mock()
        response.json.return_value = {"code": 813, "msg": "TASK_NOT_FOUND"}
        post.return_value = response
        settings = SimpleNamespace(
            runninghub_api_key="test-key",
            runninghub_base_url="https://runninghub.example",
            media_http_timeout_seconds=30,
        )
        provider = RunningHubProvider(settings, Mock())
        generation = MediaGeneration(provider="runninghub", capability="audio", owner_id=uuid4())

        result = provider.query("missing-task", generation)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "RUNNINGHUB_813")
        self.assertIn("TASK_NOT_FOUND", result.error_message)

    @patch("app.media_providers.runninghub.httpx.post")
    def test_runninghub_submit_preserves_provider_initial_status(self, post: Mock):
        response = Mock()
        response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {"taskId": "running-task-2", "taskStatus": "RUNNING"},
        }
        post.return_value = response
        settings = SimpleNamespace(
            runninghub_api_key="test-key",
            runninghub_base_url="https://runninghub.example",
            media_http_timeout_seconds=30,
        )
        provider = RunningHubProvider(settings, Mock())
        generation = MediaGeneration(provider="runninghub", capability="audio", owner_id=uuid4())
        version = SimpleNamespace(parameter_config=[])
        template = SimpleNamespace(external_workflow_id="workflow-1")

        result = provider.submit(None, generation, {}, version, template)

        self.assertEqual(result.task_id, "running-task-2")
        self.assertEqual(result.provider_status, "RUNNING")
        self.assertNotIn("apiKey", result.request_payload)

    @patch("app.media_providers.runninghub.httpx.post")
    def test_runninghub_submit_rejects_immediate_failed_status(self, post: Mock):
        """平台若在创建响应中直接失败，不能留下一个永远不会再扫描的悬挂任务。"""

        response = Mock()
        response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {"taskId": "running-task-failed", "taskStatus": "FAILED", "promptTips": "node invalid"},
        }
        post.return_value = response
        settings = SimpleNamespace(
            runninghub_api_key="test-key",
            runninghub_base_url="https://runninghub.example",
            media_http_timeout_seconds=30,
        )
        provider = RunningHubProvider(settings, Mock())
        generation = MediaGeneration(provider="runninghub", capability="audio", owner_id=uuid4())
        version = SimpleNamespace(parameter_config=[])
        template = SimpleNamespace(external_workflow_id="workflow-1")

        with self.assertRaisesRegex(RuntimeError, "node invalid"):
            provider.submit(None, generation, {}, version, template)

    @patch("app.media_providers.runninghub.httpx.post")
    def test_runninghub_optional_mapped_file_can_use_workflow_default(self, post: Mock):
        response = Mock()
        response.json.return_value = {
            "code": 0,
            "msg": "success",
            "data": {"taskId": "running-task-3", "taskStatus": "QUEUED"},
        }
        post.return_value = response
        settings = SimpleNamespace(
            runninghub_api_key="test-key",
            runninghub_base_url="https://runninghub.example",
            media_http_timeout_seconds=30,
        )
        provider = RunningHubProvider(settings, Mock())
        generation = MediaGeneration(
            provider="runninghub",
            capability="audio",
            request_parameters={"_optional_file_keys": ["audio_15"]},
            owner_id=uuid4(),
        )
        version = SimpleNamespace(
            parameter_config=[
                {
                    "key": "audio_15",
                    "node_id": "15",
                    "field_name": "audio",
                    "label": "情绪参考",
                    "value_type": "file",
                    "required": True,
                    "visibility": "basic",
                    "asset_role": "audio_15",
                    "order": 0,
                }
            ]
        )
        template = SimpleNamespace(external_workflow_id="workflow-1")

        result = provider.submit(None, generation, {}, version, template)

        self.assertEqual(result.task_id, "running-task-3")
        self.assertEqual(post.call_args.kwargs["json"]["nodeInfoList"], [])


class MediaResultTransferTests(unittest.TestCase):
    """GRS AI Mock 结果仍需经过真实的转存编码路径。"""

    def test_data_url_is_saved_under_media_results(self):
        expected = b"small-image-result"
        storage = WorkerMediaStorage.__new__(WorkerMediaStorage)
        storage.settings = SimpleNamespace(minio_bucket="test-bucket")
        storage.client = _FakeMinioClient()
        storage.ensure_bucket = lambda: None

        object_key, content_type, size, filename = storage.transfer_result(
            f"data:image/png;base64,{base64.b64encode(expected).decode()}", "image", "image/png"
        )

        self.assertTrue(object_key.startswith("media-results/"))
        self.assertTrue(filename.endswith(".png"))
        self.assertEqual(content_type, "image/png")
        self.assertEqual(size, len(expected))
        self.assertEqual(storage.client.saved["data"], expected)

    def test_private_input_can_be_encoded_as_bounded_data_url(self):
        storage = WorkerMediaStorage.__new__(WorkerMediaStorage)
        storage.settings = SimpleNamespace(minio_bucket="test-bucket")
        storage.client = _FakeMinioClient()
        storage.client.source = b"reference-image"

        data_url = storage.read_data_url("media-inputs/reference.png", "image/png")

        self.assertTrue(data_url.startswith("data:image/png;base64,"))
        encoded = data_url.split(",", 1)[1]
        self.assertEqual(base64.b64decode(encoded), b"reference-image")

    def test_minio_network_stream_is_staged_as_seekable_file_for_multipart(self):
        storage = WorkerMediaStorage.__new__(WorkerMediaStorage)
        storage.settings = SimpleNamespace(minio_bucket="test-bucket")
        storage.client = _FakeMinioClient()
        storage.client.source = b"audio-from-minio"

        with storage.staged_upload("media-inputs/reference.wav", len(storage.client.source)) as (stream, size):
            self.assertTrue(stream.seekable())
            self.assertEqual(size, len(storage.client.source))
            self.assertEqual(stream.read(), storage.client.source)
            stream.seek(0)
            self.assertEqual(stream.read(5), b"audio")

            # 直接序列化 multipart，确保协议层声明长度与实际发送字节一致。
            request = httpx.Request(
                "POST",
                "https://runninghub.example/openapi/v2/media/upload/binary",
                files={"file": ("reference.wav", stream, "audio/wav")},
            )
            actual_body_size = sum(len(chunk) for chunk in request.stream)
            self.assertEqual(int(request.headers["Content-Length"]), actual_body_size)

    def test_staged_upload_rejects_truncated_minio_object(self):
        storage = WorkerMediaStorage.__new__(WorkerMediaStorage)
        storage.settings = SimpleNamespace(minio_bucket="test-bucket")
        storage.client = _FakeMinioClient()
        storage.client.source = b"short"

        with self.assertRaisesRegex(RuntimeError, "记录大小 100 字节，实际读取 5 字节"):
            with storage.staged_upload("media-inputs/reference.wav", 100):
                pass


class RunningHubUploadTests(unittest.TestCase):
    """RunningHub 上传必须使用可定位文件，避免 multipart 长度与实际数据不一致。"""

    @patch("app.media_providers.runninghub.httpx.post")
    def test_upload_uses_seekable_staged_file_and_returns_provider_filename(self, post: Mock):
        expected = b"runninghub-audio"
        storage = Mock()

        @contextmanager
        def staged_upload(_object_key, expected_size):
            self.assertEqual(expected_size, len(expected))
            stream = BytesIO(expected)
            try:
                yield stream, len(expected)
            finally:
                stream.close()

        storage.staged_upload.side_effect = staged_upload
        response = Mock()
        response.json.return_value = {"code": 0, "msg": "success", "data": {"fileName": "uploaded.wav"}}

        def inspect_upload(*_args, **kwargs):
            upload_file = kwargs["files"]["file"][1]
            self.assertTrue(upload_file.seekable())
            self.assertEqual(upload_file.read(), expected)
            return response

        post.side_effect = inspect_upload
        settings = SimpleNamespace(
            runninghub_api_key="test-key",
            runninghub_base_url="https://runninghub.example",
            media_http_timeout_seconds=30,
        )
        provider = RunningHubProvider(settings, storage)
        asset = MediaAsset(
            id=uuid4(),
            role="input",
            media_type="audio",
            storage_mode="managed",
            object_key="media-inputs/reference.wav",
            original_file_name="reference.wav",
            content_type="audio/wav",
            size_bytes=len(expected),
            owner_id=uuid4(),
        )

        filename = provider._upload_asset(asset)

        self.assertEqual(filename, "uploaded.wav")
        storage.staged_upload.assert_called_once_with(asset.object_key, len(expected))


class GrsaiUnifiedApiTests(unittest.TestCase):
    """验证图生图使用 unified 接口，同时不把 Base64 输入写入任务运行记录。"""

    @patch("app.media_providers.grsai.httpx.post")
    def test_submit_image_to_image_orders_multiple_inputs_and_sanitizes_snapshot(self, post: Mock):
        response = Mock()
        response.json.return_value = {"id": "grs-task-1", "status": "running"}
        post.return_value = response
        storage = Mock()
        storage.read_data_url.side_effect = [
            "data:image/png;base64,Zmlyc3QtaW1hZ2U=",
            "data:image/webp;base64,c2Vjb25kLWltYWdl",
        ]
        settings = SimpleNamespace(
            grsai_api_key="test-key",
            grsai_base_url="https://grs.example",
            media_http_timeout_seconds=30,
        )
        provider = GrsaiProvider(settings, storage)
        generation = MediaGeneration(
            provider="grsai",
            capability="image",
            model="nano-banana-fast",
            prompt="保留人物并修改舞台背景",
            request_parameters={"_api_mode": "unified", "aspectRatio": "16:9", "imageSize": "1K"},
            owner_id=uuid4(),
        )
        asset = MediaAsset(
            id=uuid4(),
            role="input",
            media_type="image",
            storage_mode="managed",
            object_key="media-inputs/reference.png",
            content_type="image/png",
            size_bytes=1024,
            owner_id=uuid4(),
        )
        second_asset = MediaAsset(
            id=uuid4(),
            role="input",
            media_type="image",
            storage_mode="managed",
            object_key="media-inputs/reference-2.webp",
            content_type="image/webp",
            size_bytes=2048,
            owner_id=uuid4(),
        )

        # 故意把第二张放在字典前面，模拟 JSONB 读取后键顺序变化。
        result = provider.submit(
            None,
            generation,
            {"source_image_2": second_asset, "source_image": asset},
            None,
            None,
        )

        self.assertEqual(result.task_id, "grs-task-1")
        self.assertEqual(post.call_args.args[0], "https://grs.example/v1/api/generate")
        self.assertEqual(
            post.call_args.kwargs["json"]["images"],
            [
                "data:image/png;base64,Zmlyc3QtaW1hZ2U=",
                "data:image/webp;base64,c2Vjb25kLWltYWdl",
            ],
        )
        self.assertEqual(post.call_args.kwargs["json"]["replyType"], "async")
        self.assertEqual(result.provider_status, "RUNNING")
        self.assertEqual(
            [item["asset_id"] for item in result.request_payload["images"]],
            [str(asset.id), str(second_asset.id)],
        )
        self.assertNotIn("base64", str(result.request_payload))

    @patch("app.media_providers.grsai.httpx.post")
    def test_submit_rejects_immediate_violation(self, post: Mock):
        """异步创建若已明确违规，应立即失败而不是写入无法轮询的任务。"""

        response = Mock(status_code=400)
        response.json.return_value = {"id": "grs-task-violation", "status": "violation", "error": "blocked"}
        post.return_value = response
        storage = Mock()
        storage.read_data_url.return_value = "data:image/png;base64,cHJpdmF0ZS1pbWFnZQ=="
        settings = SimpleNamespace(
            grsai_api_key="test-key",
            grsai_base_url="https://grs.example",
            media_http_timeout_seconds=30,
        )
        provider = GrsaiProvider(settings, storage)
        generation = MediaGeneration(
            provider="grsai",
            capability="image",
            model="nano-banana-fast",
            prompt="测试",
            request_parameters={"_api_mode": "unified"},
            owner_id=uuid4(),
        )
        asset = MediaAsset(
            id=uuid4(), role="input", media_type="image", storage_mode="managed",
            object_key="media-inputs/reference.png", content_type="image/png", size_bytes=1024,
            owner_id=uuid4(),
        )

        with self.assertRaisesRegex(RuntimeError, "blocked"):
            provider.submit(None, generation, {"source_image": asset}, None, None)


class GrsaiQueryTests(unittest.TestCase):
    """覆盖 Unified async 查询的成功、审核失败和结果过期终态。"""

    @staticmethod
    def _provider() -> GrsaiProvider:
        settings = SimpleNamespace(
            grsai_api_key="test-key",
            grsai_base_url="https://grs.example",
            media_http_timeout_seconds=30,
        )
        return GrsaiProvider(settings, Mock())

    @staticmethod
    def _generation() -> MediaGeneration:
        return MediaGeneration(
            provider="grsai",
            capability="image",
            request_parameters={"_api_mode": "unified"},
            owner_id=uuid4(),
        )

    @patch("app.media_providers.grsai.httpx.get")
    def test_query_extracts_async_success_result(self, get: Mock):
        response = Mock(status_code=200)
        response.json.return_value = {
            "id": "grs-task-success",
            "status": "succeeded",
            "results": [{"url": "https://example.com/result.jpg"}],
        }
        get.return_value = response

        result = self._provider().query("grs-task-success", self._generation())

        self.assertEqual(result.status, "succeeded")
        self.assertEqual([item.url for item in result.outputs], ["https://example.com/result.jpg"])

    @patch("app.media_providers.grsai.httpx.get")
    def test_query_maps_violation_to_terminal_failure(self, get: Mock):
        # 官方接口可能使用 HTTP 400 承载结构化的审核失败，适配器仍应保留业务语义。
        response = Mock(status_code=400)
        response.json.return_value = {
            "id": "grs-task-violation",
            "status": "violation",
            "error": "content rejected",
        }
        get.return_value = response

        result = self._provider().query("grs-task-violation", self._generation())

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "GRSAI_VIOLATION")
        self.assertEqual(result.error_message, "content rejected")

    @patch("app.media_providers.grsai.httpx.get")
    def test_query_maps_expired_result_to_terminal_failure(self, get: Mock):
        response = Mock(status_code=404)
        response.json.return_value = {"error": "result not exist, valid for 2 hours"}
        get.return_value = response

        result = self._provider().query("grs-task-expired", self._generation())

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "GRSAI_RESULT_NOT_FOUND")
        self.assertIn("valid for 2 hours", result.error_message)


class MediaPollPolicyTests(unittest.TestCase):
    """GRS AI 使用独立低频策略，RunningHub 保持原有通用策略。"""

    def test_provider_specific_poll_policy_and_safe_minimum(self):
        processor = MediaGenerationProcessor.__new__(MediaGenerationProcessor)
        processor.settings = SimpleNamespace(
            grsai_poll_interval_seconds=15,
            grsai_poll_max_count=400,
            media_poll_interval_seconds=5,
            media_poll_max_count=720,
        )

        self.assertEqual(processor._poll_policy("grsai"), (15, 400))
        self.assertEqual(processor._poll_policy("runninghub"), (5, 720))

        processor.settings.grsai_poll_interval_seconds = 0
        processor.settings.grsai_poll_max_count = 0
        self.assertEqual(processor._poll_policy("grsai"), (1, 1))

    def test_due_scan_is_case_insensitive_for_existing_provider_statuses(self):
        """升级前保存的小写 `running` 也必须被到期扫描重新捞起。"""

        captured: dict[str, str] = {}
        fake_db = Mock()

        def capture_statement(statement):
            captured["sql"] = str(statement).lower()
            return SimpleNamespace(all=lambda: [])

        fake_db.scalars.side_effect = capture_statement

        @contextmanager
        def fake_session():
            yield fake_db

        processor = MediaGenerationProcessor.__new__(MediaGenerationProcessor)
        with patch("app.media_generation_processor.SessionLocal", side_effect=fake_session):
            processor.poll_due()

        self.assertIn("upper(provider_task_runs.provider_status)", captured["sql"])


if __name__ == "__main__":
    unittest.main()
