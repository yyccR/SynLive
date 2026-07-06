"""直播 Session 路由：创建 / 查询 / 播报（TTS + LiveTalking 编排）。

/say 编排：
  1. 校验 session 与文本
  2. 计时调用 Azure TTS → 拿到 mp3（记录 tts_latency_ms）
  3. 调用 LiveTalking /human（本机不可达时优雅降级，不抛异常）
  4. 返回 SayResponse（含延迟指标与 LiveTalking 状态）
"""

from __future__ import annotations

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
from ...services.tts import config as tts_config
from ...services.tts.azure import synthesize

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

    lang = req.lang or session.lang
    voice = req.voice or session.voice or tts_config.default_voice(lang)
    if not voice:
        raise HTTPException(status_code=400, detail=f"语言 {lang} 无可用音色")

    # 1) TTS（本地可完整验证：Azure 是云端合成）
    tts_start = time.perf_counter()
    audio, tts_err = synthesize(req.text, lang, voice)
    tts_latency_ms = int((time.perf_counter() - tts_start) * 1000)
    if tts_err or not audio:
        logger.error(f"[live] tts failed: session={session_id} err={tts_err}")
        raise HTTPException(status_code=502, detail=f"tts failed: {tts_err}")

    # 2) 驱动数字人渲染（本机无 GPU 时降级，不影响上面的 TTS）
    lt_sid = req.livetalking_session_id or session.livetalking_session_id
    livetalking = await livetalking_client.speak(lt_sid, req.text, voice, req.interrupt)

    return SayResponse(
        session_id=session_id,
        text=req.text,
        tts_latency_ms=tts_latency_ms,
        audio_bytes=len(audio),
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

    # 1) LLM 生成回答
    llm_start = time.perf_counter()
    try:
        result = complete_litellm_chat(
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

    # 2) 可选：TTS + LiveTalking 播报
    tts_latency_ms: int | None = None
    audio_bytes: int | None = None
    livetalking: dict | None = None
    if req.speak and answer_text:
        lang = req.lang or session.lang
        voice = req.voice or session.voice or tts_config.default_voice(lang)
        if not voice:
            raise HTTPException(status_code=400, detail=f"语言 {lang} 无可用音色")

        tts_start = time.perf_counter()
        audio, tts_err = synthesize(answer_text, lang, voice)
        tts_latency_ms = int((time.perf_counter() - tts_start) * 1000)
        if tts_err or not audio:
            logger.error(f"[live] answer tts failed: session={session_id} err={tts_err}")
            raise HTTPException(status_code=502, detail=f"tts failed: {tts_err}")
        audio_bytes = len(audio)

        livetalking = await livetalking_client.speak(
            session.livetalking_session_id, answer_text, voice
        )

    return AnswerResponse(
        session_id=session_id,
        question=req.question,
        answer=answer_text,
        model_id=result["model_id"],
        llm_latency_ms=llm_latency_ms,
        tts_latency_ms=tts_latency_ms,
        audio_bytes=audio_bytes,
        livetalking=livetalking,
    )
