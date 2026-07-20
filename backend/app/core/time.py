from datetime import datetime, timezone


def utc_datetime_isoformat(value: datetime) -> str:
    """把数据库时间序列化为带 ``Z`` 的 UTC ISO 8601 字符串。

    当前数据库按项目既有约定保存 UTC-naive 时间；这里在 API 边界补全时区语义。
    如果后续某个数据源已经返回 aware 时间，也统一转换为 UTC，避免同一接口混用偏移量。
    """

    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


def utc_now_isoformat() -> str:
    """生成可直接写入 JSON 内容的标准 UTC 时间字符串。"""

    return utc_datetime_isoformat(datetime.now(timezone.utc))
