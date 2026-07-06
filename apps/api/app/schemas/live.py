"""直播 Session 相关 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    title: str = "未命名直播"
    avatar: str | None = None
    voice: str | None = None


class SayRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    lang: str = "zh"
    voice: str | None = None
    interrupt: bool = False
    # 由前端在 /offer（WebRTC）拿到后回传；本地无 LiveTalking 时为空，/say 会降级
    livetalking_session_id: str | None = None


class SayResponse(BaseModel):
    session_id: str
    text: str
    tts_latency_ms: int
    audio_bytes: int
    livetalking: dict


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="观众/弹幕问题")
    model_id: str | None = None
    system_prompt: str = ""
    context: str | None = Field(None, description="可选参考资料（后续接 RAG 检索结果）")
    lang: str = "zh"
    voice: str | None = None
    max_tokens: int | None = Field(None, ge=1, le=32768)
    speak: bool = Field(True, description="是否把答案交给 TTS+LiveTalking 播报")


class AnswerResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    model_id: str
    llm_latency_ms: int
    tts_latency_ms: int | None
    audio_bytes: int | None
    livetalking: dict | None
