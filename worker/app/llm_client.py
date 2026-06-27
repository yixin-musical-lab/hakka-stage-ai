import json
import time
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import ValidationError

from app.config import WorkerSettings
from app.llm_options import REASONING_LEVELS, provider_models
from app.schemas import LessonPlanContent

PROMPT_VERSION = "lesson_plan_v1"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "lesson_plan_v1.md"
LLM_RETRY_ATTEMPTS = 4
REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与教案无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合教案字段结构：title、course_overview、teaching_goals、key_points、common_mistakes、warmup、main_teaching、movement_breakdown、cooldown、homework、teacher_notes。
"""


class LLMClient:
    """统一的大模型调用封装。

    业务代码只依赖这个类，不直接依赖 DeepSeek、通义千问或 OpenAI 的具体 SDK 参数。
    """

    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings
        self.clients: dict[str, OpenAI] = {}

    def _client(self, provider: str) -> OpenAI:
        """按供应商延迟创建 OpenAI 兼容客户端。"""

        provider_config = self._provider_config(provider)
        if not provider_config["api_key"]:
            env_name = "DEEPSEEK_API_KEY" if provider == "deepseek" else "QWEN_API_KEY"
            raise RuntimeError(f"{env_name} 未配置，无法调用 {provider} 模型。")
        if provider not in self.clients:
            self.clients[provider] = OpenAI(
                api_key=provider_config["api_key"],
                base_url=provider_config["base_url"],
            )
        return self.clients[provider]

    def generate_lesson_plan(self, input_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """调用 LLM 生成结构化教案，并返回教案内容和脱敏后的模型信息。"""

        provider = str(input_snapshot.get("llm_provider") or self.settings.llm_default_provider)
        model = str(input_snapshot.get("llm_model") or self.settings.llm_default_model)
        reasoning_level = str(input_snapshot.get("reasoning_level") or self.settings.llm_default_reasoning_level)
        if model not in provider_models(provider):
            raise RuntimeError(f"{provider} 不支持模型 {model}。")
        extra_body = self._reasoning_extra_body(provider, reasoning_level)

        if self.settings.llm_mock_mode:
            return self._mock_lesson_plan(input_snapshot, provider, model, reasoning_level, extra_body)

        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(input_snapshot, ensure_ascii=False, indent=2),
            },
        ]
        response = self._chat_completion(
            provider=provider,
            model=model,
            messages=messages,
            temperature=0.4,
            response_format={"type": "json_object"},
            extra_body=extra_body,
            timeout=self._request_timeout(model, reasoning_level),
        )
        message = response.choices[0].message.content
        if not message:
            raise RuntimeError("LLM 返回内容为空。")
        if response.choices[0].finish_reason == "length":
            raise RuntimeError("LLM 输出被截断，无法生成完整教案 JSON，请调高 LLM_TIMEOUT_SECONDS 或降低推理强度后重试。")

        validated = self._parse_lesson_plan_message(
            message=message,
            provider=provider,
            model=model,
            extra_body=extra_body,
        )
        model_info = {
            "provider": provider,
            "model": model,
            "reasoning_level": reasoning_level,
            "provider_parameters": extra_body,
            "prompt_version": PROMPT_VERSION,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "finish_reason": response.choices[0].finish_reason,
            "usage": response.usage.model_dump() if response.usage else None,
        }
        return validated, model_info

    def _chat_completion(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        response_format: dict[str, str],
        extra_body: dict[str, Any],
        timeout: float,
    ) -> Any:
        """调用 OpenAI-compatible Chat Completion，并对连接类错误做短重试。

        DeepSeek Pro 与增强推理偶尔会因为首包慢被 SDK 包装成 Connection error。
        这里重试的是网络/5xx 类瞬时错误，不会吞掉鉴权、参数错误等确定性失败。
        """

        last_error: Exception | None = None
        for attempt in range(1, LLM_RETRY_ATTEMPTS + 1):
            try:
                return self._client(provider).with_options(timeout=timeout).chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format=response_format,
                    extra_body=extra_body,
                )
            except (APIConnectionError, APITimeoutError) as exc:
                last_error = exc
            except APIStatusError as exc:
                if exc.status_code < 500 or attempt == LLM_RETRY_ATTEMPTS:
                    raise
                last_error = exc

            if attempt < LLM_RETRY_ATTEMPTS:
                time.sleep(1.5 * attempt)

        detail = self._connection_error_detail(last_error)
        raise RuntimeError(f"{provider}/{model} 调用失败，已重试 {LLM_RETRY_ATTEMPTS} 次：{detail}") from last_error

    def _parse_lesson_plan_message(
        self,
        message: str,
        provider: str,
        model: str,
        extra_body: dict[str, Any],
    ) -> dict[str, Any]:
        """解析并校验教案 JSON；失败时让模型只做一次 JSON 修复。

        一些模型即使开启 json_object，也可能在长中文字符串里漏逗号或未转义引号。
        与其让老师看到 Python 的 JSONDecodeError，这里先做一次受约束的自动修复。
        """

        try:
            content = json.loads(self._strip_json_fence(message))
            return LessonPlanContent.model_validate(content).model_dump()
        except (JSONDecodeError, ValidationError) as exc:
            repaired_message = self._repair_json_message(message, exc, provider, model, extra_body)

        try:
            repaired_content = json.loads(self._strip_json_fence(repaired_message))
            return LessonPlanContent.model_validate(repaired_content).model_dump()
        except (JSONDecodeError, ValidationError) as repaired_exc:
            raise RuntimeError(
                f"模型返回的教案 JSON 无法解析，自动修复后仍失败：{type(repaired_exc).__name__}: {repaired_exc}"
            ) from repaired_exc

    def _repair_json_message(
        self,
        message: str,
        parse_error: Exception,
        provider: str,
        model: str,
        extra_body: dict[str, Any],
    ) -> str:
        """请求模型把 malformed JSON 修复为合法 JSON。"""

        repair_response = self._chat_completion(
            provider=provider,
            model=model,
            messages=[
                {"role": "system", "content": REPAIR_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"解析错误：{type(parse_error).__name__}: {parse_error}\n\n"
                        "需要修复的模型原文如下：\n"
                        f"{message[:12000]}"
                    ),
                },
            ],
            temperature=0,
            response_format={"type": "json_object"},
            extra_body=self._repair_extra_body(provider, extra_body),
            timeout=max(self.settings.llm_timeout_seconds, 120),
        )
        repaired_message = repair_response.choices[0].message.content
        if not repaired_message:
            raise RuntimeError("模型 JSON 修复结果为空。")
        return repaired_message

    def _request_timeout(self, model: str, reasoning_level: str) -> float:
        """根据模型和推理强度给请求留出合理超时。

        Pro 模型与增强推理首包更慢，使用基础 90 秒时容易表现为 Connection error。
        这里仍尊重用户配置，只在配置过低时给重模型设置安全下限。
        """

        timeout = self.settings.llm_timeout_seconds
        if model.endswith("-pro"):
            timeout = max(timeout, 180)
        if reasoning_level == "enhanced":
            timeout = max(timeout, 240)
        return timeout

    def _strip_json_fence(self, message: str) -> str:
        """移除模型偶尔包上的 JSON 代码块围栏。"""

        stripped = message.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return stripped

    def _connection_error_detail(self, exc: Exception | None) -> str:
        """提取连接错误的底层原因，避免前端只看到模糊的 Connection error。"""

        if exc is None:
            return "未知连接错误。"
        cause = getattr(exc, "__cause__", None)
        if cause is not None:
            return f"{type(cause).__name__}: {cause}"
        return str(exc) or type(exc).__name__

    def _repair_extra_body(self, provider: str, fallback_extra_body: dict[str, Any]) -> dict[str, Any]:
        """JSON 修复阶段尽量关闭额外思考，让模型直接输出修复后的对象。"""

        try:
            return self._reasoning_extra_body(provider, "off")
        except RuntimeError:
            return fallback_extra_body

    def _provider_config(self, provider: str) -> dict[str, str]:
        """获取供应商配置，并校验模型供应商名称。"""

        if provider == "deepseek":
            return {"api_key": self.settings.deepseek_api_key, "base_url": self.settings.deepseek_base_url}
        if provider == "qwen":
            return {"api_key": self.settings.qwen_api_key, "base_url": self.settings.qwen_base_url}
        raise RuntimeError(f"不支持的大模型供应商：{provider}")

    def _reasoning_extra_body(self, provider: str, reasoning_level: str) -> dict[str, Any]:
        """把系统统一推理强度映射为各供应商的 OpenAI-compatible 扩展参数。"""

        if reasoning_level not in REASONING_LEVELS:
            raise RuntimeError(f"不支持的推理强度：{reasoning_level}")

        if provider_models(provider) == []:
            raise RuntimeError(f"不支持的大模型供应商：{provider}")

        if provider == "deepseek":
            if reasoning_level == "off":
                return {"thinking": {"type": "disabled"}}
            effort = "max" if reasoning_level == "enhanced" else "high"
            return {"thinking": {"type": "enabled"}, "reasoning_effort": effort}

        if provider == "qwen":
            if reasoning_level == "off":
                return {"enable_thinking": False}
            thinking_budget = 12000 if reasoning_level == "enhanced" else 4096
            return {"enable_thinking": True, "thinking_budget": thinking_budget}

        raise RuntimeError(f"不支持的大模型供应商：{provider}")

    def _mock_lesson_plan(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """生成本地演示教案。

        这个兜底只在 LLM_MOCK_MODE=true 时启用，用于 API Key 暂不可用或演示现场网络异常。
        """

        duration = int(input_snapshot["duration_minutes"])
        title = f"{input_snapshot['theme']} · {input_snapshot['dance_style']}教案"
        content = LessonPlanContent(
            title=title,
            course_overview=(
                f"面向{input_snapshot['age_group']}学生的{duration}分钟课程，"
                f"围绕“{input_snapshot['theme']}”学习{input_snapshot['dance_style']}基础组合。"
            ),
            teaching_goals=[
                f"理解{input_snapshot['dance_style']}的节奏特点和文化表达。",
                "掌握一个安全、清晰、可排练的八拍动作组合。",
                "能在老师口令下完成队形进入、动作连接和情绪表达。",
            ],
            key_points=["节拍稳定", "手位方向清楚", "动作和乡土情感表达一致"],
            common_mistakes=["抢拍或漏拍", "手臂路线含糊", "只模仿动作但缺少表情和呼吸"],
            warmup=[
                {
                    "name": "节奏唤醒",
                    "duration_minutes": 6,
                    "description": "用拍手、踏步和呼吸练习建立四拍稳定节奏，提醒学生膝盖放松。",
                }
            ],
            main_teaching=[
                {
                    "name": "主题动作组合",
                    "duration_minutes": max(duration - 14, 12),
                    "description": "分句教学手位、脚步和转身连接，先慢速口令，再配音乐完成。",
                }
            ],
            movement_breakdown=[
                {
                    "name": "山歌引手",
                    "beats": "八拍 x 1",
                    "teaching_tips": "双手从胸前打开到斜上方，眼神跟随手位，注意肩膀放松。",
                },
                {
                    "name": "踏步转身",
                    "beats": "八拍 x 1",
                    "teaching_tips": "小步移动，转身时保持重心稳定，不做高难度跳跃。",
                },
            ],
            cooldown=[
                {
                    "name": "呼吸与伸展",
                    "duration_minutes": 5,
                    "description": "放慢音乐，做肩颈、手腕和腿部伸展，回顾今天的文化主题。",
                }
            ],
            homework=["回家练习两遍八拍组合。", "用一句话写下自己理解的客家山歌情绪。"],
            teacher_notes=["这是 mock 演示数据，正式上课前需要老师复核。", "注意控制动作难度和学生间距。"],
        ).model_dump()
        model_info = {
            "provider": provider,
            "model": model,
            "reasoning_level": reasoning_level,
            "provider_parameters": extra_body,
            "mock": True,
            "prompt_version": PROMPT_VERSION,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "finish_reason": "mock_mode",
            "usage": None,
        }
        return content, model_info
