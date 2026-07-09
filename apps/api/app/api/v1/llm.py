"""LLM 路由：模型列表 + 非流式对话 + SSE 流式对话。"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from loguru import logger
from starlette.concurrency import iterate_in_threadpool

from ...core.config import settings
from ...schemas.llm import ChatRequest, ChatResponse
from ...services.llm import (
    DEFAULT_PERSONA_SYSTEM_PROMPT,
    complete_litellm_chat,
    list_litellm_models,
    stream_litellm_chat,
)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/models")
async def list_models() -> dict:
    return {
        "default_model_id": settings.llm_default_model_id,
        "models": list_litellm_models(),
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    model_id = req.model_id or settings.llm_default_model_id
    messages = [m.model_dump() for m in req.messages]
    start = time.perf_counter()
    try:
        # litellm.completion 同步阻塞，丢线程池避免卡事件循环
        result = await asyncio.to_thread(
            complete_litellm_chat,
            model_id=model_id,
            messages=messages,
            system_prompt=req.system_prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    latency_ms = int((time.perf_counter() - start) * 1000)
    return ChatResponse(latency_ms=latency_ms, **result)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    model_id = req.model_id or settings.llm_default_model_id
    messages = [m.model_dump() for m in req.messages]

    async def event_source():
        try:
            # stream_litellm_chat 是同步生成器（litellm.completion 阻塞），
            # 用 iterate_in_threadpool 在线程池里迭代，避免阻塞事件循环
            async for chunk in iterate_in_threadpool(
                stream_litellm_chat(
                    model_id=model_id,
                    messages=messages,
                    system_prompt=req.system_prompt,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                )
            ):
                yield chunk
        except Exception as exc:  # 兜底，避免生成器中途抛异常破坏 SSE
            logger.error(f"[LLM] stream generator error: {exc}")
            yield f"event: error\ndata: {{\"message\": \"流式生成异常: {str(exc)[:200]}\"}}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/persona")
async def default_persona() -> dict:
    """返回默认数字人主播人设，前端可基于此再编辑。"""
    return {"system_prompt": DEFAULT_PERSONA_SYSTEM_PROMPT}
