import unittest
from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.musical import MusicalFusionContent, MusicalFusionGenerateRequest
from app.services.musical_service import render_musical_fusion_markdown


def valid_content() -> dict:
    """返回覆盖 M04 验收字段的最小合法结构。"""

    return {
        "title": "第二幕歌舞融合建议",
        "related_scene": "第二幕：一起排练",
        "fusion_goal": "从主角领唱推进到全员齐唱群舞高潮",
        "stage_space": "普通教室或小舞台",
        "actor_count": 12,
        "overall_design": "前奏铺垫、主歌推进、副歌高潮。",
        "segments": [
            {
                "segment_no": "A1",
                "story_content": "旁白介绍山歌来源。",
                "music_position": "前奏",
                "singing_mode": "旁白衔接",
                "singing_roles": ["旁白"],
                "dance_form": "轻律动",
                "formation_suggestion": "半圆分散",
                "emotion": "温柔",
                "song_dance_relationship": "动作只做氛围铺垫。",
                "transition_note": "主角进入中心。",
                "rehearsal_tip": "先排路线再合音乐。",
                "safety_note": "保持一臂距离。",
                "is_highlight": False,
            },
            {
                "segment_no": "B1",
                "story_content": "全体齐唱完成剧情高潮。",
                "music_position": "副歌",
                "singing_mode": "全员齐唱",
                "singing_roles": ["全体"],
                "dance_form": "八拍群舞",
                "formation_suggestion": "两排展开为宽半圆",
                "emotion": "热烈",
                "song_dance_relationship": "齐唱和队形展开同步增强。",
                "transition_note": "定格后进入间奏。",
                "rehearsal_tip": "慢速练队形后再按原速合排。",
                "safety_note": "展开时不得后退交叉。",
                "is_highlight": True,
            },
        ],
        "highlight_summary": "B1 是齐唱和群舞高潮。",
        "rehearsal_notes": ["先分段后连接。"],
        "director_review_notes": ["编导确认实际场地和动作难度。"],
    }


class MusicalFusionSchemaTests(unittest.TestCase):
    """验证 M04 输入来源互斥和结构化输出约束。"""

    def test_manual_source_requires_music_structure(self):
        with self.assertRaises(ValidationError):
            MusicalFusionGenerateRequest(
                script_id=uuid4(),
                source_mode="manual",
                related_scene="第二幕",
                actor_count=12,
                stage_space="教室",
                fusion_goal="形成唱跳高潮",
            )

    def test_song_adaptation_source_rejects_manual_fields(self):
        with self.assertRaises(ValidationError):
            MusicalFusionGenerateRequest(
                script_id=uuid4(),
                source_mode="song_adaptation",
                song_adaptation_id=uuid4(),
                related_scene="第二幕",
                manual_music_structure="副歌",
                actor_count=12,
                stage_space="教室",
                fusion_goal="形成唱跳高潮",
            )

    def test_content_requires_highlight_segment(self):
        content = valid_content()
        for segment in content["segments"]:
            segment["is_highlight"] = False
        with self.assertRaises(ValidationError):
            MusicalFusionContent.model_validate(content)


class MusicalFusionServiceTests(unittest.TestCase):
    """验证 M04 Markdown 导出覆盖编导需要的结构。"""

    def test_markdown_contains_structure_highlight_and_safety(self):
        record = SimpleNamespace(
            title="第二幕歌舞融合建议",
            music_title="客家山歌",
            related_scene="第二幕：一起排练",
            actor_count=12,
            stage_space="普通教室",
            fusion_goal="形成齐唱群舞高潮",
            content=None,
            edited_content=valid_content(),
            raw_model_info={"provider": "deepseek", "model": "deepseek-v4-flash", "generated_at": "2026-07-11"},
        )

        markdown = render_musical_fusion_markdown(record)

        self.assertIn("## 歌舞融合结构表", markdown)
        self.assertIn("高潮", markdown)
        self.assertIn("保持一臂距离", markdown)
        self.assertIn("## 编导复核提醒", markdown)


class MusicalFusionOpenApiTests(unittest.TestCase):
    """确保 M04 所需接口在 OpenAPI 中可发现。"""

    def test_openapi_exposes_full_resource_flow(self):
        from app.main import app

        paths = app.openapi()["paths"]
        self.assertIn("post", paths["/api/musical-fusion-plans/generate"])
        self.assertIn("get", paths["/api/musical-fusion-plans"])
        detail_path = paths["/api/musical-fusion-plans/{musical_fusion_plan_id}"]
        for method in ["get", "put", "delete"]:
            self.assertIn(method, detail_path)
        self.assertIn("get", paths["/api/musical-fusion-plans/{musical_fusion_plan_id}/markdown"])


if __name__ == "__main__":
    unittest.main()
