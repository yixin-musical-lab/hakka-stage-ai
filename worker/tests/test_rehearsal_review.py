import unittest
from pathlib import Path
from uuid import uuid4

from app.config import WorkerSettings
from app.llm_client import LLMClient
from app.schemas import RehearsalReviewContent


class RehearsalReviewWorkerTests(unittest.TestCase):
    """验证 M08 mock、Schema、Prompt 边界和 Worker 分发。"""

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
            "fusion_plan_id": str(uuid4()),
            "role_training_plan_id": str(uuid4()),
            "project_title": "客家山歌小剧场",
            "script_title": "山歌里的家乡",
            "event_type": "rehearsal",
            "event_date": "2026-07-12",
            "rehearsal_content": "完成第二幕和副歌连接",
            "observation_notes": "副歌队形略散，主角台词稳定。",
            "strengths": "主角台词稳定。",
            "issues": "群演进入间奏偏慢。",
            "review_focus": ["唱段与节奏", "舞蹈与队形"],
            "next_goal": "稳定队形和间奏进入。",
            "has_video_attachment": True,
            "video_notes": "老师上传了第二幕片段，仅供人工回看。",
            "script_content": {"characters": [{"name": "阿月"}]},
            "fusion_plan_title": "第二幕歌舞融合",
            "fusion_content": {"highlight_summary": "副歌齐唱群舞高潮"},
            "role_training_plan_title": "分角色训练计划",
            "role_training_content": {"role_tasks": [{"role_name": "阿月"}]},
            "llm_provider": "deepseek",
            "llm_model": "deepseek-v4-flash",
            "reasoning_level": "standard",
        }

    def test_mock_generation_uses_upstream_context_and_boundary(self):
        content, model_info = self._client().generate_rehearsal_review(self._snapshot())
        validated = RehearsalReviewContent.model_validate(content)

        self.assertGreaterEqual(len(validated.issues), 1)
        self.assertGreaterEqual(len(validated.reusable_template.observation_prompts), 1)
        self.assertIn("M04", validated.overview)
        self.assertIn("M05", validated.overview)
        self.assertIn("AI 未分析视频", validated.boundary_note)
        self.assertEqual(model_info["prompt_version"], "rehearsal_review_v1")

    def test_prompt_forbids_video_analysis_and_private_keys(self):
        prompt_path = Path(__file__).resolve().parents[1] / "app" / "prompts" / "rehearsal_review_v1.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        for boundary in ["绝对不要声称看过", "不做姿态识别", "AI 未分析视频"]:
            self.assertIn(boundary, prompt)
        self.assertNotIn("video_object_key", prompt)
        self.assertNotIn("video_url", prompt)

    def test_dispatch_routes_rehearsal_review_task(self):
        from app import main as worker_main

        self.assertIn("ai:rehearsal_review", worker_main.AI_QUEUES)
        calls: list[dict] = []
        original = worker_main._process_rehearsal_review_task
        try:
            worker_main._process_rehearsal_review_task = lambda payload, _client: calls.append(payload)
            payload = {"task_type": "rehearsal_review.generate"}
            worker_main._dispatch_task(payload, object())
        finally:
            worker_main._process_rehearsal_review_task = original
        self.assertEqual(calls, [{"task_type": "rehearsal_review.generate"}])


if __name__ == "__main__":
    unittest.main()
