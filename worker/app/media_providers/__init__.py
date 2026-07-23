"""第三方媒体生成供应商适配层。"""

from app.media_providers.base import MediaProvider, ProviderOutput, QueryResult, SubmitResult
from app.media_providers.grsai import GrsaiProvider
from app.media_providers.mock import MockMediaProvider
from app.media_providers.runninghub import RunningHubProvider

__all__ = [
    "GrsaiProvider", "MediaProvider", "MockMediaProvider", "ProviderOutput",
    "QueryResult", "RunningHubProvider", "SubmitResult",
]
