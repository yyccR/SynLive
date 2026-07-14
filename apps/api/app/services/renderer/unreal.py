"""UE5 + Pixel Streaming 渲染后端（3D 数字人，默认，verbatim 模式）。

驱动方式（verbatim，逐字复述）：本后端用 Azure TTS 合成文本的**精确音频（mp3）**，
base64 返回给前端；前端经 Pixel Streaming datachannel（emitUIInteraction）把音频发给 UE，
UE 侧（RuntimeAudioImporter 插件）解码成 USoundWave → audio component 播放 + OVRLipSync 驱动
MetaHuman 口型；音频再经 Pixel Streaming 回传浏览器。

为什么 verbatim（Azure TTS）而非 Convai Invoke Speech：Convai 的 Invoke Speech 把文本当 context
喂给它自己的 LLM 再回应（非逐字复述），不适合 SynLive 的精确播报/客服场景。Azure TTS 是标准 TTS、
逐字精确，且 SynLive 后端已有该能力。代价：UE 侧需接 lipsync（OVRLipSync）+ 运行时音频解码
（RuntimeAudioImporter）——见 infra/docs/pixel-streaming-deploy.md。

POC 限制：emitUIInteraction 走文本 datachannel，单条消息有大小限制（~16KB），适合短播报；
长文本后续可改 Pixel Streaming 的 audio input（mic）通道或分片。
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

from loguru import logger

from ...core.config import settings
from ...services.tts import config as tts_config
from ...services.tts.azure import synthesize
from .base import RendererClient, make_result


class UnrealRenderer(RendererClient):
    backend = "unreal"

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        # ue_render_url 在 verbatim 模式下不用于驱动（驱动是 Azure 音频），仅作占位/诊断。
        self._url = (base_url or settings.ue_render_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.ue_render_timeout

    @property
    def base_url(self) -> str:
        return self._url

    async def health(self) -> bool:
        # verbatim/datachannel 模式：后端不直连 UE（音频由前端发），始终视为就绪。
        # UE 可达性由前端 Pixel Streaming 连接状态体现，不由后端探测。
        return True

    async def speak(
        self,
        session_id: str | None,
        text: str,
        voice: str | None = None,
        interrupt: bool = False,
    ) -> dict[str, Any]:
        """verbatim：Azure TTS 合成精确音频（mp3），base64 返回给前端发 UE。"""
        start = time.perf_counter()

        voice_id = voice or tts_config.default_voice("zh") or "zh-CN-XiaoxiaoNeural"
        # synthesize 用 requests 同步阻塞，丢线程池避免卡事件循环
        audio_bytes, err = await asyncio.to_thread(synthesize, text, "zh", voice_id)
        latency_ms = self.elapsed_ms(start)

        if err or not audio_bytes:
            logger.warning(f"[Unreal] azure tts failed: {err}")
            return make_result(False, True, latency_ms, "azure", f"tts: {err}")

        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        logger.info(
            f"[Unreal] speak synthesized: session={session_id} len={len(text)} "
            f"bytes={len(audio_bytes)} in {latency_ms}ms"
        )
        return make_result(True, False, latency_ms, "azure", "ok", audio=audio_b64)
