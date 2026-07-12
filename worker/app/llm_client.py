import json
import time
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import BaseModel, ValidationError

from app.config import WorkerSettings
from app.llm_options import REASONING_LEVELS, provider_models
from app.schemas import (
    ClassInteractionContent,
    LessonPlanContent,
    MusicalFusionContent,
    MusicalScriptContent,
    RehearsalReviewContent,
    RoleTrainingContent,
    SongAdaptationContent,
)

LESSON_PLAN_PROMPT_VERSION = "lesson_plan_v1"
MUSICAL_SCRIPT_PROMPT_VERSION = "musical_script_v1"
SONG_ADAPTATION_PROMPT_VERSION = "song_adaptation_v1"
MUSICAL_FUSION_PROMPT_VERSION = "musical_fusion_v1"
ROLE_TRAINING_PROMPT_VERSION = "role_training_v1"
CLASS_INTERACTION_PROMPT_VERSION = "class_interaction_v1"
REHEARSAL_REVIEW_PROMPT_VERSION = "rehearsal_review_v1"
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
LESSON_PLAN_PROMPT_PATH = PROMPT_DIR / "lesson_plan_v1.md"
MUSICAL_SCRIPT_PROMPT_PATH = PROMPT_DIR / "musical_script_v1.md"
SONG_ADAPTATION_PROMPT_PATH = PROMPT_DIR / "song_adaptation_v1.md"
MUSICAL_FUSION_PROMPT_PATH = PROMPT_DIR / "musical_fusion_v1.md"
ROLE_TRAINING_PROMPT_PATH = PROMPT_DIR / "role_training_v1.md"
CLASS_INTERACTION_PROMPT_PATH = PROMPT_DIR / "class_interaction_v1.md"
REHEARSAL_REVIEW_PROMPT_PATH = PROMPT_DIR / "rehearsal_review_v1.md"
LLM_RETRY_ATTEMPTS = 4
LESSON_PLAN_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与教案无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合教案字段结构：title、course_overview、teaching_goals、key_points、common_mistakes、warmup、main_teaching、movement_breakdown、cooldown、homework、teacher_notes。
"""
MUSICAL_SCRIPT_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与剧本无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合剧本字段结构：title、synopsis、acts、characters、performance_slots、director_notes。
"""
SONG_ADAPTATION_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与唱段适配无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合唱段适配字段结构：title、source_song、related_scene、adaptation_goal、sections、dance_interludes、review_notes。
"""
MUSICAL_FUSION_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与歌舞融合结构无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合字段结构：title、related_scene、fusion_goal、stage_space、actor_count、overall_design、segments、highlight_summary、rehearsal_notes、director_review_notes。
5. segments 至少包含两个段落，并且至少一个段落的 is_highlight 为 true。
"""
ROLE_TRAINING_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与训练计划无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合训练计划字段结构：title、project_overview、role_tasks、daily_plan、teacher_checkpoints。
"""
CLASS_INTERACTION_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与课堂互动方案无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合课堂互动字段结构：title、teaching_phase、interaction_goal、duration_minutes、space_materials、game_rules、teacher_script、command_phrases、student_actions、grouping_method、encouragement_phrases、safety_notes、variations、teacher_check_notes。
5. teaching_phase 只能是「开场」「热身」「动作学习」「分组展示」「收束」之一。
"""
REHEARSAL_REVIEW_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增人工观察记录中不存在的具体演出事实。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合字段结构：title、overview、highlights、issues、role_suggestions、singing_and_rhythm_advice、dance_and_formation_advice、performance_and_blocking_advice、next_rehearsal_plan、teaching_reflection、reusable_template、reviewer_notes、boundary_note。
5. boundary_note 必须说明视频仅供人工查看，AI 未分析视频内容。
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

        return self._generate_structured_json(
            input_snapshot=input_snapshot,
            provider=provider,
            model=model,
            reasoning_level=reasoning_level,
            extra_body=extra_body,
            prompt_path=LESSON_PLAN_PROMPT_PATH,
            prompt_version=LESSON_PLAN_PROMPT_VERSION,
            schema_model=LessonPlanContent,
            repair_prompt=LESSON_PLAN_REPAIR_PROMPT,
            empty_message="LLM 返回内容为空。",
            truncated_message="LLM 输出被截断，无法生成完整教案 JSON，请调高 LLM_TIMEOUT_SECONDS 或降低推理强度后重试。",
            parse_error_label="教案 JSON",
            temperature=0.4,
        )

    def generate_musical_script(self, input_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """调用 LLM 生成结构化歌舞剧剧本。"""

        provider = str(input_snapshot.get("llm_provider") or self.settings.llm_default_provider)
        model = str(input_snapshot.get("llm_model") or self.settings.llm_default_model)
        reasoning_level = str(input_snapshot.get("reasoning_level") or self.settings.llm_default_reasoning_level)
        if model not in provider_models(provider):
            raise RuntimeError(f"{provider} 不支持模型 {model}。")
        extra_body = self._reasoning_extra_body(provider, reasoning_level)

        if self.settings.llm_mock_mode:
            return self._mock_musical_script(input_snapshot, provider, model, reasoning_level, extra_body)

        return self._generate_structured_json(
            input_snapshot=input_snapshot,
            provider=provider,
            model=model,
            reasoning_level=reasoning_level,
            extra_body=extra_body,
            prompt_path=MUSICAL_SCRIPT_PROMPT_PATH,
            prompt_version=MUSICAL_SCRIPT_PROMPT_VERSION,
            schema_model=MusicalScriptContent,
            repair_prompt=MUSICAL_SCRIPT_REPAIR_PROMPT,
            empty_message="LLM 返回内容为空。",
            truncated_message="LLM 输出被截断，无法生成完整剧本 JSON，请调高 LLM_TIMEOUT_SECONDS 或降低推理强度后重试。",
            parse_error_label="剧本 JSON",
            temperature=0.45,
        )

    def generate_song_adaptation(self, input_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """调用 LLM 生成结构化唱段适配与歌词改写建议。"""

        provider = str(input_snapshot.get("llm_provider") or self.settings.llm_default_provider)
        model = str(input_snapshot.get("llm_model") or self.settings.llm_default_model)
        reasoning_level = str(input_snapshot.get("reasoning_level") or self.settings.llm_default_reasoning_level)
        if model not in provider_models(provider):
            raise RuntimeError(f"{provider} 不支持模型 {model}。")
        extra_body = self._reasoning_extra_body(provider, reasoning_level)

        if self.settings.llm_mock_mode:
            return self._mock_song_adaptation(input_snapshot, provider, model, reasoning_level, extra_body)

        return self._generate_structured_json(
            input_snapshot=input_snapshot,
            provider=provider,
            model=model,
            reasoning_level=reasoning_level,
            extra_body=extra_body,
            prompt_path=SONG_ADAPTATION_PROMPT_PATH,
            prompt_version=SONG_ADAPTATION_PROMPT_VERSION,
            schema_model=SongAdaptationContent,
            repair_prompt=SONG_ADAPTATION_REPAIR_PROMPT,
            empty_message="LLM 返回内容为空。",
            truncated_message="LLM 输出被截断，无法生成完整唱段适配 JSON，请调高 LLM_TIMEOUT_SECONDS 或降低推理强度后重试。",
            parse_error_label="唱段适配 JSON",
            temperature=0.35,
        )

    def generate_musical_fusion(self, input_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """调用 LLM 生成结构化 M04 歌舞融合建议。"""

        provider = str(input_snapshot.get("llm_provider") or self.settings.llm_default_provider)
        model = str(input_snapshot.get("llm_model") or self.settings.llm_default_model)
        reasoning_level = str(input_snapshot.get("reasoning_level") or self.settings.llm_default_reasoning_level)
        if model not in provider_models(provider):
            raise RuntimeError(f"{provider} 不支持模型 {model}。")
        extra_body = self._reasoning_extra_body(provider, reasoning_level)

        if self.settings.llm_mock_mode:
            return self._mock_musical_fusion(input_snapshot, provider, model, reasoning_level, extra_body)

        return self._generate_structured_json(
            input_snapshot=input_snapshot,
            provider=provider,
            model=model,
            reasoning_level=reasoning_level,
            extra_body=extra_body,
            prompt_path=MUSICAL_FUSION_PROMPT_PATH,
            prompt_version=MUSICAL_FUSION_PROMPT_VERSION,
            schema_model=MusicalFusionContent,
            repair_prompt=MUSICAL_FUSION_REPAIR_PROMPT,
            empty_message="LLM 返回内容为空。",
            truncated_message="LLM 输出被截断，无法生成完整歌舞融合 JSON，请降低段落数量或推理强度后重试。",
            parse_error_label="歌舞融合方案 JSON",
            temperature=0.35,
        )

    def generate_role_training(self, input_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """调用 LLM 生成结构化分角色训练计划。"""

        provider = str(input_snapshot.get("llm_provider") or self.settings.llm_default_provider)
        model = str(input_snapshot.get("llm_model") or self.settings.llm_default_model)
        reasoning_level = str(input_snapshot.get("reasoning_level") or self.settings.llm_default_reasoning_level)
        if model not in provider_models(provider):
            raise RuntimeError(f"{provider} 不支持模型 {model}。")
        extra_body = self._reasoning_extra_body(provider, reasoning_level)

        if self.settings.llm_mock_mode:
            return self._mock_role_training(input_snapshot, provider, model, reasoning_level, extra_body)

        return self._generate_structured_json(
            input_snapshot=input_snapshot,
            provider=provider,
            model=model,
            reasoning_level=reasoning_level,
            extra_body=extra_body,
            prompt_path=ROLE_TRAINING_PROMPT_PATH,
            prompt_version=ROLE_TRAINING_PROMPT_VERSION,
            schema_model=RoleTrainingContent,
            repair_prompt=ROLE_TRAINING_REPAIR_PROMPT,
            empty_message="LLM 返回内容为空。",
            truncated_message="LLM 输出被截断，无法生成完整训练计划 JSON，请调高 LLM_TIMEOUT_SECONDS 或降低推理强度后重试。",
            parse_error_label="训练计划 JSON",
            temperature=0.35,
        )

    def generate_class_interaction(self, input_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """调用 LLM 生成老师可现场执行的结构化课堂互动方案。"""

        provider = str(input_snapshot.get("llm_provider") or self.settings.llm_default_provider)
        model = str(input_snapshot.get("llm_model") or self.settings.llm_default_model)
        reasoning_level = str(input_snapshot.get("reasoning_level") or self.settings.llm_default_reasoning_level)
        if model not in provider_models(provider):
            raise RuntimeError(f"{provider} 不支持模型 {model}。")
        extra_body = self._reasoning_extra_body(provider, reasoning_level)

        if self.settings.llm_mock_mode:
            return self._mock_class_interaction(input_snapshot, provider, model, reasoning_level, extra_body)

        return self._generate_structured_json(
            input_snapshot=input_snapshot,
            provider=provider,
            model=model,
            reasoning_level=reasoning_level,
            extra_body=extra_body,
            prompt_path=CLASS_INTERACTION_PROMPT_PATH,
            prompt_version=CLASS_INTERACTION_PROMPT_VERSION,
            schema_model=ClassInteractionContent,
            repair_prompt=CLASS_INTERACTION_REPAIR_PROMPT,
            empty_message="LLM 返回内容为空。",
            truncated_message="LLM 输出被截断，无法生成完整课堂互动方案 JSON，请降低时长或推理强度后重试。",
            parse_error_label="课堂互动方案 JSON",
            temperature=0.4,
        )

    def generate_rehearsal_review(self, input_snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """根据人工观察记录生成结构化 M08 复盘报告。"""

        provider = str(input_snapshot.get("llm_provider") or self.settings.llm_default_provider)
        model = str(input_snapshot.get("llm_model") or self.settings.llm_default_model)
        reasoning_level = str(input_snapshot.get("reasoning_level") or self.settings.llm_default_reasoning_level)
        if model not in provider_models(provider):
            raise RuntimeError(f"{provider} 不支持模型 {model}。")
        extra_body = self._reasoning_extra_body(provider, reasoning_level)

        if self.settings.llm_mock_mode:
            return self._mock_rehearsal_review(input_snapshot, provider, model, reasoning_level, extra_body)

        return self._generate_structured_json(
            input_snapshot=input_snapshot,
            provider=provider,
            model=model,
            reasoning_level=reasoning_level,
            extra_body=extra_body,
            prompt_path=REHEARSAL_REVIEW_PROMPT_PATH,
            prompt_version=REHEARSAL_REVIEW_PROMPT_VERSION,
            schema_model=RehearsalReviewContent,
            repair_prompt=REHEARSAL_REVIEW_REPAIR_PROMPT,
            empty_message="LLM 返回内容为空。",
            truncated_message="LLM 输出被截断，无法生成完整复盘报告 JSON，请减少观察记录长度或降低推理强度后重试。",
            parse_error_label="排练复盘 JSON",
            temperature=0.35,
        )

    def _generate_structured_json(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
        prompt_path: Path,
        prompt_version: str,
        schema_model: type[BaseModel],
        repair_prompt: str,
        empty_message: str,
        truncated_message: str,
        parse_error_label: str,
        temperature: float,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """调用 LLM 并按给定 Pydantic schema 校验结构化 JSON。"""

        prompt = prompt_path.read_text(encoding="utf-8")
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
            temperature=temperature,
            response_format={"type": "json_object"},
            extra_body=extra_body,
            timeout=self._request_timeout(model, reasoning_level),
        )
        message = response.choices[0].message.content
        if not message:
            raise RuntimeError(empty_message)
        if response.choices[0].finish_reason == "length":
            raise RuntimeError(truncated_message)

        validated = self._parse_structured_message(
            message=message,
            schema_model=schema_model,
            repair_prompt=repair_prompt,
            provider=provider,
            model=model,
            extra_body=extra_body,
            parse_error_label=parse_error_label,
        )
        model_info = {
            "provider": provider,
            "model": model,
            "reasoning_level": reasoning_level,
            "provider_parameters": extra_body,
            "prompt_version": prompt_version,
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

    def _parse_structured_message(
        self,
        message: str,
        schema_model: type[BaseModel],
        repair_prompt: str,
        provider: str,
        model: str,
        extra_body: dict[str, Any],
        parse_error_label: str,
    ) -> dict[str, Any]:
        """解析并校验结构化 JSON；失败时让模型只做一次 JSON 修复。

        一些模型即使开启 json_object，也可能在长中文字符串里漏逗号或未转义引号。
        与其让老师看到 Python 的 JSONDecodeError，这里先做一次受约束的自动修复。
        """

        try:
            content = json.loads(self._strip_json_fence(message))
            return schema_model.model_validate(content).model_dump()
        except (JSONDecodeError, ValidationError) as exc:
            repaired_message = self._repair_json_message(message, exc, repair_prompt, provider, model, extra_body)

        try:
            repaired_content = json.loads(self._strip_json_fence(repaired_message))
            return schema_model.model_validate(repaired_content).model_dump()
        except (JSONDecodeError, ValidationError) as repaired_exc:
            raise RuntimeError(
                f"模型返回的{parse_error_label}无法解析，自动修复后仍失败：{type(repaired_exc).__name__}: {repaired_exc}"
            ) from repaired_exc

    def _repair_json_message(
        self,
        message: str,
        parse_error: Exception,
        repair_prompt: str,
        provider: str,
        model: str,
        extra_body: dict[str, Any],
    ) -> str:
        """请求模型把 malformed JSON 修复为合法 JSON。"""

        repair_response = self._chat_completion(
            provider=provider,
            model=model,
            messages=[
                {"role": "system", "content": repair_prompt},
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
            "prompt_version": LESSON_PLAN_PROMPT_VERSION,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "finish_reason": "mock_mode",
            "usage": None,
        }
        return content, model_info

    def _mock_musical_script(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """生成本地演示剧本。"""

        title = f"{input_snapshot['theme']}小剧场"
        content = MusicalScriptContent(
            title=title,
            synopsis=(
                f"一部面向{input_snapshot['age_group']}演员的{input_snapshot['duration_minutes']}分钟歌舞剧，"
                f"围绕“{input_snapshot['theme']}”展开，用山歌、劳动场景和集体舞表达乡土美育。"
            ),
            acts=[
                {
                    "name": "第一幕：听见山歌",
                    "duration_minutes": 3,
                    "story_outline": "孩子们在村口听奶奶讲客家山歌的来历，第一次跟着节奏拍手。",
                    "emotion": "好奇、温暖",
                    "narrator_text": "一声山歌从远处飘来，把孩子们带进客家记忆。",
                    "dialogues": [
                        {
                            "role_name": "奶奶",
                            "line": "山歌不是只用来唱的，它也把家乡记在心里。",
                            "stage_direction": "面向孩子们，语速放慢，右手指向远处。",
                        },
                        {
                            "role_name": "阿月",
                            "line": "那我们可以把山歌跳出来吗？",
                            "stage_direction": "向前一步，带着好奇表情。",
                        },
                    ],
                },
                {
                    "name": "第二幕：一起排练",
                    "duration_minutes": 4,
                    "story_outline": "孩子们分成唱、跳、旁白和群演小组，学习用身体表现劳动节奏。",
                    "emotion": "活泼、投入",
                    "narrator_text": "拍手、踏步、转身，山歌慢慢变成了大家共同的动作。",
                    "dialogues": [
                        {
                            "role_name": "领舞",
                            "line": "我们先慢一点，听到四拍再打开手。",
                            "stage_direction": "站在队伍前方示范手位。",
                        }
                    ],
                },
                {
                    "name": "第三幕：唱响家乡",
                    "duration_minutes": 3,
                    "story_outline": "所有角色汇合，在群舞和齐唱中完成展示。",
                    "emotion": "热烈、团结",
                    "narrator_text": "当每个人都找到自己的位置，家乡的声音也被大家一起唱响。",
                    "dialogues": [
                        {
                            "role_name": "全体",
                            "line": "我们把山歌唱给明天听！",
                            "stage_direction": "形成半圆队形，最后定格。",
                        }
                    ],
                },
            ],
            characters=[
                {
                    "name": "阿月",
                    "role_type": "主角",
                    "personality": "好奇、主动、愿意带动同伴",
                    "character_arc": "从不敢表现到主动邀请大家一起完成展示。",
                    "performance_tips": "表情要明亮，台词短句清楚。",
                    "key_lines": ["那我们可以把山歌跳出来吗？"],
                },
                {
                    "name": "奶奶",
                    "role_type": "配角",
                    "personality": "温和、有故事感",
                    "character_arc": "用讲述帮助孩子理解山歌和家乡的关系。",
                    "performance_tips": "语速放慢，动作稳定。",
                    "key_lines": ["山歌不是只用来唱的，它也把家乡记在心里。"],
                },
                {
                    "name": "领舞",
                    "role_type": "领舞",
                    "personality": "稳重、节奏感强",
                    "character_arc": "从示范动作到带领全体完成高潮段落。",
                    "performance_tips": "队形变化前要给同伴明确眼神提示。",
                    "key_lines": ["我们先慢一点，听到四拍再打开手。"],
                },
            ],
            performance_slots=[
                {
                    "act_name": "第一幕：听见山歌",
                    "slot_type": "旁白过渡",
                    "description": "旁白结束后保留 15 秒，让孩子们用拍手进入节奏。",
                    "suggested_duration": "15 秒",
                    "notes": "节奏不要过快，方便低龄演员进入状态。",
                },
                {
                    "act_name": "第二幕：一起排练",
                    "slot_type": "群舞",
                    "description": "安排 8 拍 x 4 的劳动节奏组合，群演跟随领舞完成队形变化。",
                    "suggested_duration": "45 秒",
                    "notes": "动作以踏步、开合手和小转身为主，避免高难度跳跃。",
                },
                {
                    "act_name": "第三幕：唱响家乡",
                    "slot_type": "齐唱",
                    "description": "所有角色汇合，齐唱一句主题口号后进入终场造型。",
                    "suggested_duration": "30 秒",
                    "notes": "终场造型需要编导确认舞台空间。",
                },
            ],
            director_notes=["这是 mock 演示剧本，正式排练前需要编导复核。", "台词、时长和队形应按真实演员能力调整。"],
        ).model_dump()
        model_info = self._mock_model_info(provider, model, reasoning_level, extra_body, MUSICAL_SCRIPT_PROMPT_VERSION)
        return content, model_info

    def _mock_song_adaptation(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """生成本地演示唱段适配建议。"""

        script_title = input_snapshot.get("script_title") or "客家山歌小剧场"
        source_song = input_snapshot.get("source_song") or "客家山歌类曲目"
        related_scene = input_snapshot.get("related_scene") or "第二幕：一起排练"
        adaptation_goal = input_snapshot.get("adaptation_goal") or "表现孩子们从陌生到喜欢客家山歌的过程"
        content = SongAdaptationContent(
            title=f"{script_title} · {related_scene}唱段适配建议",
            source_song=str(source_song),
            related_scene=str(related_scene),
            adaptation_goal=str(adaptation_goal),
            sections=[
                {
                    "section_no": "A1",
                    "music_position": "0:00-0:18 前奏",
                    "original_lyrics": "前奏无歌词",
                    "adapted_lyrics": "保留前奏，由旁白引入山歌主题。",
                    "singing_mode": "旁白衔接",
                    "suggested_roles": ["旁白", "奶奶"],
                    "emotion": "温柔、铺垫",
                    "dance_opportunity": "群演用拍手和轻踏步建立节奏，不做复杂队形变化。",
                    "transition_note": "旁白结束后，主角从舞台左侧进入，听见第一句山歌。",
                },
                {
                    "section_no": "B1",
                    "music_position": "0:18-0:55 主歌一",
                    "original_lyrics": "山歌唱出家乡路，清清风里有回声",
                    "adapted_lyrics": "山歌唱出家乡路，小小脚步跟着风",
                    "singing_mode": "独唱",
                    "suggested_roles": ["阿月"],
                    "emotion": "好奇、明亮",
                    "dance_opportunity": "主角以站位表演和小幅手位为主，群演保持背景律动。",
                    "transition_note": "主歌结束后由奶奶回应，引出孩子们一起学习。",
                },
                {
                    "section_no": "C1",
                    "music_position": "0:55-1:25 副歌一",
                    "original_lyrics": "大家一起唱，山歌响满堂",
                    "adapted_lyrics": "大家一起唱，山歌亮课堂",
                    "singing_mode": "齐唱",
                    "suggested_roles": ["全体"],
                    "emotion": "热烈、团结",
                    "dance_opportunity": "适合加入群舞高潮，完成半圆到两排的队形变化。",
                    "transition_note": "齐唱收束后进入间奏，领舞带队形转场。",
                },
            ],
            dance_interludes=[
                {
                    "music_position": "1:25-1:45 间奏",
                    "suggestion": "安排 8 人做左右错落踏步，主角和奶奶在中区完成对望与递进动作。",
                }
            ],
            review_notes=[
                "这是 mock 演示数据，正式排练前需要音乐负责人确认歌词押韵和节拍。",
                "如使用已有曲目，应确认授权或改为原创填词。",
            ],
        ).model_dump()
        model_info = self._mock_model_info(provider, model, reasoning_level, extra_body, SONG_ADAPTATION_PROMPT_VERSION)
        return content, model_info

    def _mock_musical_fusion(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """生成同时覆盖 M03 引用和手工音乐段落模式的本地 M04 示例。"""

        script_title = str(input_snapshot.get("script_title") or "客家山歌小剧场")
        related_scene = str(input_snapshot.get("related_scene") or "第二幕：一起排练")
        fusion_goal = str(input_snapshot.get("fusion_goal") or "从剧情铺垫推进到全员齐唱群舞高潮")
        stage_space = str(input_snapshot.get("stage_space") or "普通教室或小舞台")
        actor_count = int(input_snapshot.get("actor_count") or 12)
        music_title = str(input_snapshot.get("music_title") or "客家山歌类曲目")
        content = MusicalFusionContent(
            title=f"{script_title} · {related_scene}歌舞融合建议",
            related_scene=related_scene,
            fusion_goal=fusion_goal,
            stage_space=stage_space,
            actor_count=actor_count,
            overall_design=(
                f"围绕《{music_title}》采用“旁白铺垫—主角领唱—全员齐唱—间奏转场”的递进结构，"
                "舞蹈强度和队形变化逐段增加，同时保留清楚的剧情信息和少儿排演安全距离。"
            ),
            segments=[
                {
                    "segment_no": "A1",
                    "story_content": "旁白介绍山歌和家乡记忆，主角从侧区进入。",
                    "music_position": "0:00-0:18 前奏",
                    "singing_mode": "不演唱，旁白衔接",
                    "singing_roles": ["旁白"],
                    "dance_form": "群演做轻踏步和呼吸式手位，保持背景律动。",
                    "formation_suggestion": "群演半圆分散，中心留出主角进入通道。",
                    "emotion": "温柔、好奇",
                    "song_dance_relationship": "动作只负责营造氛围，不遮挡旁白和主角入场。",
                    "transition_note": "旁白最后一句结束时，主角走到中心并接入主歌。",
                    "rehearsal_tip": "先无音乐排清入场路线，再加入前奏卡点。",
                    "safety_note": "半圆演员之间保持一臂距离，入场通道不得交叉。",
                    "is_highlight": False,
                },
                {
                    "segment_no": "B1",
                    "story_content": "主角第一次尝试唱山歌，其他角色用动作回应。",
                    "music_position": "0:18-0:55 主歌一",
                    "singing_mode": "主角独唱，奶奶短句回应",
                    "singing_roles": ["主角", "奶奶"],
                    "dance_form": "主角以表演性手位为主，群演做左右呼应的小幅动作。",
                    "formation_suggestion": "主角中心偏前，奶奶侧后方，群演保持两侧弧线。",
                    "emotion": "试探、逐渐明亮",
                    "song_dance_relationship": "独唱承担剧情，舞蹈保持克制并用呼应动作突出歌词关键词。",
                    "transition_note": "奶奶回应后，两侧群演向中心收拢准备副歌。",
                    "rehearsal_tip": "先把独唱和回应台词排稳，再加入群演动作。",
                    "safety_note": "向中心收拢时统一走两拍，不抢位、不快速转圈。",
                    "is_highlight": False,
                },
                {
                    "segment_no": "C1",
                    "story_content": "全体理解山歌情感，完成齐唱和群舞爆发点。",
                    "music_position": "0:55-1:25 副歌",
                    "singing_mode": "领唱带全体齐唱",
                    "singing_roles": ["领唱", "全体"],
                    "dance_form": "八拍群舞组合，动作幅度逐步打开并在末句定格。",
                    "formation_suggestion": "两排错位展开为宽半圆，领唱保持视觉中心。",
                    "emotion": "热烈、团结",
                    "song_dance_relationship": "齐唱和群舞同步增强，歌词重拍对应队形展开和手位打开。",
                    "transition_note": "副歌末句定格两拍后，由领舞带入间奏转场。",
                    "rehearsal_tip": "先慢速练队形变化，再按原速合唱跳，老师重点检查重拍同步。",
                    "safety_note": "展开队形时避免后退交叉，动作幅度按实际场地缩小。",
                    "is_highlight": True,
                },
                {
                    "segment_no": "D1",
                    "story_content": "间奏中角色完成位置交换，为后续剧情或收束做准备。",
                    "music_position": "1:25-1:45 间奏",
                    "singing_mode": "不演唱，可保留短口令",
                    "singing_roles": ["领舞"],
                    "dance_form": "领舞带队完成错位踏步和方向转换。",
                    "formation_suggestion": "宽半圆收成前后三组，主角回到中心。",
                    "emotion": "轻快、收束",
                    "song_dance_relationship": "间奏让舞蹈承担转场功能，不新增复杂剧情信息。",
                    "transition_note": "音乐收弱时全体面向中心，接入下一段台词或终场造型。",
                    "rehearsal_tip": "给每组设置固定终点标记，分组确认后再整体连接。",
                    "safety_note": "路线交汇处采用先后顺序，不同时穿越中心。",
                    "is_highlight": False,
                },
            ],
            highlight_summary="副歌 C1 是全段高潮：领唱带全员齐唱，两排展开为宽半圆并完成八拍群舞定格。",
            rehearsal_notes=[
                "先分别排唱段、动作和队形，再按 A1 到 D1 顺序连接。",
                "每次合排只增加一个变量，优先保证歌词、路线和安全距离清楚。",
            ],
            director_review_notes=[
                "这是 mock 演示方案，编导需要结合真实场地、演员能力和音乐长度复核。",
                "方案没有完成专业编舞或音频节拍分析，具体动作和卡点由老师最终确认。",
            ],
        ).model_dump()
        model_info = self._mock_model_info(provider, model, reasoning_level, extra_body, MUSICAL_FUSION_PROMPT_VERSION)
        return content, model_info

    def _mock_role_training(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """生成本地演示分角色训练计划。"""

        script_title = input_snapshot.get("script_title") or "客家山歌小剧场"
        fusion_content = input_snapshot.get("fusion_content") or {}
        fusion_note = (
            f" 已引用歌舞融合方案“{input_snapshot.get('fusion_plan_title') or fusion_content.get('title')}”，"
            f"训练时重点复现其高潮设计：{fusion_content.get('highlight_summary', '')}"
            if fusion_content
            else ""
        )
        content = RoleTrainingContent(
            title=f"{script_title} · 分角色训练计划",
            project_overview=(
                f"排练周期 {input_snapshot['rehearsal_days']} 天，每次 {input_snapshot['session_minutes']} 分钟，"
                f"重点训练：{input_snapshot['training_focus']}。{fusion_note}"
            ),
            role_tasks=[
                {
                    "role_name": "阿月",
                    "role_type": "主角",
                    "line_focus": "把关键疑问句说清楚，句尾保持上扬和好奇感。",
                    "singing_focus": "齐唱时保持稳定音量，不抢领唱。",
                    "dance_focus": "练习开合手和踏步连接，注意转身后面向观众。",
                    "blocking_tips": "第一幕从舞台左侧走到奶奶身边，第三幕回到半圆中心。",
                    "daily_tasks": ["第 1 天熟悉台词", "第 2 天加入走位", "第 3 天与群演合排"],
                    "teacher_checkpoints": ["台词是否短句清楚", "转身后是否能找到站位"],
                },
                {
                    "role_name": "奶奶",
                    "role_type": "配角",
                    "line_focus": "语速放慢，重点词如「山歌」「家乡」要说稳。",
                    "singing_focus": "没有独唱任务，主要在齐唱段落做情绪带入。",
                    "dance_focus": "动作幅度不需要大，重点是手势和身体方向。",
                    "blocking_tips": "多数时间站在中后区，避免遮挡主角和领舞。",
                    "daily_tasks": ["练习旁白式台词", "与阿月对话", "加入终场造型"],
                    "teacher_checkpoints": ["声音是否温和清楚", "手势是否自然"],
                },
                {
                    "role_name": "领舞",
                    "role_type": "领舞",
                    "line_focus": "口令短而有力，帮助群演进入节奏。",
                    "singing_focus": "齐唱中保持节奏提示，不需要突出个人音量。",
                    "dance_focus": "重点练习八拍组合、队形切换和终场定格。",
                    "blocking_tips": "站在队伍前方，转场时用眼神提示左右两组。",
                    "daily_tasks": ["拆分八拍动作", "带群演慢速练习", "合音乐完成终场"],
                    "teacher_checkpoints": ["节拍是否稳定", "能否带动群演同步"],
                },
            ],
            daily_plan=[
                {
                    "day": "第 1 天",
                    "focus": "读剧本和分角色认知",
                    "tasks": ["全体读剧本", "确认每个角色任务", "主角和旁白单独读台词"],
                    "expected_result": "演员知道自己在每一幕要做什么。",
                },
                {
                    "day": "第 2 天",
                    "focus": "台词和基础走位",
                    "tasks": ["分幕走位", "主角与配角对话", "群演练习入场路线"],
                    "expected_result": "主要角色能边走位边完成台词。",
                },
                {
                    "day": "第 3 天",
                    "focus": "群舞和终场合排",
                    "tasks": ["领舞带群演练习八拍组合", "加入齐唱", "完成终场定格"],
                    "expected_result": "形成可展示的完整排练版本。",
                },
            ],
            teacher_checkpoints=["不同角色任务是否有区分。", "群演和旁白是否都有明确任务。", "正式排练前需要老师确认动作难度。"],
        ).model_dump()
        model_info = self._mock_model_info(provider, model, reasoning_level, extra_body, ROLE_TRAINING_PROMPT_VERSION)
        return content, model_info

    def _mock_rehearsal_review(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """生成完全离线、且明确不分析视频的 M08 演示报告。"""

        script_title = str(input_snapshot.get("script_title") or "客家山歌小剧场")
        event_label = "演出" if input_snapshot.get("event_type") == "performance" else "排练"
        review_focus = [str(item) for item in input_snapshot.get("review_focus") or ["唱段", "队形", "表情"]]
        fusion_content = input_snapshot.get("fusion_content") or {}
        role_training_content = input_snapshot.get("role_training_content") or {}
        source_notes = []
        if fusion_content:
            source_notes.append(f"已参考 M04 高潮设计：{fusion_content.get('highlight_summary', '歌舞融合重点段落')}。")
        if role_training_content:
            source_notes.append("已参考 M05 的分角色任务和老师检查点。")
        role_name = "全体演员"
        role_tasks = role_training_content.get("role_tasks") or []
        if role_tasks:
            role_name = str(role_tasks[0].get("role_name") or role_name)
        strengths = str(input_snapshot.get("strengths") or "").strip()
        highlights = (
            [strengths]
            if strengths
            else ["人工记录未单独标注表现亮点，请老师结合现场情况补充后再确认报告。"]
        )
        role_observation = (
            "M05 已为该角色安排训练任务，本次需要由老师核对这些任务在现场的落实情况。"
            if role_tasks
            else "人工观察记录未按角色拆分表现，本条仅作为下一次分角色记录提示。"
        )

        content = RehearsalReviewContent(
            title=f"{script_title} · {input_snapshot.get('event_date', '')} {event_label}复盘",
            overview=(
                f"本次围绕“{input_snapshot.get('rehearsal_content', '')}”开展{event_label}。"
                f"以下结论仅整理老师填写的观察记录。{' '.join(source_notes)}"
            ),
            highlights=highlights,
            issues=[
                {
                    "category": review_focus[0],
                    "observation": str(
                        input_snapshot.get("issues")
                        or input_snapshot.get("observation_notes")
                        or "重点段落的完成稳定性仍需继续观察。"
                    ),
                    "possible_cause": "分段练习和完整连接之间的切换次数不足，演员对统一检查点还不够熟悉。",
                    "improvement_action": "下一次先按问题段落慢速拆分，再加入前后衔接，并由老师逐项确认。",
                    "priority": "high",
                    "next_check": "连续完成两次重点段落，确认节奏、队形和角色任务均能稳定复现。",
                },
            ],
            role_suggestions=[
                {
                    "role_name": role_name,
                    "observation": role_observation,
                    "suggestion": "先由老师补充该角色的现场观察，再确认个人任务，并与相邻角色完成两轮连接。",
                    "next_tasks": ["补充分角色观察", "复核个人关键段落", "确认与相邻角色的衔接信号"],
                },
            ],
            singing_and_rhythm_advice="先用拍点或口令统一进入时机，再加入歌词；老师重点检查重拍和句尾是否整齐。",
            dance_and_formation_advice="先确认起点、移动路线和终点，队形稳定后再增加动作幅度，避免同时修改多个变量。",
            performance_and_blocking_advice="角色进入重点段落前要有清楚的视线和情绪变化，转场时保持观众能理解剧情关系。",
            next_rehearsal_plan={
                "goal": str(input_snapshot.get("next_goal") or "稳定完成重点段落并跑通整场连接。"),
                "focus_items": review_focus,
                "action_steps": [
                    "用 10 分钟复盘本次两个最高优先级问题。",
                    "分角色或分组慢速修正重点段落。",
                    "加入唱段、动作和队形完成两次连接。",
                    "最后进行一次不中断合排并记录结果。",
                ],
                "teacher_checkpoints": ["问题是否有可观察改善", "转场是否减少临时提醒", "下一次任务是否落实到角色"],
            },
            teaching_reflection="本次复盘说明，先固定观察标准再合排，比同时纠正台词、唱段、动作和队形更容易形成稳定改进。老师后续可沿用同一检查清单记录变化。",
            reusable_template={
                "template_title": f"{script_title} · 常规{event_label}复盘模板",
                "review_focus": review_focus,
                "observation_prompts": [
                    "本次哪些段落已经可以稳定复现？",
                    "问题出现在哪个角色、段落或衔接环节？",
                    "老师减少提醒后，演员能否独立完成？",
                    "下一次最需要先解决哪一个问题？",
                ],
                "closing_checklist": ["确认问题有事实依据", "确认改进措施可执行", "确认任务落实到角色", "确认下次检查方法"],
            },
            reviewer_notes=["请老师核对问题描述是否符合现场事实。", "请结合真实场地和演员状态调整排练时长与动作强度。"],
            boundary_note="本报告仅整理人工观察记录；上传视频仅供人工查看，AI 未分析视频内容。",
        ).model_dump()
        model_info = self._mock_model_info(provider, model, reasoning_level, extra_body, REHEARSAL_REVIEW_PROMPT_VERSION)
        return content, model_info

    def _mock_class_interaction(
        self,
        input_snapshot: dict[str, Any],
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """生成完全离线、可用于前后端联调的课堂互动方案。"""

        theme = str(input_snapshot["course_theme"])
        duration = int(input_snapshot["duration_minutes"])
        teaching_phase = str(input_snapshot["teaching_phase"])
        goal = str(input_snapshot["interaction_goal"])
        space_materials = str(input_snapshot.get("space_materials") or "清空教室中间区域，无需额外材料").strip()
        if "保持一臂距离" not in space_materials:
            space_materials = space_materials.rstrip("；。") + "；学生之间保持一臂距离。"
        content = ClassInteractionContent(
            title=f"{theme} · 节奏动作接龙",
            teaching_phase=teaching_phase,
            interaction_goal=goal,
            duration_minutes=duration,
            space_materials=space_materials,
            game_rules=[
                "老师先示范一组四拍动作，学生观察后同步完成。",
                "第二轮由每组补充一个简单动作，全班按顺序接成动作链。",
            ],
            teacher_script=[
                {
                    "step_no": 1,
                    "name": "说明规则并示范",
                    "duration_hint": "2 分钟",
                    "teacher_action": "站在全班都能看见的位置，慢速示范拍手、踏步、打开双手四拍动作。",
                    "teacher_cue": "先看我一次，听到「开始」再一起做。",
                    "student_action": "保持原位观察，听到开始后同步完成四拍动作。",
                },
                {
                    "step_no": 2,
                    "name": "分组动作接龙",
                    "duration_hint": f"{max(duration - 4, 2)} 分钟",
                    "teacher_action": "按小组依次点名，每组在前一组动作后补充一个简单动作。",
                    "teacher_cue": "接住前一组的四拍，再加上你们的一拍动作！",
                    "student_action": "先重复已有动作，再补充一个原地拍手、踏步或手位动作。",
                },
                {
                    "step_no": 3,
                    "name": "全班完成并收束",
                    "duration_hint": "2 分钟",
                    "teacher_action": "用稳定口令带全班完成完整动作链，并请学生用手势反馈难度。",
                    "teacher_cue": "最后一次，眼睛看前方，四拍一起完成！",
                    "student_action": "全班同步完成动作链，并用大拇指手势反馈是否能跟上。",
                },
            ],
            command_phrases=["准备，眼睛看老师。", "四拍开始，一、二、三、四！", "停在原位，给同伴一点掌声。"],
            student_actions=["观察并复现老师的四拍动作。", "小组补充一个安全、简单的原地动作。", "全班同步完成动作链。"],
            grouping_method=(
                f"全班 {input_snapshot['student_count']} 人按现有座位或站位分成 4 至 6 人小组，"
                "空间不足时不移动队形。"
            ),
            encouragement_phrases=["这一组节奏接得很稳！", "动作简单清楚，大家一下就跟上了。", "谢谢你给同伴留出了空间。"],
            safety_notes=["开始前确认地面没有水渍、书包和线缆。", "学生之间保持一臂距离，不追逐、不碰撞、不快速转圈。"],
            variations=["时间不足时取消小组创编，只完成老师示范和全班复现。", "空间不足时全部改为原地拍手、点头和小幅手位动作。"],
            teacher_check_notes=["确认场地和学生间距安全。", "确认动作难度适合当前年龄段和课堂状态。", "正式执行前复核口令、分组和总时长。"],
        ).model_dump()
        model_info = self._mock_model_info(provider, model, reasoning_level, extra_body, CLASS_INTERACTION_PROMPT_VERSION)
        return content, model_info

    def _mock_model_info(
        self,
        provider: str,
        model: str,
        reasoning_level: str,
        extra_body: dict[str, Any],
        prompt_version: str,
    ) -> dict[str, Any]:
        """生成统一的 mock 模型信息。"""

        return {
            "provider": provider,
            "model": model,
            "reasoning_level": reasoning_level,
            "provider_parameters": extra_body,
            "mock": True,
            "prompt_version": prompt_version,
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "finish_reason": "mock_mode",
            "usage": None,
        }
