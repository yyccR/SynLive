"""渲染后端工厂：按 settings.renderer_backend 返回单例。

- unreal     : UE5 + MetaHuman + Pixel Streaming（默认，3D 数字人）。
               后端 POST 文本到 UE 工程的 HTTP 接口；驱动由 UE 侧 Convai 完成。
- livetalking: 旧 2D talking-head（LiveTalking /human），保留作降级 / 对照。

切换：在 .env 设 RENDERER_BACKEND=livetalking 即可回到旧 2D 链路（逃生通道）。
"""

from __future__ import annotations

from ...core.config import settings
from .base import RendererClient, make_result
from .livetalking import LiveTalkingRenderer
from .unreal import UnrealRenderer

__all__ = [
    "RendererClient",
    "make_result",
    "renderer_client",
    "get_renderer",
]


def get_renderer() -> RendererClient:
    backend = (settings.renderer_backend or "unreal").strip().lower()
    if backend == "livetalking":
        return LiveTalkingRenderer()
    if backend == "unreal":
        return UnrealRenderer()

    from loguru import logger

    logger.warning(f"[renderer] unknown renderer_backend={backend!r}, fallback to unreal")
    return UnrealRenderer()


# 模块级单例：settings 经 lru_cache 在进程启动时固定一次，backend 随之固定。
renderer_client: RendererClient = get_renderer()
