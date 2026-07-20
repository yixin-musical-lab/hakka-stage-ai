import json
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes.media_generations import _validate_runninghub_audio_asset
from app.core.schema_migrations import run_schema_migrations
from app.main import app
from app.models import MediaGeneration
from app.schemas.media_generation import MediaGenerationCreateRequest, MediaWorkbenchInputConfig
from app.services.media_workbench_service import (
    DEFAULT_WORKBENCHES,
    validate_workbench_configuration,
    validate_workflow_mapping,
)
from app.services.workflow_analyzer import WorkflowAnalysisError, analyze_workflow, parse_workflow_json


class WorkflowAnalyzerTests(unittest.TestCase):
    """验证自动识别的核心安全边界，避免把节点连线误当成运行参数。"""

    def _workflow(self) -> dict:
        return {
            "1": {"class_type": "LoadAudio", "inputs": {"audio": "voice.wav"}, "_meta": {"title": "参考音色"}},
            "2": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": "你好"}, "_meta": {"title": "合成文本"}},
            "3": {
                "class_type": "IndexTTS2Run",
                "inputs": {"audio": ["1", 0], "text": ["2", 0], "temperature": 0.8, "unload_model": True},
            },
            "4": {"class_type": "SaveAudio", "inputs": {"audio": ["3", 0]}, "_meta": {"title": "主音频输出"}},
            "5": {"class_type": "SaveAudioMP3", "inputs": {"audio": ["3", 0]}, "_meta": {"title": "(DEPRECATED) 旧输出"}},
        }

    def test_analyzer_finds_file_text_parameters_and_primary_output(self):
        analysis = analyze_workflow(self._workflow())
        parameters = analysis["parameters"]

        self.assertEqual(analysis["node_count"], 5)
        self.assertEqual([(item["node_id"], item["field_name"]) for item in parameters if item["value_type"] == "file"], [("1", "audio")])
        self.assertTrue(any(item["node_id"] == "2" and item["value_type"] == "text" for item in parameters))
        self.assertFalse(any(item["field_name"] in {"audio", "text"} and item["node_id"] == "3" for item in parameters))
        self.assertFalse(any(item["field_name"] == "unload_model" for item in parameters))
        self.assertTrue(analysis["outputs"][0]["primary"])
        self.assertFalse(analysis["outputs"][1]["enabled"])

    def test_parser_rejects_comfyui_ui_format_without_class_type(self):
        raw = json.dumps({"nodes": [{"id": 1, "type": "LoadAudio"}]}).encode()
        with self.assertRaises(WorkflowAnalysisError):
            parse_workflow_json(raw)


class MediaGenerationSchemaTests(unittest.TestCase):
    """验证供应商专属字段在进入数据库前被拦截。"""

    def test_grsai_defaults_to_nano_banana_fast(self):
        request = MediaGenerationCreateRequest(provider="grsai", capability="image", prompt="舞台概念图")
        self.assertEqual(request.model, "nano-banana-fast")

    def test_grsai_rejects_non_image_capability(self):
        with self.assertRaises(ValidationError):
            MediaGenerationCreateRequest(provider="grsai", capability="audio", prompt="音乐")

    def test_runninghub_requires_published_workflow_version_reference(self):
        with self.assertRaises(ValidationError):
            MediaGenerationCreateRequest(provider="runninghub", capability="audio")

        request = MediaGenerationCreateRequest(
            provider="runninghub", capability="audio", workflow_version_id=uuid4()
        )
        self.assertIsNotNone(request.workflow_version_id)


class MediaWorkbenchConfigurationTests(unittest.TestCase):
    """验证两个工作台的固定职责以及 RunningHub 字段映射边界。"""

    def test_default_workbenches_have_valid_input_schema(self):
        audio = DEFAULT_WORKBENCHES["audio-clone"]
        image = DEFAULT_WORKBENCHES["image-to-image"]

        MediaWorkbenchInputConfig.model_validate(audio["input_config"])
        MediaWorkbenchInputConfig.model_validate(image["input_config"])
        self.assertEqual(audio["provider"], "runninghub")
        self.assertEqual(image["provider_api_mode"], "unified")
        self.assertIn("workbench_slug", MediaGeneration.__table__.columns)

    def test_audio_mapping_accepts_text_file_and_exposed_parameters(self):
        version = SimpleNamespace(
            status="published",
            parameter_config=[
                {"key": "2.value", "value_type": "text"},
                {"key": "1.audio", "value_type": "file"},
                {"key": "3.temperature", "value_type": "number"},
            ],
        )
        db = SimpleNamespace(get=lambda _model, _version_id: version)

        validate_workflow_mapping(
            db,
            uuid4(),
            {
                "prompt": {"target_parameter_key": "2.value"},
                "primary_asset": {"label": "参考音色", "required": True, "target_parameter_key": "1.audio"},
                "secondary_asset": None,
                "exposed_parameter_keys": ["3.temperature"],
            },
        )

    def test_audio_mapping_rejects_file_bound_to_text_parameter(self):
        version = SimpleNamespace(
            status="published",
            parameter_config=[
                {"key": "2.value", "value_type": "text"},
                {"key": "1.audio", "value_type": "file"},
            ],
        )
        db = SimpleNamespace(get=lambda _model, _version_id: version)

        with self.assertRaisesRegex(ValueError, "必须映射到工作流文件参数"):
            validate_workflow_mapping(
                db,
                uuid4(),
                {
                    "prompt": {"target_parameter_key": "2.value"},
                    "primary_asset": {"label": "参考音色", "required": True, "target_parameter_key": "2.value"},
                    "secondary_asset": None,
                    "exposed_parameter_keys": [],
                },
            )

    def test_audio_mapping_rejects_unmapped_required_file_node(self):
        version = SimpleNamespace(
            status="published",
            parameter_config=[
                {"key": "2.value", "value_type": "text"},
                {"key": "1.audio", "label": "参考音色", "value_type": "file", "required": True},
                {"key": "3.audio", "label": "情绪音频", "value_type": "file", "required": True},
            ],
        )
        db = SimpleNamespace(get=lambda _model, _version_id: version)

        with self.assertRaisesRegex(ValueError, "仍有必填文件节点未绑定"):
            validate_workflow_mapping(
                db,
                uuid4(),
                {
                    "prompt": {"target_parameter_key": "2.value"},
                    "primary_asset": {"label": "参考音色", "required": True, "target_parameter_key": "1.audio"},
                    "secondary_asset": None,
                    "exposed_parameter_keys": [],
                },
            )

    def test_openapi_exposes_focused_workbench_and_teacher_configuration_paths(self):
        paths = app.openapi()["paths"]

        self.assertIn("/api/media-workbenches", paths)
        self.assertIn("/api/media-workbenches/{slug}/configuration", paths)
        self.assertIn("/api/media-workbenches/{slug}/runs", paths)
        self.assertEqual(
            paths["/api/media-workbenches/{slug}/runs"]["post"]["summary"],
            "从专注工作台创建媒体任务",
        )

    def test_real_runninghub_workbench_reports_missing_platform_workflow_id(self):
        version = SimpleNamespace(status="published", template_id=uuid4())
        template = SimpleNamespace(external_workflow_id="")
        db = SimpleNamespace(
            get=lambda model, _record_id: version if model.__name__ == "WorkflowTemplateVersion" else template
        )
        record = SimpleNamespace(
            slug="audio-clone",
            enabled=True,
            workflow_version_id=uuid4(),
            input_config={
                "prompt": {"label": "合成文本", "target_parameter_key": "2.value"},
                "primary_asset": {"label": "参考音色", "target_parameter_key": "1.audio"},
            },
        )

        issues = validate_workbench_configuration(
            db,
            record,
            grsai_configured=True,
            runninghub_configured=True,
            mock_mode=False,
        )

        self.assertIn("所选工作流尚未配置 RunningHub workflowId", issues)

    def test_runninghub_audio_workbench_rejects_unsupported_upload_extension(self):
        with self.assertRaises(HTTPException) as context:
            _validate_runninghub_audio_asset(SimpleNamespace(original_file_name="reference.m4a"), "参考音色")

        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("MP3、WAV 或 FLAC", context.exception.detail)


class _FakeMigrationResult:
    def __init__(self, values=()):
        self.values = values

    def scalars(self):
        return self.values


class _FakeMigrationConnection:
    def __init__(self, applied: set[str], executed: list[str]):
        self.applied = applied
        self.executed = executed

    def execute(self, statement, parameters=None):
        sql = str(statement)
        self.executed.append(sql)
        if "SELECT version FROM app_schema_migrations" in sql:
            return _FakeMigrationResult(tuple(self.applied))
        if "INSERT INTO app_schema_migrations" in sql and parameters:
            self.applied.add(parameters["version"])
        return _FakeMigrationResult()


class _FakeMigrationEngine:
    def __init__(self):
        self.applied: set[str] = set()
        self.executed: list[str] = []

    @contextmanager
    def begin(self):
        yield _FakeMigrationConnection(self.applied, self.executed)


class SchemaMigrationTests(unittest.TestCase):
    """确保开发期增量迁移可重复执行，避免旧 Docker 数据卷再次触发缺列错误。"""

    def test_workbench_slug_migration_runs_once_and_is_recorded(self):
        engine = _FakeMigrationEngine()

        run_schema_migrations(engine)
        first_run_sql = "\n".join(engine.executed)
        self.assertIn("ADD COLUMN IF NOT EXISTS workbench_slug", first_run_sql)
        self.assertIn("20260720_01_media_generation_workbench_slug", engine.applied)

        engine.executed.clear()
        run_schema_migrations(engine)
        second_run_sql = "\n".join(engine.executed)
        self.assertNotIn("ADD COLUMN IF NOT EXISTS workbench_slug", second_run_sql)


if __name__ == "__main__":
    unittest.main()
