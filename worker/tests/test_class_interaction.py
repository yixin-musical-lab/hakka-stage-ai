import unittest
from pathlib import Path

from pydantic import ValidationError

from app.config import WorkerSettings
from app.llm_client import LLMClient


class ClassInteractionWorkerTests(unittest.TestCase):
    """验证 Worker 的 T05 结构化生成和范围边界。"""

    def _client(self) -> LLMClient:
        """构造完全离线的 Mock 客户端，测试不会请求真实模型。"""

        return LLMClient(
            WorkerSettings(
                llm_mock_mode=True,
                llm_default_provider="deepseek",
                llm_default_model="deepseek-v4-flash",
                llm_default_reasoning_level="standard",
            )
        )

    def _input_snapshot(self) -> dict:
        """返回一份覆盖 T05 核心输入字段的任务快照。"""

        return {
            "course_theme": "客家山歌节奏",
            "age_group": "9-12 岁",
            "teaching_phase": "热身",
            "interaction_goal": "建立四拍节奏并鼓励学生协作",
            "class_style": "活泼、协作",
            "duration_minutes": 8,
            "student_count": 24,
            "space_materials": "清空教室中间区域，不使用道具；学生之间保持一臂距离。",
            "lesson_context": "本课重点：听清重拍；老师备注：避免快速转圈",
            "llm_provider": "deepseek",
            "llm_model": "deepseek-v4-flash",
            "reasoning_level": "standard",
        }

    def test_mock_generation_returns_executable_teacher_plan(self):
        """Mock 输出必须同时提供教师步骤、学生动作、安全和备用方案。"""

        client = self._client()
        self.assertTrue(hasattr(client, "generate_class_interaction"), "课堂互动生成方法尚未实现")

        content, model_info = client.generate_class_interaction(self._input_snapshot())

        self.assertGreaterEqual(len(content["teacher_script"]), 1)
        self.assertTrue(content["teacher_script"][0]["teacher_cue"])
        self.assertGreaterEqual(len(content["student_actions"]), 1)
        self.assertGreaterEqual(len(content["safety_notes"]), 1)
        self.assertGreaterEqual(len(content["variations"]), 1)
        self.assertEqual(content["space_materials"].count("保持一臂距离"), 1)
        self.assertEqual(model_info["prompt_version"], "class_interaction_v1")

    def test_schema_rejects_empty_safety_notes(self):
        """Worker 侧 schema 必须阻止缺少安全提醒的模型输出入库。"""

        try:
            from app.schemas import ClassInteractionContent
        except ImportError:
            self.fail("Worker 课堂互动 schema 尚未实现")

        content, _ = self._client().generate_class_interaction(self._input_snapshot())
        content["safety_notes"] = []
        with self.assertRaises(ValidationError):
            ClassInteractionContent.model_validate(content)

        content, _ = self._client().generate_class_interaction(self._input_snapshot())
        content["game_rules"] = ["   "]
        with self.assertRaises(ValidationError):
            ClassInteractionContent.model_validate(content)

    def test_prompt_keeps_text_only_boundary(self):
        """提示词必须明确排除可运行网页游戏和多媒体设备控制。"""

        prompt_path = Path(__file__).resolve().parents[1] / "app" / "prompts" / "class_interaction_v1.md"
        self.assertTrue(prompt_path.exists(), "课堂互动提示词尚未实现")
        prompt = prompt_path.read_text(encoding="utf-8")
        for boundary in ["Web 游戏", "2D/3D", "TTS", "设备控制"]:
            self.assertIn(boundary, prompt)
        self.assertIn('"teaching_phase": "热身"', prompt)
        self.assertNotIn('"teaching_phase": "开场/热身/动作学习/分组展示/收束"', prompt)

    def test_dispatch_routes_class_interaction_task(self):
        """Worker 主循环必须识别课堂互动任务类型和独立队列。"""

        from app import main as worker_main

        self.assertIn("ai:class_interaction", worker_main.AI_QUEUES)
        self.assertTrue(
            hasattr(worker_main, "_process_class_interaction_task"),
            "课堂互动任务处理函数尚未实现",
        )
        calls: list[dict] = []
        original = worker_main._process_class_interaction_task
        try:
            worker_main._process_class_interaction_task = lambda payload, _client: calls.append(payload)
            payload = {"task_type": "class_interaction.generate"}
            worker_main._dispatch_task(payload, object())
        finally:
            worker_main._process_class_interaction_task = original
        self.assertEqual(calls, [{"task_type": "class_interaction.generate"}])


if __name__ == "__main__":
    unittest.main()
