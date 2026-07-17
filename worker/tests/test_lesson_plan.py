import unittest
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.config import WorkerSettings
from app.llm_client import LLMClient
from app.schemas import LessonPlanVariantContent


def source_content() -> dict:
    """返回四种变体共同使用的原教案确认稿快照。"""

    return {
        "title": "客家山歌律动教案",
        "course_overview": "面向 8-12 岁学生的四十分钟课程。",
        "teaching_goals": ["理解客家山歌节奏", "完成基础动作组合"],
        "key_points": ["节拍稳定"],
        "common_mistakes": ["抢拍"],
        "warmup": [{"name": "节奏热身", "duration_minutes": 5, "description": "拍手踏步。"}],
        "main_teaching": [{"name": "组合学习", "duration_minutes": 25, "description": "分句练习。"}],
        "movement_breakdown": [{"name": "山歌引手", "beats": "八拍", "teaching_tips": "肩膀放松。"}],
        "cooldown": [{"name": "呼吸放松", "duration_minutes": 5, "description": "伸展放松。"}],
        "homework": ["复习八拍组合"],
        "teacher_notes": ["老师课前确认动作安全"],
    }


class LessonPlanVariantWorkerTests(unittest.TestCase):
    """验证 T02 离线生成、严格 Schema、Prompt 边界和任务分发。"""

    def _client(self) -> LLMClient:
        return LLMClient(
            WorkerSettings(
                llm_mock_mode=True,
                llm_default_provider="deepseek",
                llm_default_model="deepseek-v4-flash",
                llm_default_reasoning_level="standard",
            )
        )

    def _snapshot(self, variant_type: str) -> dict:
        return {
            "source_lesson_plan_id": str(uuid4()),
            "source_title": "客家山歌律动教案",
            "source_content": source_content(),
            "course": {"age_group": "8-12 岁", "duration_minutes": 40, "learning_level": "零基础"},
            "variant_type": variant_type,
            "adjustment_direction": "课堂中增加小组互相观察",
            "llm_provider": "deepseek",
            "llm_model": "deepseek-v4-flash",
            "reasoning_level": "standard",
        }

    def test_four_mock_presets_produce_distinct_and_complete_variants(self):
        titles: set[str] = set()
        audiences: set[str] = set()
        key_points: set[tuple[str, ...]] = set()

        for variant_type in ["younger", "basic", "advanced", "performance"]:
            content, model_info = self._client().generate_lesson_plan_variant(self._snapshot(variant_type))
            titles.add(content["title"])
            audiences.add(content["applicable_audience"])
            key_points.add(tuple(content["key_points"]))
            self.assertGreaterEqual(len(content["adjustment_summary"]), 2)
            self.assertTrue(content["common_mistakes"])
            self.assertIn("小组互相观察", " ".join(content["adjustment_summary"]))
            self.assertEqual(model_info["prompt_version"], "lesson_plan_variant_v1")

        self.assertEqual(len(titles), 4)
        self.assertEqual(len(audiences), 4)
        self.assertEqual(len(key_points), 4)

    def test_variant_schema_rejects_missing_audience_or_empty_summary(self):
        content, _ = self._client().generate_lesson_plan_variant(self._snapshot("younger"))
        content["adjustment_summary"] = []
        with self.assertRaises(ValidationError):
            LessonPlanVariantContent.model_validate(content)

        content, _ = self._client().generate_lesson_plan_variant(self._snapshot("younger"))
        content["applicable_audience"] = "   "
        with self.assertRaises(ValidationError):
            LessonPlanVariantContent.model_validate(content)

    def test_prompt_declares_presets_and_text_only_boundary(self):
        prompt_path = Path(__file__).resolve().parents[1] / "app" / "prompts" / "lesson_plan_variant_v1.md"
        prompt = prompt_path.read_text(encoding="utf-8")

        for marker in ["younger（低龄版）", "basic（基础版）", "advanced（进阶版）", "performance（演出版）"]:
            self.assertIn(marker, prompt)
        for boundary in ["不自动生成专业编舞动作", "音频", "曲谱", "视频分析"]:
            self.assertIn(boundary, prompt)

    def test_dispatch_routes_variant_task_on_lesson_plan_queue(self):
        from app import main as worker_main

        self.assertIn("ai:lesson_plan", worker_main.AI_QUEUES)
        calls: list[dict] = []
        original = worker_main._process_lesson_plan_variant_task
        try:
            worker_main._process_lesson_plan_variant_task = lambda payload, _client: calls.append(payload)
            payload = {"task_type": "lesson_plan.variant.generate"}
            worker_main._dispatch_task(payload, object())
        finally:
            worker_main._process_lesson_plan_variant_task = original
        self.assertEqual(calls, [{"task_type": "lesson_plan.variant.generate"}])

    def test_unknown_variant_type_fails_before_model_call(self):
        with self.assertRaisesRegex(RuntimeError, "不支持的教案变体类型"):
            self._client().generate_lesson_plan_variant(self._snapshot("custom"))


if __name__ == "__main__":
    unittest.main()
