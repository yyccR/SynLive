# SynLive API

AI 数字人直播中控平台后端（FastAPI）。本阶段已打通：**文本 → Azure TTS → mp3**，并提供直播 Session 编排接口 `/say`（TTS + LiveTalking，本机无 GPU 时 LiveTalking 自动降级）。

## 目录结构

```
app/
  main.py                 # FastAPI 入口（CORS / lifespan / 路由挂载）
  core/                   # config(pydantic-settings)、logging(loguru)
  api/v1/                 # health / tts / live 路由
  services/
    tts/                  # Azure TTS（移植自 seo_video_generate，已解耦 Django）
    livetalking/          # LiveTalking 异步客户端（优雅降级）
    live/                 # 直播 Session 管理器（内存版）
  schemas/                # 请求/响应模型
```

## 本地运行（无需 Docker）

```bash
cd apps/api
cp .env.example .env          # 填入 AZURE_SERVICE_KEY / AZURE_SERVICE_REGION
# 用项目根目录已有的 .venv（Python 3.13）
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

打开 http://localhost:8000/docs 看 Swagger。

## 接口速览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 存活检查 |
| GET | `/health/ready` | 就绪检查（Azure 是否配置、LiveTalking 地址） |
| GET | `/api/v1/tts/languages` | 16 种语言列表 |
| GET | `/api/v1/tts/voices?lang=zh` | 某语言音色列表 |
| POST | `/api/v1/tts/synthesize` | 文本 → mp3（响应体即音频） |
| GET | `/api/v1/llm/models` | 可用 LLM 列表（GPT/DeepSeek/Gemini/Doubao）+ 默认模型 |
| POST | `/api/v1/llm/chat` | 非流式对话（OpenAI messages 风格） |
| POST | `/api/v1/llm/chat/stream` | SSE 流式对话（meta→content…→done） |
| GET | `/api/v1/llm/persona` | 默认数字人主播人设 |
| POST | `/api/v1/live/sessions` | 创建直播会话 |
| GET | `/api/v1/live/sessions/{id}` | 查询会话 |
| PUT | `/api/v1/live/sessions/{id}/livetalking-session` | 绑定 LiveTalking sessionid |
| POST | `/api/v1/live/sessions/{id}/say` | 编排播报：TTS + 驱动数字人 |
| POST | `/api/v1/live/sessions/{id}/answer` | 弹幕问答编排：问题→LLM→TTS→数字人 |

## /say 编排流程

1. 校验 session、文本 → 计时调用 Azure TTS 得到 mp3（记录 `tts_latency_ms`）。
2. 调用 LiveTalking `POST /human {sessionid, text, type:"echo"}` 驱动渲染。
3. LiveTalking 不可达（本机无 GPU / 未启动）→ 返回 `livetalking.degraded=true`，**不抛异常、不阻塞 TTS 验证**。

## 配置（.env）

见 `.env.example`。关键项：

- `AZURE_SERVICE_KEY` / `AZURE_SERVICE_REGION`：Azure 语音凭据。
- `LIVETALKING_URL`：docker 内网 `http://livetalking:8010`；本地原生跑改 `http://localhost:8010`。
- `LIVETALKING_ENABLED=false`：完全跳过 LiveTalking 调用（不看降级日志）。

## 后续阶段

- 持久化：SQLAlchemy + Alembic（替换内存 Session 管理器）。
- 实时状态：Redis（直播状态、播报队列）。
- 知识库：Qdrant（向量检索）、MinIO（音频/模型资产）。
- 媒体：SRS（RTMP/WebRTC 预览与推流）。
- AI：ASR（FunASR）、LLM（OpenAI-compatible）、声线克隆（CosyVoice）。
