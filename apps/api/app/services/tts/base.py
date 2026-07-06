"""TTS Adapter 协议。

后续接入 CosyVoice / GPT-SoVITS / 云厂商时，各自实现该协议，路由层按配置选择。
当前唯一实现是 Azure（services/tts/azure.py 的 synthesize）。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSAdapter(Protocol):
    provider: str

    def synthesize(
        self,
        text: str,
        lang: str,
        voice: str,
        rate_pct: int = 0,
        pitch_pct: int = 0,
        volume: int = 50,
    ) -> tuple[bytes | None, str | None]:
        """返回 (audio_bytes, error)，成功时 error 为 None。"""
        ...
