import unittest
from uuid import uuid4

from app.config import WorkerSettings
from app.llm_client import LLMClient
from app.schemas import RoleTrainingContent


class RoleTrainingWorkerTests(unittest.TestCase):
    """验证 M05 Mock 多角色训练结果和 M04 上下文继承。"""

    def _client(self) -> LLMClient:
        return LLMClient(
            WorkerSettings(
                llm_mock_mode=True,
                llm_default_provider="deepseek",
                llm_default_model="deepseek-v4-flash",
                llm_default_reasoning_level="standard",
            )
        )

    def _snapshot(self) -> dict:
        return {
            "script_id": str(uuid4()),
            "script_title": "山歌里的家乡",
            "script_content": {"characters": [{"name": "阿月"}, {"name": "奶奶"}]},
            "rehearsal_days": 3,
            "session_minutes": 60,
            "training_focus": "唱段、队形和高潮段落",
            "fusion_plan_id": str(uuid4()),
            "fusion_plan_title": "第二幕歌舞融合建议",
            "fusion_content": {
                "title": "第二幕歌舞融合建议",
                "highlight_summary": "副歌齐唱时完成全员群舞高潮。",
            },
            "llm_provider": "deepseek",
            "llm_model": "deepseek-v4-flash",
            "reasoning_level": "standard",
        }

    def test_mock_returns_distinct_roles_with_required_training_fields(self):
        content, model_info = self._client().generate_role_training(self._snapshot())

        # Pydantic 复核能提前发现 Worker 输出缺少 M05 必填结构。
        RoleTrainingContent.model_validate(content)
        self.assertGreaterEqual(len(content["role_tasks"]), 2)
        self.assertEqual(len({item["role_name"] for item in content["role_tasks"]}), len(content["role_tasks"]))

        required_text_fields = [
            "role_name",
            "role_type",
            "line_focus",
            "singing_focus",
            "dance_focus",
            "blocking_tips",
        ]
        for role_task in content["role_tasks"]:
            for field in required_text_fields:
                self.assertTrue(role_task[field], f"{role_task['role_name']} 缺少 {field}")
            self.assertTrue(role_task["daily_tasks"])
            self.assertTrue(role_task["teacher_checkpoints"])

        self.assertTrue(model_info["mock"])
        self.assertEqual(model_info["prompt_version"], "role_training_v1")

    def test_mock_inherits_m04_highlight_context(self):
        content, _ = self._client().generate_role_training(self._snapshot())

        self.assertIn("已引用歌舞融合方案", content["project_overview"])
        self.assertIn("副歌齐唱", content["project_overview"])


if __name__ == "__main__":
    unittest.main()
