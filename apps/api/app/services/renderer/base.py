"""渲染后端抽象基类。

把「驱动数字人开口」这一步抽象成可切换接口：
- convai     : UE5 + MetaHuman，后端调 Convai REST API 驱动（默认，3D 数字人）
- livetalking: 旧 2D talking-head（LiveTalking /human），保留作降级 / 对照

所有后端必须保证：不可达 / 报错 / 未配置 → 返回 degraded=True，绝不抛异常、
不阻塞 /say、/answer 主链路（沿用 services/livetalking/client.py 的降级范式）。
返回结构统一为 {ok, degraded, latency_ms, url, detail}，前端 LiveTalkingState 零改动。
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any


def make_result(
    ok: bool,
    degraded: bool,
    latency_ms: int,
    url: str,
    detail: str,
    audio: str | None = None,
) -> dict[str, Any]:
    """统一的渲染结果结构（与前端 LiveTalkingState 一一对应）。

    audio：verbatim 后端（unreal）合成的 Azure TTS 音频（mp3 base64），
    前端经 Pixel Streaming datachannel 发 UE 驱动口型；livetalking 后端为 None（它自己出声）。
    """
    result: dict[str, Any] = {
        "ok": ok,
        "degraded": degraded,
        "latency_ms": latency_ms,
        "url": url,
        "detail": detail,
    }
    if audio is not None:
        result["audio"] = audio
    return result


class RendererClient(ABC):
    """数字人渲染后端的统一接口。"""

    #: 当前后端标识（convai / livetalking），供 health / 日志区分
    backend: str = "abstract"

    @property
    @abstractmethod
    def base_url(self) -> str:
        """对外暴露的服务地址（诊断展示用，如 Convai API 根、LiveTalking 根）。"""

    @abstractmethod
    async def health(self) -> bool:
        """探测后端是否可达。不可达返回 False，不抛异常。"""

    @abstractmethod
    async def speak(
        self,
        session_id: str | None,
        text: str,
        voice: str | None = None,
        interrupt: bool = False,
    ) -> dict[str, Any]:
        """让数字人播报一段文本。不可达 / 报错一律降级返回，绝不抛异常。"""

    @staticmethod
    def elapsed_ms(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)
