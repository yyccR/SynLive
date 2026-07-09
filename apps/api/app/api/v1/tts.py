"""TTS 路由：语言/音色列表 + 文本合成（返回 mp3）。"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...schemas.tts import TTSRequest
from ...services.tts import config as tts_config
from ...services.tts.azure import synthesize

router = APIRouter(prefix="/tts", tags=["tts"])


@router.get("/languages")
async def list_languages() -> list[dict]:
    return tts_config.LANGUAGE_OPTIONS


@router.get("/voices")
async def list_voices(lang: str = Query("zh", description="语言短代码")) -> list[dict]:
    cfg = tts_config.get_language_config(lang)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"不支持的语言: {lang}")
    return cfg["voices"]


@router.post("/synthesize")
async def synthesize_tts(req: TTSRequest) -> Response:
    voice = req.voice or tts_config.default_voice(req.lang)
    if not voice:
        raise HTTPException(status_code=400, detail=f"语言 {req.lang} 无可用音色")

    start = time.perf_counter()
    # synthesize 用 requests 同步阻塞，丢线程池避免卡事件循环
    audio, err = await asyncio.to_thread(
        synthesize,
        req.text, req.lang, voice, req.rate_pct, req.pitch_pct, req.volume,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    if err:
        raise HTTPException(status_code=502, detail=err)

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "X-TTS-Latency-Ms": str(latency_ms),
            "Content-Disposition": 'inline; filename="tts.mp3"',
        },
    )
