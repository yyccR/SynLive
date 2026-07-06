"""LLM 请求/响应 Schema。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="system / user / assistant")
    content: Any = Field(..., description="文本字符串或 multimodal 内容数组")


class ChatRequest(BaseModel):
    model_id: str | None = Field(None, description="留空用默认模型 llm-gpt")
    messages: list[ChatMessage] = Field(..., min_length=1)
    system_prompt: str = ""
    max_tokens: int | None = Field(None, ge=1, le=32768)
    temperature: float | None = Field(None, ge=0.0, le=2.0)


class ChatResponse(BaseModel):
    content: str
    model_id: str
    model: str
    provider: str
    latency_ms: int


class ModelItem(BaseModel):
    id: str
    provider: str
    name: str
    model: str
    description: str
    supports_images: bool
