import unittest
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from pydantic import ValidationError

from app.models import LessonPlanVariant
from app.schemas import LessonPlanContent, LessonPlanVariantGenerateRequest
from app.services.class_interaction_service import build_lesson_interaction_prefill
from app.services.lesson_plan_service import lesson_plan_response, render_lesson_plan_markdown


def valid_lesson_content() -> dict:
    """返回一份可被 T01/T02 共用的最小完整教案。"""

    return {
        "title": "客家山歌律动教案",
        "course_overview": "面向 8-12 岁学生的四十分钟课程。",
        "teaching_goals": ["掌握基础律动"],
        "key_points": ["节拍稳定"],
        "common_mistakes": ["抢拍"],
        "warmup": [{"name": "节奏热身", "duration_minutes": 5, "description": "拍手踏步。"}],
        "main_teaching": [{"name": "动作学习", "duration_minutes": 25, "description": "分句练习。"}],
        "movement_breakdown": [{"name": "山歌引手", "beats": "八拍", "teaching_tips": "肩膀放松。"}],
        "cooldown": [{"name": "呼吸放松", "duration_minutes": 5, "description": "伸展放松。"}],
        "homework": ["复习八拍组合"],
        "teacher_notes": ["正式上课前由老师确认"],
    }


class LessonPlanVariantSchemaTests(unittest.TestCase):
    """验证 T02 请求枚举和旧 T01 正文的向后兼容性。"""

    def test_old_t01_content_does_not_require_variant_fields(self):
        content = LessonPlanContent.model_validate(valid_lesson_content())

        self.assertIsNone(content.applicable_audience)
        self.assertEqual(content.adjustment_summary, [])

    def test_variant_request_accepts_four_presets_and_rejects_unknown_type(self):
        for variant_type in ["younger", "basic", "advanced", "performance"]:
            request = LessonPlanVariantGenerateRequest(variant_type=variant_type)
            self.assertEqual(request.variant_type, variant_type)

        with self.assertRaises(ValidationError):
            LessonPlanVariantGenerateRequest(variant_type="custom")

    def test_variant_table_uses_safe_delete_rules(self):
        foreign_keys = {foreign_key.parent.name: foreign_key.ondelete for foreign_key in LessonPlanVariant.__table__.foreign_keys}

        self.assertEqual(foreign_keys["lesson_plan_id"], "CASCADE")
        self.assertEqual(foreign_keys["source_lesson_plan_id"], "SET NULL")


class LessonPlanVariantServiceTests(unittest.TestCase):
    """验证变体详情、导出和 T05 上下文联动。"""

    def _record(self):
        now = datetime.utcnow()
        content = valid_lesson_content()
        content.update(
            {
                "applicable_audience": "6-8 岁、第一次接触民族舞的学生",
                "adjustment_summary": ["降低转身难度", "增加节奏模仿游戏"],
            }
        )
        return SimpleNamespace(
            id=uuid4(),
            course_id=uuid4(),
            title=content["title"],
            status="generated",
            content=content,
            edited_content=None,
            raw_model_info={"provider": "deepseek", "model": "deepseek-v4-flash", "generated_at": "2026-07-17"},
            created_at=now,
            updated_at=now,
        )

    def _variant(self, lesson_plan_id):
        return SimpleNamespace(
            lesson_plan_id=lesson_plan_id,
            source_lesson_plan_id=uuid4(),
            source_title_snapshot="客家山歌律动教案",
            source_content_snapshot=valid_lesson_content(),
            variant_type="younger",
            adjustment_direction="增强课堂趣味，避免连续转圈",
        )

    def test_detail_exposes_source_snapshot_and_variant_type(self):
        record = self._record()
        response = lesson_plan_response(record, self._variant(record.id))

        self.assertEqual(response.variant_info.variant_type, "younger")
        self.assertEqual(response.variant_info.source_content_snapshot.title, "客家山歌律动教案")
        self.assertEqual(response.content.applicable_audience, "6-8 岁、第一次接触民族舞的学生")

    def test_markdown_contains_variant_audience_and_adjustment_summary(self):
        record = self._record()
        markdown = render_lesson_plan_markdown(record, self._variant(record.id))

        self.assertIn("版本类型：低龄版", markdown)
        self.assertIn("6-8 岁、第一次接触民族舞的学生", markdown)
        self.assertIn("降低转身难度", markdown)
        self.assertIn("## 教学重难点", markdown)

    def test_class_interaction_prefill_includes_variant_context(self):
        record = self._record()
        course = SimpleNamespace(
            theme="客家山歌节奏",
            age_group="8-12 岁",
            student_count=20,
            course_style="活泼",
            teaching_goal="完成基础组合",
            notes="保持一臂距离",
        )

        prefill = build_lesson_interaction_prefill(course, record, self._variant(record.id))

        self.assertEqual(prefill.source_lesson_plan_title, record.title)
        self.assertEqual(prefill.source_variant_type, "younger")
        self.assertIn("变体适用对象：6-8 岁", prefill.lesson_context)
        self.assertIn("相对原版调整：降低转身难度", prefill.lesson_context)


class LessonPlanVariantOpenApiTests(unittest.TestCase):
    """确保 T02 接口在 OpenAPI 中可发现且中文语义明确。"""

    def test_openapi_exposes_variant_generate_and_list(self):
        from app.main import app

        paths = app.openapi()["paths"]
        generate_path = "/api/lesson-plans/{source_lesson_plan_id}/variants/generate"
        list_path = "/api/lesson-plans/{source_lesson_plan_id}/variants"
        self.assertIn("post", paths[generate_path])
        self.assertIn("get", paths[list_path])
        self.assertIn("T02", paths[generate_path]["post"]["summary"])


if __name__ == "__main__":
    unittest.main()
