"""LiteLLM 对话调用（非流式 + SSE 流式）。

移植自 seo_video_generate/services/llm_model_service.py，凭据改走 get_litellm_config()。
"""

from __future__ import annotations

import json
from typing import Generator

import litellm
from loguru import logger

from .config import (
    DEFAULT_PERSONA_SYSTEM_PROMPT,
    MODEL_MAP,
    _format_litellm_error,
    _messages_have_images,
    _normalize_messages,
    _normalize_temperature,
    get_litellm_config,
)

# 关掉 litellm 自身的冗长日志/遥测
litellm.set_verbose = False
try:
    litellm.suppress_debug_info = True  # type: ignore[attr-defined]
except Exception:
    pass


def sse_event(event_type: str, data: dict) -> str:
    payload = {"type": event_type, **data}
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def complete_litellm_chat(
    model_id: str,
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> dict:
    """非流式对话调用，返回模型文本内容与元信息。失败抛 RuntimeError。"""
    from ...core.config import settings

    model_config = MODEL_MAP.get(model_id)
    if not model_config:
        raise ValueError("不支持的 LLM 模型")

    api_key, api_base, configured_max_output = get_litellm_config()
    if not api_key:
        raise ValueError("LiteLLM API Key 未配置")

    clean_messages = _normalize_messages(messages)
    if not clean_messages:
        raise ValueError("消息不能为空")
    if _messages_have_images(clean_messages) and not model_config.get("supports_images"):
        raise ValueError(f"{model_config['name']} 当前不支持图片输入")

    prompt = system_prompt.strip() if isinstance(system_prompt, str) and system_prompt else ""
    if not prompt:
        prompt = DEFAULT_PERSONA_SYSTEM_PROMPT

    model_name = model_config["model"]
    safe_max_tokens = int(max_tokens or 4096)
    max_output_tokens = max(1, int(configured_max_output or model_config.get("max_output_tokens", 8192)))
    safe_temperature = _normalize_temperature(
        model_name, temperature, float(model_config.get("temperature", 0.7))
    )

    params = {
        "model": model_name,
        "messages": [{"role": "system", "content": prompt}] + clean_messages,
        "stream": False,
        "max_tokens": max(1, min(safe_max_tokens, max_output_tokens)),
        "temperature": safe_temperature,
        "api_key": api_key,
        "api_base": api_base,
        "timeout": settings.llm_request_timeout,
    }

    try:
        response = litellm.completion(**params)
    except Exception as exc:
        logger.error(f"[LLM] completion failed: model={model_id} err={exc}")
        raise RuntimeError(_format_litellm_error(exc)) from exc

    content = ""
    if getattr(response, "choices", None):
        message = getattr(response.choices[0], "message", None)
        if isinstance(message, dict):
            content = message.get("content") or ""
        else:
            content = getattr(message, "content", "") or ""

    logger.info(
        f"[LLM] completion ok: model={model_id} in_msgs={len(clean_messages)} "
        f"out_len={len(content)}"
    )
    return {
        "content": content.strip(),
        "model_id": model_config["id"],
        "model": model_config["display_model"],
        "provider": model_config["provider"],
    }


def stream_litellm_chat(
    model_id: str,
    messages: list[dict],
    system_prompt: str = "",
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> Generator[str, None, None]:
    """SSE 流式对话，逐段 yield 已格式化的 SSE 字符串。"""
    from ...core.config import settings

    model_config = MODEL_MAP.get(model_id)
    if not model_config:
        yield sse_event("error", {"message": "不支持的 LLM 模型"})
        return

    api_key, api_base, configured_max_output = get_litellm_config()
    if not api_key:
        yield sse_event("error", {"message": "LiteLLM API Key 未配置"})
        return

    clean_messages = _normalize_messages(messages)
    if not clean_messages:
        yield sse_event("error", {"message": "消息不能为空"})
        return
    if _messages_have_images(clean_messages) and not model_config.get("supports_images"):
        yield sse_event(
            "error",
            {"message": f"{model_config['name']} 当前不支持图片输入，请切换 GPT、Gemini 或 Doubao"},
        )
        return

    prompt = system_prompt.strip() if isinstance(system_prompt, str) and system_prompt else ""
    if not prompt:
        prompt = DEFAULT_PERSONA_SYSTEM_PROMPT

    request_messages = [{"role": "system", "content": prompt}] + clean_messages
    model_name = model_config["model"]
    safe_max_tokens = int(max_tokens or 4096)
    max_output_tokens = max(1, int(configured_max_output or model_config.get("max_output_tokens", 8192)))
    safe_temperature = _normalize_temperature(
        model_name, temperature, float(model_config.get("temperature", 0.7))
    )

    params = {
        "model": model_name,
        "messages": request_messages,
        "stream": True,
        "max_tokens": max(1, min(safe_max_tokens, max_output_tokens)),
        "temperature": safe_temperature,
        "api_key": api_key,
        "api_base": api_base,
        "timeout": settings.llm_request_timeout,
    }

    try:
        yield sse_event(
            "meta",
            {
                "model_id": model_config["id"],
                "model": model_config["display_model"],
                "provider": model_config["provider"],
            },
        )

        response = litellm.completion(**params)
        for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield sse_event("content", {"text": content})

        yield sse_event("done", {"model_id": model_config["id"]})
    except Exception as exc:
        logger.error(f"[LLM] stream failed: model={model_id} err={exc}")
        yield sse_event("error", {"message": _format_litellm_error(exc)})
