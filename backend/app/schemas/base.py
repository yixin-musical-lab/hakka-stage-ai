from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_serializer

from app.core.time import utc_datetime_isoformat


class ApiSchema(BaseModel):
    """平台 API Schema 的公共基类。

    数据库继续使用稳定的 UTC-naive 存储约定，但所有 JSON 响应都必须显式携带 ``Z``。
    这样浏览器、移动端或第三方客户端都不会把 UTC 时间误判为自己的本地时间。
    ``when_used='json'`` 确保 Python 内部的 ``model_dump()`` 仍保留 datetime 对象。
    """

    @field_serializer("*", mode="wrap", when_used="json", check_fields=False)
    def serialize_api_field(self, value: Any, handler):
        if isinstance(value, datetime):
            return utc_datetime_isoformat(value)
        return handler(value)
