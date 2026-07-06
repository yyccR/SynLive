# LiveTalking 部署说明（GPU 机器）

LiveTalking 是开源实时数字人渲染引擎（[lipku/LiveTalking](https://github.com/lipku/LiveTalking)），**需要 NVIDIA GPU + CUDA**，所以本机（Mac）跑不起来，部署到 Linux GPU 机器或云 GPU。

## 关键事实（已核实源码 main 分支）

- **自带 Azure TTS 插件**（`tts/azure.py`，注册名 `azuretts`），读环境变量 `AZURE_SPEECH_KEY` / `AZURE_TTS_REGION`。**无需自研插件**，与本后端共用同一把 Azure Key 即可。
- **说话接口**：`POST /human`，body `{"sessionid","text","type":"echo","interrupt":false}`。`type:"echo"` = 直接 TTS+口型渲染（不走 LLM）。
- **建立会话**：先 `POST /offer`（WebRTC SDP offer）→ 返回 `sessionid`（UUID）。没有有效 session 时 `/human` 返回 `session not found`。
- **TTS 选择**：通过启动参数 `--tts azuretts`（或 `config.yaml` 的 `tts:` 字段），**没有 `TTS=` 环境变量**。
- **端口**：HTTP 8010；WebRTC 需�� UDP 大范围端口。

## 启动方式

官方仓库**没有 docker-compose**，推荐用预构建镜像 `docker run`：

```bash
# tag 为阿里云不透明哈希，部署前从 README / codewithgpu 取最新 tag
docker run --gpus all -it --network=host --rm \
  -e AZURE_SPEECH_KEY=<你的 Azure Key> \
  -e AZURE_TTS_REGION=eastasia \
  -v $(pwd)/models:/livetalking/checkpoints \
  -v $(pwd)/data:/livetalking/data \
  registry.cn-beijing.aliyuncs.com/codewithgpu2/lipku-metahuman-stream:<latest-tag> \
  python app.py --model musetalk --tts azuretts
```

`infra/docker-compose.yml` 里的 `livetalking` 服务（`--profile gpu`）做了等价封装：

```bash
cd infra
# 把 AZURE_SERVICE_KEY 填进 .env（与 apps/api 共用），再：
docker compose --profile gpu up -d livetalking
```

> 镜像 tag 与启动命令随版本会变，部署时按当时官方文档确认 `LIVETALKING_IMAGE_TAG` 与 `app.py` 参数后，在 compose 里调整。

## 与本后端的联通

1. LiveTalking 起来后，前端浏览器对它做 WebRTC `/offer`，拿到 `sessionid`。
2. 前端把 `sessionid` 回传给本后端：`PUT /api/v1/live/sessions/{id}/livetalking-session?livetalking_session_id=<sid>`。
3. 之后 `POST /api/v1/live/sessions/{id}/say {text}` → 本后端先 Azure TTS，再调 LiveTalking `/human` 驱动渲染，`livetalking.degraded` 由 `true` 变 `false`。

## 备选：自定义 TTS 插件

若不想让 LiveTalking 直连 Azure（例如要走本后端统一计费/审计），可仿照 `tts/edge.py` 写一个 `BaseTTS` 子类，在 `txt_to_audio(msg)` 里 HTTP 调用本后端 `POST /api/v1/tts/synthesize`，把返回 mp3 解码成 16kHz mono float32 切成 20ms 帧后 `self.parent.put_audio_frame(...)` 推送。需在 `avatars/base_avatar.py` 的 `_tts_modules` 注册并 `--tts <name>` 启用。本阶段不实现，留待有需要时做。
