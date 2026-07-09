"""LiveTalking 异步客户端（优雅降级）。

LiveTalking 是独立运行的数字人渲染服务（需 NVIDIA GPU + CUDA）。
本机（Mac）通常跑不起来，因此所有调用都要保证：
- 连接失败 / 超时 / 未配置 → 返回 degraded=True，绝不抛异常，不阻塞 /say 主链路。
- 真正在 GPU 机器上跑起来时，degraded 转 False。

LiveTalking 说话流程（经运行中的镜像源码 app.py 核实）：
  1. 浏览器 POST /offer (WebRTC SDP) <-> answer SDP，建立音视频流（前端直连，不经本后端）
  2. POST /human {text, type:"echo"} -> 直接 TTS+口型渲染（不走 LLM）
注意：本镜像版本的 /human 是「无会话」的——它把文本丢进全局渲染器 nerfreal，
任何一次 /human 都会驱动当前已连上的数字人；/offer 也不返回 sessionid。
所以本客户端不再要求 sessionid（旧实现因此永远降级，是 bug）。session_id 形参保留仅做前向兼容。
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

        本镜像的 /human 无会话、只读 {type, text}；session_id 与 voice 形参保留做前向兼容，
        当前版本不使用。不可达 / 报错 一律降级返回，绝不抛异常。
        """
        start = time.perf_counter()

        if not settings.livetalking_enabled:
            return _result(False, True, 0, "livetalking disabled by config")

        # /human 是无会话的：只要 LiveTalking 在跑、且有浏览器经 /offer 连上数字人，
        # 这次���用就会驱动它开口。session_id 仅在新版（若返回 sessionid）时透传。
        payload: dict[str, Any] = {
            "text": text,
            "type": "echo",
            "interrupt": interrupt,
        }
        if session_id:
            payload["sessionid"] = session_id

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
