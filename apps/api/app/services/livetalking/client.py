"""LiveTalking 异步客户端（优雅降级）。

LiveTalking 是独立运行的数字人渲染服务（需 NVIDIA GPU + CUDA）。
本机（Mac）通常跑不起来，因此所有调用都要保证：
- 连接失败 / 超时 / 未配置 → 返回 degraded=True，绝不抛异常，不阻塞 /say 主链路。
- 真正在 GPU 机器上跑起来时，degraded 转 False。

LiveTalking 说话流程（经源码核实）：
  1. POST /offer  (WebRTC SDP)  -> 拿到 sessionid（由前端/浏览器建立 WebRTC）
  2. POST /human  {sessionid, text, type:"echo"}  -> 直接 TTS+口型渲染（不走 LLM）
其中 sessionid 由调用方传入（前端从 /offer 拿到后回传）。本地无 sessionid 时降级。
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from ...core.config import settings


def _result(ok: bool, degraded: bool, latency_ms: int, detail: str) -> dict[str, Any]:
    return {
        "ok": ok,
        "degraded": degraded,
        "latency_ms": latency_ms,
        "url": settings.livetalking_url,
        "detail": detail,
    }


class LiveTalkingClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.livetalking_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.livetalking_timeout

    async def health(self) -> bool:
        """探测 LiveTalking 是否可达。不可达返回 False，不抛异常。"""
        if not settings.livetalking_enabled:
            return False
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.base_url}/")
            logger.debug(
                f"[LiveTalking] health status={resp.status_code} "
                f"in {int((time.perf_counter() - start) * 1000)}ms"
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

        无 session_id / 不可达 / 报错 一律降级返回，绝不抛异常。
        """
        start = time.perf_counter()

        if not settings.livetalking_enabled:
            return _result(False, True, 0, "livetalking disabled by config")

        if not session_id:
            return _result(
                False,
                True,
                int((time.perf_counter() - start) * 1000),
                "no livetalking session_id（前端需先经 /offer 建立 WebRTC 会话）",
            )

        payload: dict[str, Any] = {
            "sessionid": session_id,
            "text": text,
            "type": "echo",
            "interrupt": interrupt,
        }
        if voice:
            # LiveTalking azuretts / edge 等插件约定从 datainfo['tts']['ref_file'] 读音色
            payload["tts"] = {"ref_file": voice}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/human", json=payload)
            latency_ms = int((time.perf_counter() - start) * 1000)

            if resp.status_code != 200:
                return _result(
                    False,
                    True,
                    latency_ms,
                    f"HTTP {resp.status_code}: {resp.text[:160]}",
                )

            data = resp.json()
            if data.get("code", 0) == 0:
                logger.info(
                    f"[LiveTalking] speak ok: session={session_id} "
                    f"len={len(text)} in {latency_ms}ms"
                )
                return _result(True, False, latency_ms, "ok")
            return _result(
                False,
                True,
                latency_ms,
                f"livetalking error: {data.get('msg')}",
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning(f"[LiveTalking] speak degraded: {exc}")
            return _result(False, True, latency_ms, f"unreachable: {exc}")


livetalking_client = LiveTalkingClient()
