"""LLM 集中配置：模型表 + LiteLLM 凭据 + 消息规整。

移植自 seo_video_generate/services/llm_model_service.py，去掉 Django 依赖，
凭据改从 app.core.config.settings 读取（LITELLM_LLM_API_KEY / LITELLM_LLM_BASE_URL）。
"""

from __future__ import annotations

from ...core.config import settings

# 可用模型表（id → LiteLLM model 串）
LITELLM_MODEL_OPTIONS = [
    {
        "id": "llm-gpt",
        "provider": "gpt",
        "name": "GPT",
        "model": "openai/azure-gpt-5.4",
        "display_model": "azure-gpt-5.4",
        "description": "Azure GPT 5.4 via LiteLLM",
        "temperature": 1.0,
        "supports_images": True,
        "max_output_tokens": 32768,
    },
    {
        "id": "llm-deepseek",
        "provider": "deepseek",
        "name": "DeepSeek",
        "model": "openai/deepseek-v4-pro",
        "display_model": "deepseek-v4-pro",
        "description": "DeepSeek V4 Pro via LiteLLM",
        "temperature": 0.7,
        "supports_images": False,
        "max_output_tokens": 8192,
    },
    {
        "id": "llm-gemini",
        "provider": "gemini",
        "name": "Gemini",
        "model": "openai/gemini-3-pro-preview",
        "display_model": "gemini-3-pro-preview",
        "description": "Gemini 3 Pro Preview via LiteLLM",
        "temperature": 0.7,
        "supports_images": True,
        "max_output_tokens": 8192,
    },
    {
        "id": "llm-doubao",
        "provider": "doubao",
        "name": "Doubao",
        "model": "openai/doubao-seed-2-0-pro-260215",
        "display_model": "doubao-seed-2-0-pro-260215",
        "description": "Doubao Seed 2.0 Pro via LiteLLM",
        "temperature": 0.7,
        "supports_images": True,
        "max_output_tokens": 8192,
    },
]

MODEL_MAP = {item["id"]: item for item in LITELLM_MODEL_OPTIONS}

# 数字人直播主播默认人设（口播向、简洁、不编造）
DEFAULT_PERSONA_SYSTEM_PROMPT = (
    "你是一名专业的 AI 数字人直播主播兼客服。请用口语化、热情、简洁的中文回答观众问题；"
    "回答控制在 2-3 句话以内、适合口播；不要编造不确定的信息，不知道就说不太清楚并建议咨询；"
    "避免使用 Markdown、表情符号和列表符号。"
)


def get_litellm_config() -> tuple[str, str, int]:
    """返回 (api_key, api_base, max_output_tokens)，统一从 settings 读取。"""
    return (
        settings.llm_api_key,
        settings.llm_base_url,
        settings.llm_max_output_tokens,
    )


def list_litellm_models() -> list[dict]:
    """返回前端可用模型配置，不暴露 API Key。"""
    return [
        {
            "id": item["id"],
            "provider": item["provider"],
            "name": item["name"],
            "model": item["display_model"],
            "description": item["description"],
            "supports_images": item["supports_images"],
        }
        for item in LITELLM_MODEL_OPTIONS
    ]


def _normalize_content(content):
    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return None

    normalized = []
    for item in content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "text":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                normalized.append({"type": "text", "text": text.strip()})
        elif item_type == "image_url":
            image_url = item.get("image_url") or {}
            url = image_url.get("url") if isinstance(image_url, dict) else None
            if isinstance(url, str) and (
                url.startswith("data:image/")
                or url.startswith("http://")
                or url.startswith("https://")
            ):
                normalized.append({"type": "image_url", "image_url": {"url": url}})

    return normalized or None


def _messages_have_images(messages: list[dict]) -> bool:
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    return True
    return False


def _normalize_messages(messages: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for msg in messages[-20:]:
        role = msg.get("role")
        content = msg.get("content")
        if role not in {"system", "user", "assistant"}:
            continue
        clean_content = _normalize_content(content)
        if not clean_content:
            continue
        normalized.append({"role": role, "content": clean_content})
    return normalized


def _normalize_temperature(model_name: str, temperature: float | None, default_temperature: float) -> float:
    """
    GPT 5 系列通过当前 LiteLLM 代理调用时仅接受 temperature=1。
    其他模型保持传入值或模型默认值。
    """
    if "gpt-5" in model_name or "azure-gpt-5" in model_name:
        return 1.0
    if temperature is None:
        return default_temperature
    return max(0.0, min(float(temperature), 2.0))


def _format_litellm_error(exc: Exception) -> str:
    error_msg = str(exc)
    lowered = error_msg.lower()
    if "api_key" in lowered or "authentication" in lowered or "unauthorized" in lowered:
        return "LiteLLM API Key 无效或已过期"
    if "rate" in lowered or "quota" in lowered:
        return "LiteLLM 配额不足或触发速率限制"
    return f"LLM 调用失败: {error_msg[:300]}"
