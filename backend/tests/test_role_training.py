import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.routes.musical import export_role_training_card_markdown
from app.services.musical_service import render_role_training_card_markdown, render_role_training_markdown


def valid_content(title: str = "山歌里的家乡 · 分角色训练计划") -> dict:
    """返回同时覆盖两个角色和共通检查点的 M05 最小正文。"""

    return {
        "title": title,
        "project_overview": "三天完成台词、演唱、舞蹈和走位合排。",
        "role_tasks": [
            {
                "role_name": "阿月",
                "role_type": "主角",
                "line_focus": "确认稿阿月台词重点",
                "singing_focus": "确认稿阿月演唱重点",
                "dance_focus": "确认稿阿月舞蹈重点",
                "blocking_tips": "确认稿阿月走位提醒",
                "daily_tasks": ["阿月第一天任务", "阿月第二天任务"],
                "teacher_checkpoints": ["阿月角色检查点"],
            },
            {
                "role_name": "奶奶",
                "role_type": "配角",
                "line_focus": "奶奶台词重点",
                "singing_focus": "奶奶演唱重点",
                "dance_focus": "奶奶舞蹈重点",
                "blocking_tips": "奶奶走位提醒",
                "daily_tasks": ["奶奶第一天任务"],
                "teacher_checkpoints": ["奶奶角色检查点"],
            },
        ],
        "daily_plan": [
            {
                "day": "第 1 天",
                "focus": "读本",
                "tasks": ["全体读本"],
                "expected_result": "明确角色任务",
            }
        ],
        "teacher_checkpoints": ["共通老师提醒：先慢速走位再合音乐"],
    }


def role_training_record(*, content: dict | None = None, edited_content: dict | None = None) -> SimpleNamespace:
    """构造无需数据库连接的训练计划记录。"""

    return SimpleNamespace(
        title="原始计划标题",
        content=content,
        edited_content=edited_content,
        raw_model_info={"provider": "deepseek", "model": "deepseek-v4-flash", "generated_at": "2026-07-15"},
    )


class RoleTrainingMarkdownTests(unittest.TestCase):
    """验证 M05 单角色导出隔离和整份导出的兼容行为。"""

    def test_role_card_prefers_edited_content_and_only_contains_selected_role(self):
        ai_draft = valid_content("AI 初稿")
        ai_draft["role_tasks"][0]["line_focus"] = "AI 初稿台词"
        record = role_training_record(content=ai_draft, edited_content=valid_content("老师确认稿"))

        markdown = render_role_training_card_markdown(record, 0)

        self.assertIsNotNone(markdown)
        assert markdown is not None
        self.assertIn("老师确认稿 · 阿月训练卡", markdown)
        self.assertIn("确认稿阿月台词重点", markdown)
        self.assertIn("共通老师提醒：先慢速走位再合音乐", markdown)
        self.assertNotIn("AI 初稿台词", markdown)
        self.assertNotIn("奶奶", markdown)

    def test_role_card_returns_none_for_empty_body(self):
        self.assertIsNone(render_role_training_card_markdown(role_training_record(), 0))

    def test_role_card_rejects_out_of_range_index(self):
        record = role_training_record(content=valid_content())
        for role_index in [-1, 2]:
            with self.subTest(role_index=role_index), self.assertRaises(IndexError):
                render_role_training_card_markdown(record, role_index)

    def test_full_plan_export_still_contains_every_role(self):
        markdown = render_role_training_markdown(role_training_record(content=valid_content()))

        self.assertIsNotNone(markdown)
        assert markdown is not None
        self.assertIn("### 阿月（主角）", markdown)
        self.assertIn("### 奶奶（配角）", markdown)
        self.assertIn("## 每日排练安排", markdown)


class RoleTrainingRouteTests(unittest.TestCase):
    """验证单角色接口的业务错误映射和 OpenAPI 可发现性。"""

    def test_route_maps_missing_plan_to_404(self):
        db = SimpleNamespace(get=lambda *_args: None)

        with self.assertRaises(HTTPException) as context:
            export_role_training_card_markdown(SimpleNamespace(), 0, db)

        self.assertEqual(context.exception.status_code, 404)

    def test_route_maps_empty_body_to_409(self):
        db = SimpleNamespace(get=lambda *_args: role_training_record())

        with self.assertRaises(HTTPException) as context:
            export_role_training_card_markdown(SimpleNamespace(), 0, db)

        self.assertEqual(context.exception.status_code, 409)

    def test_route_maps_out_of_range_index_to_404(self):
        db = SimpleNamespace(get=lambda *_args: role_training_record(content=valid_content()))

        with self.assertRaises(HTTPException) as context:
            export_role_training_card_markdown(SimpleNamespace(), 3, db)

        self.assertEqual(context.exception.status_code, 404)

    def test_openapi_exposes_role_card_and_keeps_full_plan_path(self):
        from app.main import app

        paths = app.openapi()["paths"]
        full_path = "/api/role-training-plans/{role_training_plan_id}/markdown"
        role_path = "/api/role-training-plans/{role_training_plan_id}/roles/{role_index}/markdown"
        self.assertIn("get", paths[full_path])
        self.assertIn("get", paths[role_path])

        role_parameters = paths[role_path]["get"]["parameters"]
        role_index = next(parameter for parameter in role_parameters if parameter["name"] == "role_index")
        self.assertEqual(role_index["schema"]["minimum"], 0)


if __name__ == "__main__":
    unittest.main()
