DEEPSEEK_MODELS = ["deepseek-v4-flash", "deepseek-v4-pro"]
QWEN_MODELS = ["qwen3.7-plus", "qwen3.7-max", "qwen3.6-flash", "qwen3.6-plus"]
REASONING_LEVELS = ["off", "standard", "enhanced"]


def provider_models(provider: str) -> list[str]:
    """返回指定供应商支持的模型列表。"""

    if provider == "deepseek":
        return DEEPSEEK_MODELS
    if provider == "qwen":
        return QWEN_MODELS
    return []
