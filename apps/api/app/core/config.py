"""全局配置：统一从 .env 读取（pydantic-settings）。

本阶段只用到 Azure TTS 与 LiveTalking；DB / Redis / Qdrant / MinIO 的连接串先
占位，留给后续阶段（ASR/LLM/RAG/资产落盘）启用，避免来回改 .env。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "SynLive API"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # --- Azure TTS（与 LiveTalking azuretts 插件共用同一把 Key）---
    azure_service_key: str = ""
    azure_service_region: str = "eastasia"

    # --- LiveTalking ---
    # 本地（无 GPU）不真正渲染，会优雅降级；GPU 机器上指向 LiveTalking 服务
    livetalking_enabled: bool = True
    livetalking_url: str = "http://livetalking:8010"
    livetalking_timeout: float = 8.0

    # --- LLM（LiteLLM 网关，移植自 seo_video_generate）---
    # env 变量名沿用源项目约定（LITELLM_LLM_API_KEY / LITELLM_LLM_BASE_URL）
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "LITELLM_LLM_API_KEY"),
    )
    llm_base_url: str = Field(
        default="https://litellm.zuzuche.com/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "LITELLM_LLM_BASE_URL"),
    )
    # 默认模型 id（llm-gpt / llm-deepseek / llm-gemini / llm-doubao）
    llm_default_model_id: str = "llm-gpt"
    llm_max_output_tokens: int = 8192
    llm_request_timeout: int = 120

    # --- 基础设施（后续阶段使用，先占位）---
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+psycopg://synlive:synlive@localhost:5432/synlive"
    qdrant_url: str = "http://localhost:6333"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
