from fastapi import APIRouter

from app.core.config import get_settings
from app.core.llm_options import DEEPSEEK_MODELS, QWEN_MODELS, REASONING_LEVELS, is_supported_model
from app.schemas import LlmModelOption, LlmOptionsResponse, LlmProviderOption, ReasoningLevelOption

router = APIRouter(prefix="/api", tags=["llm-options"])


@router.get("/llm-options", response_model=LlmOptionsResponse, summary="查询可用大模型选项")
def get_llm_options() -> LlmOptionsResponse:
    """返回前端教案生成页需要的模型供应商、模型和推理强度选项。"""

    settings = get_settings()
    default_provider = settings.llm_default_provider if settings.llm_default_provider in {"deepseek", "qwen"} else "deepseek"
    fallback_model = "qwen3.7-plus" if default_provider == "qwen" else "deepseek-v4-flash"
    default_model = settings.llm_default_model if is_supported_model(default_provider, settings.llm_default_model) else fallback_model
    default_reasoning_level = (
        settings.llm_default_reasoning_level
        if settings.llm_default_reasoning_level in REASONING_LEVELS
        else "standard"
    )

    return LlmOptionsResponse(
        default_provider=default_provider,
        default_model=default_model,
        default_reasoning_level=default_reasoning_level,
        providers=[
            LlmProviderOption(
                id="deepseek",
                label="DeepSeek",
                configured=bool(settings.deepseek_api_key) or settings.llm_mock_mode,
                models=[LlmModelOption(id=model, label=model) for model in DEEPSEEK_MODELS],
            ),
            LlmProviderOption(
                id="qwen",
                label="百炼 Qwen",
                configured=bool(settings.qwen_api_key) or settings.llm_mock_mode,
                models=[LlmModelOption(id=model, label=model) for model in QWEN_MODELS],
            ),
        ],
        reasoning_levels=[
            ReasoningLevelOption(id="off", label="关闭", description="不启用额外思考，优先速度。"),
            ReasoningLevelOption(id="standard", label="标准", description="启用中等推理预算，适合常规教案。"),
            ReasoningLevelOption(id="enhanced", label="增强", description="启用更高推理预算，适合复杂课程设计。"),
        ],
    )
