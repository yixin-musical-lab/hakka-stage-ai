import unittest
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from app.config import WorkerSettings
from app.llm_client import LLMClient
from app.schemas import MusicalFusionContent


class MusicalFusionWorkerTests(unittest.TestCase):
    """验证 M04 离线生成、Schema 和 Worker 分发。"""

    def _client(self) -> LLMClient:
        return LLMClient(
            WorkerSettings(
                llm_mock_mode=True,
                llm_default_provider="deepseek",
                llm_default_model="deepseek-v4-flash",
                llm_default_reasoning_level="standard",
            )
        )

    def _snapshot(self, source_mode: str = "song_adaptation") -> dict:
        return {
            "script_id": str(uuid4()),
            "source_mode": source_mode,
            "song_adaptation_id": str(uuid4()) if source_mode == "song_adaptation" else None,
            "related_scene": "第二幕：一起排练",
            "actor_count": 12,
            "stage_space": "普通教室或小舞台",
            "fusion_goal": "从主角领唱推进到全员齐唱群舞高潮",
            "additional_constraints": "避免快速转圈和交叉奔跑",
            "script_title": "客家山歌小剧场",
            "script_content": {"acts": [{"name": "第二幕"}]},
            "music_title": "客家山歌",
            "source_music_structure": "前奏、主歌、副歌、间奏",
            "source_lyrics_summary": "大家一起唱响家乡山歌",
            "song_adaptation_content": {"sections": []} if source_mode == "song_adaptation" else None,
            "llm_provider": "deepseek",
            "llm_model": "deepseek-v4-flash",
            "reasoning_level": "standard",
        }

    def test_mock_generation_supports_m03_and_manual_sources(self):
        for source_mode in ["song_adaptation", "manual"]:
            content, model_info = self._client().generate_musical_fusion(self._snapshot(source_mode))
            self.assertGreaterEqual(len(content["segments"]), 2)
            self.assertTrue(any(segment["is_highlight"] for segment in content["segments"]))
            self.assertTrue(all(segment["safety_note"] for segment in content["segments"]))
            self.assertEqual(model_info["prompt_version"], "musical_fusion_v1")

    def test_schema_rejects_result_without_highlight(self):
        content, _ = self._client().generate_musical_fusion(self._snapshot())
        for segment in content["segments"]:
            segment["is_highlight"] = False
        with self.assertRaises(ValidationError):
            MusicalFusionContent.model_validate(content)

    def test_role_training_mock_reads_musical_fusion_context(self):
        """M05 Mock 必须显式反映已带入的 M04 高潮和排练上下文。"""

        snapshot = self._snapshot()
        snapshot.update(
            {
                "rehearsal_days": 3,
                "session_minutes": 60,
                "training_focus": "唱段、队形和高潮段落",
                "fusion_plan_title": "第二幕歌舞融合建议",
                "fusion_content": {
                    "title": "第二幕歌舞融合建议",
                    "highlight_summary": "副歌齐唱时完成全员群舞高潮。",
                },
            }
        )
        content, _ = self._client().generate_role_training(snapshot)

        self.assertIn("已引用歌舞融合方案", content["project_overview"])
        self.assertIn("副歌齐唱", content["project_overview"])

    def test_prompt_keeps_text_only_boundary(self):
        prompt_path = Path(__file__).resolve().parents[1] / "app" / "prompts" / "musical_fusion_v1.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        for boundary in ["不自动生成专业编舞动作", "音频节拍识别", "曲谱解析", "视频分析"]:
            self.assertIn(boundary, prompt)
        self.assertIn("至少一个 segments[].is_highlight 必须为 true", prompt)

    def test_dispatch_routes_musical_fusion_task(self):
        from app import main as worker_main

        self.assertIn("ai:musical_fusion", worker_main.AI_QUEUES)
        calls: list[dict] = []
        original = worker_main._process_musical_fusion_task
        try:
            worker_main._process_musical_fusion_task = lambda payload, _client: calls.append(payload)
            payload = {"task_type": "musical_fusion.generate"}
            worker_main._dispatch_task(payload, object())
        finally:
            worker_main._process_musical_fusion_task = original
        self.assertEqual(calls, [{"task_type": "musical_fusion.generate"}])


if __name__ == "__main__":
    unittest.main()
