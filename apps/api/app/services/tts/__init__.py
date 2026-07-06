"""TTS 服务模块。

本阶段实现 Azure 神经网络 TTS（移植自 seo_video_generate/services/tts，解耦 Django）。
后续可在此挂载 CosyVoice / GPT-SoVITS 等本地声线，统一走 base.TTSAdapter 协议。
"""

from .config import (
    AZURE_TTS,
    AZURE_TTS_LANG_MAPPING,
    LANGUAGE_OPTIONS,
    default_voice,
    get_azure_config,
    get_language_config,
)
from .azure import synthesize

__all__ = [
    "AZURE_TTS",
    "AZURE_TTS_LANG_MAPPING",
    "LANGUAGE_OPTIONS",
    "default_voice",
    "get_azure_config",
    "get_language_config",
    "synthesize",
]
