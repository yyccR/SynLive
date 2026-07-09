"""直播 Session 路由：创建 / 查询 / 播报（LLM + LiveTalking 编排）。

/say 编排：直接驱动 LiveTalking /human（它自己做 azure TTS + 口型渲染，音视频经 WebRTC 回浏览器）。
/answer 编排：问题 → LLM(数字人主播 persona) → LiveTalking /human 开口。

不再在 speak 路径上做后端 Azure TTS：旧实现合成后丢弃音频（LiveTalking 会自己 TTS），
既浪费配额又让 tts_latency_ms 指标失真。后端 TTS 仅保留在 /api/v1/tts/synthesize（独立试听）。
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, HTTPException
from loguru import logger

from ...core.config import settings
from ...schemas.live import (
    AnswerRequest,
    AnswerResponse,
    SayRequest,
    SayResponse,
    SessionCreateRequest,
)
from ...services.live.sessions import session_store
from ...services.livetalking.client import livetalking_client
from ...services.llm import DEFAULT_PERSONA_SYSTEM_PROMPT
from ...services.llm.chat import complete_litellm_chat

router = APIRouter(prefix="/live/sessions", tags=["live"])


@router.post("")
async def create_session(req: SessionCreateRequest) -> dict:
    session = session_store.create(req.title, req.avatar, req.voice)
    logger.info(f"[live] session created: id={session.id} title={session.title}")
    return session_store.to_dict(session)


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return session_store.to_dict(session)


@router.put("/{session_id}/livetalking-session")
async def bind_livetalking_session(session_id: str, livetalking_session_id: str) -> dict:
    """前端经 /offer 拿到 LiveTalking sessionid 后回填绑定。"""
    if not session_store.set_livetalking_session(session_id, livetalking_session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return {"session_id": session_id, "livetalking_session_id": livetalking_session_id}


@router.post("/{session_id}/say", response_model=SayResponse)
async def say(session_id: str, req: SayRequest) -> SayResponse:
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    # 驱动数字人渲染：LiveTalking /human 自己做 TTS+口型，音视频经 WebRTC 回浏览器。
    lt_sid = req.livetalking_session_id or session.livetalking_session_id
    livetalking = await livetalking_client.speak(lt_sid, req.text, req.voice, req.interrupt)

    return SayResponse(
        session_id=session_id,
        text=req.text,
        livetalking=livetalking,
    )


@router.post("/{session_id}/answer", response_model=AnswerResponse)
async def answer(session_id: str, req: AnswerRequest) -> AnswerResponse:
    """弹幕问答编排：问题 → LLM(数字人主播 persona) → TTS → LiveTalking。

    这是数字人"会回答问题"的核心链路。RAG 启用后，把检索到的资料放进 req.context，
    即可让回答基于知识库（不必改本函数）。
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    model_id = req.model_id or settings.llm_default_model_id

    # 人设 + 可选参考资料（RAG 注入口）
    system_prompt = req.system_prompt.strip() or DEFAULT_PERSONA_SYSTEM_PROMPT
    if req.context:
        system_prompt = (
            system_prompt
            + "\n\n参考资料（请优先基于以下信息回答，超出范围请如实说明）：\n"
            + req.context.strip()
        )

    # 1) LLM 生成回答（litellm.completion 是同步阻塞，丢线程池，避免卡事件循环）
    llm_start = time.perf_counter()
    try:
        result = await asyncio.to_thread(
            complete_litellm_chat,
            model_id=model_id,
            messages=[{"role": "user", "content": req.question}],
            system_prompt=system_prompt,
            max_tokens=req.max_tokens,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    llm_latency_ms = int((time.perf_counter() - llm_start) * 1000)
    answer_text = result["content"]

    # 2) 可选：驱动数字人开口（LiveTalking 自己 TTS+渲染，音视频经 WebRTC）
    livetalking: dict | None = None
    if req.speak and answer_text:
        livetalking = await livetalking_client.speak(
            session.livetalking_session_id, answer_text, req.voice
        )

    return AnswerResponse(
        session_id=session_id,
        question=req.question,
        answer=answer_text,
        model_id=result["model_id"],
        llm_latency_ms=llm_latency_ms,
        livetalking=livetalking,
    )
