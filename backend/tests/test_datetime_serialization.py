import json
import unittest
from datetime import datetime, timedelta, timezone

from app.core.time import utc_datetime_isoformat, utc_now_isoformat
from app.schemas.base import ApiSchema


class TimestampExample(ApiSchema):
    """只用于验证全平台 Schema 继承后的时间序列化约定。"""

    created_at: datetime
    finished_at: datetime | None = None
    label: str


class ApiDateTimeSerializationTests(unittest.TestCase):
    """确保 UTC-naive 数据在 API 边界被明确标记为 UTC。"""

    def test_naive_datetime_is_serialized_with_utc_suffix(self):
        value = TimestampExample(created_at=datetime(2026, 7, 20, 14, 36, 22), label="任务")

        payload = json.loads(value.model_dump_json())

        self.assertEqual(payload["created_at"], "2026-07-20T14:36:22Z")
        self.assertIsNone(payload["finished_at"])
        self.assertEqual(payload["label"], "任务")
        # Python 模式仍返回 datetime，避免影响服务层和测试中的时间运算。
        self.assertIsInstance(value.model_dump()["created_at"], datetime)

    def test_aware_datetime_is_converted_to_utc(self):
        china_time = datetime(2026, 7, 20, 22, 36, 22, tzinfo=timezone(timedelta(hours=8)))

        self.assertEqual(utc_datetime_isoformat(china_time), "2026-07-20T14:36:22Z")

    def test_generated_timestamp_and_openapi_keep_standard_formats(self):
        self.assertTrue(utc_now_isoformat().endswith("Z"))
        schema = TimestampExample.model_json_schema()
        self.assertEqual(schema["properties"]["created_at"]["format"], "date-time")


if __name__ == "__main__":
    unittest.main()
