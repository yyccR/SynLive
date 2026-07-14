"""LiveTalking 渲染后端（旧 2D talking-head，保留作降级 / 对照）。

逻辑从 services/livetalking/client.py 迁移，行为不变：
POST {livetalking_url}/human {text, type:"echo"} → LiveTalking 内部 azure TTS + 口型渲染，
音视频经 WebRTC 回浏览器。该镜像 /human 无会话、只读 {type, text}。
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from ...core.config import settings
from .base import RendererClient, make_result


class LiveTalkingRenderer(RendererClient):
    backend = "livetalking"

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self._url = (base_url or settings.livetalking_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.livetalking_timeout

    @property
    def base_url(self) -> str:
        return self._url

    async def health(self) -> bool:
        """探测 LiveTalking 是否可达。不可达返回 False，不抛异常。"""
        if not settings.livetalking_enabled:
            return False
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._url}/")
            logger.debug(
                f"[LiveTalking] health status={resp.status_code} in "
                f"{int((time.perf_counter() - start) * 1000)}ms"
            )
            return resp.status_code < 500
        except Exception as exc:
            logger.warning(f"[LiveTalking] health unreachable: {exc}")
            return False

    async def speak(
        self,
        session_id: str | None,
        text: str,
        voice: str | None = None,
        interrupt: bool = False,
    ) -> dict[str, Any]:
        """让数字人播报一段文本（type=echo，直接 TTS+渲染，不走 LLM）。

        /human 无会话、只读 {type, text}；session_id / voice 形参保留做前向兼容。
        不可达 / 报错一律降级返回，绝不抛异常。
        """
        start = time.perf_counter()

        if not settings.livetalking_enabled:
            return make_result(False, True, 0, self._url, "livetalking disabled by config")

        payload: dict[str, Any] = {
            "text": text,
            "type": "echo",
            "interrupt": interrupt,
        }
        if session_id:
            payload["sessionid"] = session_id

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._url}/human", json=payload)
            latency_ms = self.elapsed_ms(start)

            if resp.status_code != 200:
                return make_result(
                    False,
                    True,
                    latency_ms,
                    self._url,
                    f"HTTP {resp.status_code}: {resp.text[:160]}",
                )

            data = resp.json()
            if data.get("code", 0) == 0:
                logger.info(
                    f"[LiveTalking] speak ok: session={session_id} "
                    f"len={len(text)} in {latency_ms}ms"
                )
                return make_result(True, False, latency_ms, self._url, "ok")
            return make_result(
                False,
                True,
                latency_ms,
                self._url,
                f"livetalking error: {data.get('msg')}",
            )
        except Exception as exc:
            latency_ms = self.elapsed_ms(start)
            logger.warning(f"[LiveTalking] speak degraded: {exc}")
            return make_result(False, True, latency_ms, self._url, f"unreachable: {exc}")
