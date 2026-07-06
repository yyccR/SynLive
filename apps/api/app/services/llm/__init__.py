"""LLM 服务模块。

通过 LiteLLM 网关统一调用 GPT / DeepSeek / Gemini / Doubao
（移植自 seo_video_generate/services/llm_model_service.py，解耦 Django）。
"""

from .chat import complete_litellm_chat, stream_litellm_chat
from .config import (
    DEFAULT_PERSONA_SYSTEM_PROMPT,
    LITELLM_MODEL_OPTIONS,
    MODEL_MAP,
    get_litellm_config,
    list_litellm_models,
)

__all__ = [
    "DEFAULT_PERSONA_SYSTEM_PROMPT",
    "LITELLM_MODEL_OPTIONS",
    "MODEL_MAP",
    "complete_litellm_chat",
    "stream_litellm_chat",
    "get_litellm_config",
    "list_litellm_models",
]
