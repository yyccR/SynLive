"""SynLive API 入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1 import health, live, llm, tts
from .core.config import settings
from .core.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI 数字人直播中控平台后端",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tts.router, prefix=settings.api_prefix)
app.include_router(llm.router, prefix=settings.api_prefix)
app.include_router(live.router, prefix=settings.api_prefix)


@app.get("/")
async def root() -> dict:
    return {"service": settings.app_name, "version": "0.1.0", "docs": "/docs", "health": "/health"}
