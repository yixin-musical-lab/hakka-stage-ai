import importlib
import unittest
from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError


class ClassInteractionSchemaTests(unittest.TestCase):
    """验证 T05 课堂互动输入与输出的核心业务约束。"""

    def _load_schema_module(self):
        """把缺失模块转换为断言失败，确保 RED 阶段原因清晰可读。"""

        try:
            return importlib.import_module("app.schemas.class_interaction")
        except ModuleNotFoundError:
            self.fail("课堂互动 schema 尚未实现")

    def test_content_requires_teacher_student_and_safety_fields(self):
        """生成结果必须同时包含老师口令、学生动作和安全提醒。"""

        schemas = self._load_schema_module()
        valid_content = {
            "title": "山歌节奏接龙",
            "teaching_phase": "热身",
            "interaction_goal": "建立四拍节奏感",
            "duration_minutes": 8,
            "space_materials": "清空教室中间区域，无需额外材料",
            "game_rules": ["老师示范一组四拍动作，学生依次接龙。"],
            "teacher_script": [
                {
                    "step_no": 1,
                    "name": "示范节奏",
                    "duration_hint": "2分钟",
                    "teacher_action": "面向学生示范拍手和踏步。",
                    "teacher_cue": "看我一次，然后一起接上！",
                    "student_action": "观察后同步完成四拍动作。",
                }
            ],
            "command_phrases": ["预备，四拍开始！"],
            "student_actions": ["跟随口令完成拍手和踏步。"],
            "grouping_method": "全班围成半圆，不额外分组。",
            "encouragement_phrases": ["这一组节奏接得很稳！"],
            "safety_notes": ["学生之间保持一臂距离。"],
            "variations": ["空间不足时改为原地拍手。"],
            "teacher_check_notes": ["开始前确认地面无障碍物。"],
        }

        content = schemas.ClassInteractionContent.model_validate(valid_content)
        self.assertEqual(content.teacher_script[0].teacher_cue, "看我一次，然后一起接上！")

        invalid_content = dict(valid_content)
        invalid_content["safety_notes"] = []
        with self.assertRaises(ValidationError):
            schemas.ClassInteractionContent.model_validate(invalid_content)

        empty_rule_content = dict(valid_content)
        empty_rule_content["game_rules"] = [""]
        with self.assertRaises(ValidationError):
            schemas.ClassInteractionContent.model_validate(empty_rule_content)


class ClassInteractionServiceTests(unittest.TestCase):
    """验证导出和教案联动等不依赖数据库的服务行为。"""

    def _load_service_module(self):
        """把缺失服务转换为清晰的断言失败。"""

        try:
            return importlib.import_module("app.services.class_interaction_service")
        except ModuleNotFoundError:
            self.fail("课堂互动 service 尚未实现")

    def test_markdown_contains_live_execution_sections(self):
        """Markdown 必须覆盖老师现场执行最需要的关键内容。"""

        service = self._load_service_module()
        record = SimpleNamespace(
            title="山歌节奏接龙",
            course_theme="客家山歌节奏",
            age_group="9-12 岁",
            teaching_phase="热身",
            interaction_goal="建立四拍节奏感",
            class_style="活泼",
            duration_minutes=8,
            student_count=24,
            space_materials="清空教室中间区域",
            content=None,
            edited_content={
                "title": "山歌节奏接龙",
                "teaching_phase": "热身",
                "interaction_goal": "建立四拍节奏感",
                "duration_minutes": 8,
                "space_materials": "清空教室中间区域",
                "game_rules": ["老师示范四拍动作，学生依次接龙。"],
                "teacher_script": [
                    {
                        "step_no": 1,
                        "name": "示范节奏",
                        "duration_hint": "2分钟",
                        "teacher_action": "示范拍手和踏步。",
                        "teacher_cue": "看我一次，然后一起接上！",
                        "student_action": "观察后完成四拍动作。",
                    }
                ],
                "command_phrases": ["预备，四拍开始！"],
                "student_actions": ["跟随口令完成拍手和踏步。"],
                "grouping_method": "全班围成半圆。",
                "encouragement_phrases": ["这一组节奏接得很稳！"],
                "safety_notes": ["学生之间保持一臂距离。"],
                "variations": ["空间不足时改为原地拍手。"],
                "teacher_check_notes": ["开始前确认地面无障碍物。"],
            },
            raw_model_info={"provider": "deepseek", "model": "deepseek-chat", "generated_at": "2026-07-10"},
        )

        markdown = service.render_class_interaction_markdown(record)

        self.assertIn("## 老师逐步执行脚本", markdown)
        self.assertIn("看我一次，然后一起接上！", markdown)
        self.assertIn("## 学生动作与回应", markdown)
        self.assertIn("## 安全提醒", markdown)
        self.assertIn("## 变式与备用方案", markdown)

    def test_lesson_prefill_uses_edited_lesson_context(self):
        """关联教案时优先把老师编辑稿作为生成上下文快照。"""

        service = self._load_service_module()
        lesson_plan_id = uuid4()
        course = SimpleNamespace(
            theme="客家山歌中的劳动节奏",
            age_group="9-12 岁",
            student_count=28,
            course_style="活泼、协作",
            teaching_goal="感受劳动节奏并完成四拍组合",
            notes="教室后排空间较窄，不使用道具",
        )
        lesson_plan = SimpleNamespace(
            id=lesson_plan_id,
            content={"teaching_goals": ["AI 初稿目标"]},
            edited_content={
                "teaching_goals": ["老师确认目标：稳定完成四拍组合"],
                "key_points": ["听清重拍"],
                "teacher_notes": ["避免快速转圈"],
            },
        )

        prefill = service.build_lesson_interaction_prefill(course, lesson_plan)

        self.assertEqual(prefill.source_lesson_plan_id, lesson_plan_id)
        self.assertEqual(prefill.class_style, "活泼、协作")
        self.assertIn("老师确认目标：稳定完成四拍组合", prefill.lesson_context)
        self.assertNotIn("AI 初稿目标", prefill.lesson_context)
        self.assertIn("不使用道具", prefill.space_materials)


class ClassInteractionOpenApiTests(unittest.TestCase):
    """确保课堂互动接口在 OpenAPI 中完整、可发现。"""

    def test_openapi_exposes_generation_edit_export_and_prefill(self):
        """T05 首版所需接口必须全部注册到 FastAPI 应用。"""

        from app.main import app

        paths = app.openapi()["paths"]
        expected_methods = {
            "/api/interactions/generate": "post",
            "/api/interactions": "get",
            "/api/interactions/prefill-from-lesson/{lesson_plan_id}": "get",
            "/api/interactions/{class_interaction_id}": "get",
            "/api/interactions/{class_interaction_id}/markdown": "get",
        }
        for path, method in expected_methods.items():
            self.assertIn(path, paths)
            self.assertIn(method, paths[path])

        self.assertIn("put", paths["/api/interactions/{class_interaction_id}"])
        self.assertIn("delete", paths["/api/interactions/{class_interaction_id}"])


if __name__ == "__main__":
    unittest.main()
