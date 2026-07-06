"""TTS 请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="要合成的文本")
    lang: str = Field("zh", description="语言短代码 zh/en/...")
    voice: str | None = Field(None, description="Azure 音色名；为空时取该语言第一个")
    rate_pct: int = Field(0, ge=-100, le=100, description="语速百分比，0 为正常")
    pitch_pct: int = Field(0, ge=-100, le=100, description="语调百分比，0 为正常")
    volume: int = Field(50, ge=0, le=100, description="音量 0~100")


class VoiceItem(BaseModel):
    id: str
    name: str
    gender: str


class LanguageItem(BaseModel):
    code: str
    label: str
