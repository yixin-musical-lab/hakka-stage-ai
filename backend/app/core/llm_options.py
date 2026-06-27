from typing import Literal

LlmProvider = Literal["deepseek", "qwen"]
ReasoningLevel = Literal["off", "standard", "enhanced"]

DEEPSEEK_MODELS = ["deepseek-v4-flash", "deepseek-v4-pro"]
QWEN_MODELS = ["qwen3.7-plus", "qwen3.7-max", "qwen3.6-flash", "qwen3.6-plus"]
REASONING_LEVELS = ["off", "standard", "enhanced"]


def models_for_provider(provider: str) -> list[str]:
    """返回指定供应商可用的模型列表。"""

    if provider == "deepseek":
        return DEEPSEEK_MODELS
    if provider == "qwen":
        return QWEN_MODELS
    return []


def is_supported_model(provider: str, model: str) -> bool:
    """校验模型是否属于指定供应商，避免前端或接口传错模型名。"""

    return model in models_for_provider(provider)


def is_supported_reasoning_level(reasoning_level: str) -> bool:
    """校验统一推理强度。"""

    return reasoning_level in REASONING_LEVELS
