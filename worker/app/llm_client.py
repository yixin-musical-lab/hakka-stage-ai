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
from app.schemas import LessonPlanContent, MusicalScriptContent, RoleTrainingContent

LESSON_PLAN_PROMPT_VERSION = "lesson_plan_v1"
MUSICAL_SCRIPT_PROMPT_VERSION = "musical_script_v1"
ROLE_TRAINING_PROMPT_VERSION = "role_training_v1"
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
LESSON_PLAN_PROMPT_PATH = PROMPT_DIR / "lesson_plan_v1.md"
MUSICAL_SCRIPT_PROMPT_PATH = PROMPT_DIR / "musical_script_v1.md"
ROLE_TRAINING_PROMPT_PATH = PROMPT_DIR / "role_training_v1.md"
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
ROLE_TRAINING_REPAIR_PROMPT = """你是严格的 JSON 修复器。

请把用户提供的模型原文修复为一个合法 JSON 对象。

规则：
1. 只能输出 JSON，不要 Markdown、代码块或解释。
2. 不要新增与训练计划无关的信息，尽量保留原始语义。
3. 修复缺失逗号、未转义双引号、尾逗号、代码块包裹等常见问题。
4. JSON 必须符合训练计划字段结构：title、project_overview、role_tasks、daily_plan、teacher_checkpoints。
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
        content = RoleTrainingContent(
            title=f"{script_title} · 分角色训练计划",
            project_overview=(
                f"排练周期 {input_snapshot['rehearsal_days']} 天，每次 {input_snapshot['session_minutes']} 分钟，"
                f"重点训练：{input_snapshot['training_focus']}。"
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
