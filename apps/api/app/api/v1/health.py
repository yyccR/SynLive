"""健康检查路由。"""

from __future__ import annotations

from fastapi import APIRouter

from ...core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@router.get("/health/ready")
async def ready() -> dict:
    return {
        "status": "ok",
        "azure_configured": bool(settings.azure_service_key),
        "azure_region": settings.azure_service_region,
        "llm_configured": bool(settings.llm_api_key),
        "llm_default_model_id": settings.llm_default_model_id,
        "renderer_backend": settings.renderer_backend,
        "ue_render_url": settings.ue_render_url,
        # 旧 LiveTalking 字段保留（切回 livetalking 后端时用）
        "livetalking_enabled": settings.livetalking_enabled,
        "livetalking_url": settings.livetalking_url,
    }
