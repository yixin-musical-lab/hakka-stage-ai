import unittest
from datetime import datetime
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.services.workspace_overview_service import (
    _build_workspace_overview_statement,
    build_workspace_overview,
)


class _FakeMappingResult:
    """只实现概览服务单元测试需要的 SQLAlchemy 结果接口。"""

    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def mappings(self):
        return self

    def all(self) -> list[dict]:
        return self._rows


class _FakeSession:
    """记录执行语句，并返回预设的映射行。"""

    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)
        return _FakeMappingResult(self.rows)


class WorkspaceOverviewServiceTests(unittest.TestCase):
    """验证概览聚合结果和轻量查询边界。"""

    def test_builds_counts_latest_item_and_empty_modules(self):
        latest_id = uuid4()
        latest_time = datetime(2026, 7, 16, 9, 30)
        session = _FakeSession(
            [
                {
                    "module": "lesson_plans",
                    "total_count": 3,
                    "id": latest_id,
                    "title": "客家山歌体验课",
                    "status": "reviewed",
                    "updated_at": latest_time,
                }
            ]
        )

        overview = build_workspace_overview(session)  # type: ignore[arg-type]

        self.assertEqual(overview.lesson_plans.count, 3)
        self.assertEqual(overview.lesson_plans.latest.id, latest_id)
        self.assertEqual(overview.lesson_plans.latest.title, "客家山歌体验课")
        self.assertEqual(overview.musical_scripts.count, 0)
        self.assertIsNone(overview.musical_scripts.latest)
        self.assertEqual(len(session.statements), 1)

    def test_query_selects_only_summary_columns(self):
        statement = _build_workspace_overview_statement()
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).lower()

        self.assertEqual(sql.count("limit 1"), 9)
        self.assertNotIn("edited_content", sql)
        self.assertNotIn("raw_model_info", sql)
        self.assertNotIn("raw_pipeline_info", sql)
        self.assertNotIn("select *", sql)


class WorkspaceOverviewOpenApiTests(unittest.TestCase):
    """确保轻量工作空间概览接口在 OpenAPI 中可发现。"""

    def test_openapi_exposes_workspace_overview(self):
        from app.main import app

        operation = app.openapi()["paths"]["/api/workspace/overview"]["get"]
        self.assertEqual(operation["summary"], "查询轻量工作空间概览")
        self.assertIn("200", operation["responses"])


if __name__ == "__main__":
    unittest.main()
