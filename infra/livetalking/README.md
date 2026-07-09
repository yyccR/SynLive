# LiveTalking 部署说明（GPU 机器）

LiveTalking 是开源实时数字人渲染引擎（[lipku/LiveTalking](https://github.com/lipku/LiveTalking)），**需要 NVIDIA GPU + CUDA**，本机（Mac）跑不起来，部署到 Linux GPU 机器或云 GPU。

## 关键事实（按当前固定镜像 codewithgpu `vjo1Y6NJ3N` 核实 app.py）

> ⚠ 这些事实是针对**当前固定 tag** 的镜像核实的，与 LiveTalking 官方 main 分支有出入（main 有 azure 插件、/human 带 sessionid）。换 tag 后需重新核实。

- **TTS**：该镜像 `ttsreal.py` 只支持 `edgetts` / `gpt-sovits` / `xtts`，**没有 azure 插件**。但 **`edgetts` 已废**——微软封了 edge-tts 硬编码的 `TrustedClientToken`，`edge_tts.Communicate().stream()` 持续返回 **403**（实测走代理也救不了），导致点播放无声、嘴不动。本项目改用**注入的 AzureTTS**：`infra/livetalking/ttsreal_azure.py`（走 REST、复用 `AZURE_SPEECH_KEY`、输出 `riff-16khz-16bit-mono-pcm`），由 `deploy-livetalking.sh` 挂载 + `patch-tts-azure.sh` 给 `musereal.py` 幂等注入 `--tts azure` 分支。默认 `--tts azure`，回退 `--tts edgetts` 会 403。可选音色：容器内 `AZURE_TTS_VOICE`（默认 `zh-CN-XiaoxiaoNeural`）。
- **说话接口**：`POST /human`，body `{"type":"echo","text":"..."}`。`type:"echo"` = 直接 TTS+口型渲染。**该版本 /human 不读 sessionid**——文本直接丢进全局渲染器 `nerfreal`，任何一次调用都驱动当前连上的数字人。
- **建立画面**：浏览器 `POST /offer`（WebRTC SDP offer）→ 返回 `{sdp, type}` answer（**不返回 sessionid**）。浏览器拿到 answer 建立 WebRTC，拉到数字人音视频流。
- **transport**：`app.py --transport` 决定媒体去向。默认 `rtcpush` 会去连 SRS 的 WHIP（`localhost:1985`），**SRS 没起时 aiohttp 会假死（8028 端口开着但不响应任何请求）**。浏览器直连预览务必用 `--transport webrtc`。
- **端口**：HTTP/信令/控制都在 `--listenport`（默认 8028）；老的 gevent WS 被 sed 改到 8029 避让，不用管。WebRTC 媒体还需一段 UDP（如 30000-65535）。

## 启动方式

官方仓库没有 docker-compose，用预构建镜像 `docker run`。已封装在 `scripts/deploy-livetalking.sh`（自动读根目录 `.env`，注入 Azure key 别名、修端口、注入播放页）：

```bash
# 1) 根目录 .env 填 AZURE_SPEECH_KEY（与 SynLive 共用同一把 key）
# 2) 一键部署（默认 MODEL=musetalk TTS=azure TRANSPORT=webrtc LT_PORT=8028）
./scripts/deploy-livetalking.sh
```

等价的 `docker run`（手动）：

```bash
docker run -d --name livetalking --gpus all --network=host --restart unless-stopped \
  -e AZURE_SPEECH_KEY=<你的 Azure Key> -e AZURE_TTS_REGION=eastasia \
  -v $PWD/infra/livetalking/ttsreal_azure.py:/root/metahuman-stream/ttsreal_azure.py:ro \
  -v $PWD/infra/livetalking/patch-tts-azure.sh:/root/metahuman-stream/patch-tts-azure.sh:ro \
  registry.cn-beijing.aliyuncs.com/codewithgpu2/lipku-metahuman-stream:<tag> \
  bash -c "source /root/miniconda3/etc/profile.d/conda.sh; conda activate base; \
    cd /root/metahuman-stream && sed -i 's/, 8000), app/, 8029), app/' app.py && \
    bash patch-tts-azure.sh && \
    python app.py --model musetalk --tts azure --transport webrtc --listenport 8028"
```

`infra/docker-compose.yml` 里的 `livetalking` 服务（`--profile gpu`）做了类似封装，但**单机直连预览推荐用上面的 `deploy-livetalking.sh`**（compose 版默认 transport 走 rtcpush 会假死，需自行覆盖命令）。

> 镜像 tag 与启动命令随版本会变。若启动失败，看 `docker logs livetalking`，并用 `.env` 里的 `LIVETALKING_IMAGE_TAG` / `LIVETALKING_CMD` 覆盖。

## 与本后端的联通

1. LiveTalking 起来后（`curl -X POST :8028/human -d '{"type":"echo","text":"你好"}'` 返回 `{"code":0}` 即正常）。
2. 浏览器对它做 WebRTC `/offer`，拿到 answer 后建立音视频流（前端 `live-console.tsx` 已实现）。
3. 用户点「让数字人说 / 提问」→ SynLive 后端 `POST /api/v1/live/sessions/{id}/say|/answer` → 后端调 LiveTalking `/human` → 数字人开口，音视频经同一条 WebRTC 流回浏览器。

后端访问 LiveTalking 用 `LIVETALKING_URL=http://host.docker.internal:8028`（api 容器经 `host-gateway` 访问 host 网络的 LiveTalking）；浏览器访问 LiveTalking 用 `http://<机器IP>:8028`（同主机名，前端按 `window.location.hostname` 自动推断）。
