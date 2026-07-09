#!/usr/bin/env bash
# ============================================================================
# 在 GPU 机器上一键部署 LiveTalking（数字人渲染节点）。
# 前置：NVIDIA GPU + CUDA、docker、nvidia-container-toolkit（--gpus 可用）。
#
# 用 codewithgpu 预构建镜像（自带代码与模型，位于 /root/metahuman-stream）：
#   - 用 LiveTalking 自带 azuretts 插件（与本后端共用同一把 Azure Key）
#   - 渲染画面可推流 RTMP 到 SynLive 的 SRS（可选，见 SRS_HOST）
#   - 暴露 HTTP :8028 供浏览器 /offer(WebRTC)与 SynLive 后端 /human 调用
#   - transport=webrtc：浏览器经 /offer 直接拉取数字人音视频；rtcpush 会去连 SRS，
#     SRS 没起时 aiohttp 会假死（端口开着但不响应），单机直连预览务必用 webrtc
#
# 用法：
#   1) 在根目录 .env 填 AZURE_SPEECH_KEY 等（与 deploy-full.sh 同一个文件）
#   2) ./deploy-livetalking.sh
# ============================================================================
set -euo pipefail

# 自动加载【根目录 .env】（与部署脚本共用同一份配置）
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

c_red() { printf '\033[31m%s\033[0m' "$1"; }
c_grn() { printf '\033[32m%s\033[0m' "$1"; }
c_yel() { printf '\033[33m%s\033[0m' "$1"; }
c_dim() { printf '\033[2m%s\033[0m' "$1"; }

# ---- 可配置参数（环境变量覆盖）----
MODEL="${MODEL:-musetalk}"                                   # ernerf / musetalk / wav2lip
# 该镜像(codewithgpu vjo1Y6NJ3N)的 ttsreal.py 只有 edgetts / gpt-sovits / xtts，无 azure 插件。
# edgetts 因微软封 TrustedClientToken 持续 403（点播放无声、嘴不动，已实测代理也救不了），
# 改用我们注入的 AzureTTS（infra/livetalking/ttsreal_azure.py，走 REST、复用 AZURE_SPEECH_KEY）。
# 回退 edgetts 可设 TTS=edgetts，但会 403 无声。
TTS="${TTS:-azure}"
TRANSPORT="${TRANSPORT:-webrtc}"                             # webrtc(浏览器直连)/rtcpush(推 SRS)/virtualcam
# musetalk 推理批大小：每次 VAE decode batch_size 帧。镜像默认 16 在 24GB 卡(3090/4090)上 OOM
# （点播放渲染峰值 >18GB，VAE decode 16 帧激活撑爆，渲染子进程崩→画面卡在最后一帧）。
# 但开太小(batch_size=2)吞吐不足→嘴型跟不上音频→说话断续。8 是 24GB 卡的平衡点：
# 显存峰值约 3GB模型 + 8×0.9GB激活 ≈ 10GB（安全），吞吐又够 fps=50。≥40GB 卡可调回 16。
BATCH_SIZE="${BATCH_SIZE:-8}"

# 不同模型的 app.py 额外参数（musetalk 和 ernerf 的 batch_size 语义不同，不能一套通吃）：
#   ernerf：必须 -O（=--fp16 --cuda_ray --exp_eye），否则 NeRF 推理又慢显存又爆；
#           它的 batch_size 是 ray-batch 语义（单帧分块采样），用默认 16 即可，不要传。
#   musetalk/wav2lip：--batch_size 是帧批，默认 16 会 OOM，必须按 BATCH_SIZE 控。
if [ "$MODEL" = "ernerf" ]; then
  MODEL_ARGS="-O"
else
  MODEL_ARGS="--batch_size ${BATCH_SIZE}"
fi
AZURE_KEY="${AZURE_SPEECH_KEY:-${AZURE_SERVICE_KEY:-}}"
AZURE_REGION="${AZURE_TTS_REGION:-${AZURE_SERVICE_REGION:-eastasia}}"
# 镜像 tag 是不透明 commit hash（无 latest），随版本变；取官方文档当前值
IMAGE_TAG="${LIVETALKING_IMAGE_TAG:-vjo1Y6NJ3N}"
IMAGE="${LIVETALKING_IMAGE:-registry.cn-beijing.aliyuncs.com/codewithgpu2/lipku-metahuman-stream:${IMAGE_TAG}}"
SRS_HOST="${SRS_HOST:-}"                                      # 填了就推流到 rtmp://SRS_HOST:1935/live/avatar
# 端口：LiveTalking 有两个服务
#   LT_PORT   = aiohttp：网页 + /offer(WebRTC 视频) + /human(控制) + CORS —— 浏览器和 SynLive 都用这个（默认 8028）
#   LT_WS_PORT= gevent WSGI：老的 /humanecho WebSocket，没用，挪开避免和 SynLive 的 8000 冲突（默认 8029）
LT_PORT="${LIVETALKING_PORT:-8028}"
LT_WS_PORT="${LIVETALKING_WS_PORT:-8029}"
CONTAINER="${CONTAINER:-livetalking}"
# GPU：默认 all（落在 GPU0）。单机多卡时建议指定一张空闲卡，否则 musetalk 渲染
# 容易被同卡其它进程挤到 CUDA OOM（容器仍在、/human 照返回 code:0，但渲染/azure 已死）。
# 指定单卡用 GPU='"device=1"'（内层引号是 docker --gpus device= 形式的要求）。
GPU="${GPU:-all}"

echo "$(c_dim '== 前置检查 ==')"
[ -n "$AZURE_KEY" ] || { echo "$(c_red '请提供 AZURE_SPEECH_KEY（或 AZURE_SERVICE_KEY），写到根目录 .env')"; exit 1; }
command -v docker >/dev/null || { echo "$(c_red '未安装 docker')"; exit 1; }

# GPU 检查：优先用 REGISTRY 前缀的 busybox 探测（避免 Docker Hub 拉取失败误报）；
# 探测镜像拉不到时，退而检查 docker 是否已注册 nvidia runtime。两者皆无才报错。
gpu_ok=0
if docker run --rm --gpus all "${REGISTRY}busybox" true >/dev/null 2>&1; then
  gpu_ok=1
elif docker info --format '{{.Runtimes}}' 2>/dev/null | grep -q nvidia; then
  echo "$(c_yel '  提示：busybox 探测镜像未拉到，但检测到 nvidia runtime，视为 GPU 可用，继续。')"
  gpu_ok=1
fi
if [ "$gpu_ok" != 1 ]; then
  echo "$(c_red 'docker 无法使用 GPU（--gpus all 失败）')"
  echo "$(c_yel '  多半没装 nvidia-container-toolkit：')"
  echo "$(c_yel '  https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html')"
  exit 1
fi
echo "$(c_grn 'GPU 可用 ✔')"

echo "$(c_dim '== 拉取镜像（首次较大，请耐心）==')"
if ! docker pull "$IMAGE"; then
  echo "$(c_red "拉取失败：$IMAGE")"
  echo "$(c_yel '  LiveTalking 镜像 tag 是不透明 commit hash，会随版本变。')"
  echo "$(c_yel '  打开 https://livetalking-doc.readthedocs.io/en/latest/docker.html')"
  echo "$(c_yel '  复制 docker run 里 lipku-metahuman-stream:<tag> 的最新 tag，')"
  echo "$(c_yel "  在根目录 .env 设 LIVETALKING_IMAGE_TAG=<新tag> 后重跑本脚本。")"
  exit 1
fi

# ---- 启动命令 ----
# 镜像里代码在 /root/metahuman-stream，自带模型；进目录 git pull 更新后跑 app.py。
# 想完全自定义命令，在 .env 设 LIVETALKING_CMD="..."。
echo "$(c_dim '== 启动 LiveTalking ==')"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

PUBLISH=""
[ -n "$SRS_HOST" ] && PUBLISH="--publish_url rtmp://${SRS_HOST}:1935/live/avatar"

# 自定义模型/形象目录（可选）：设了才挂载，避免遮住镜像自带内容
EXTRA_VOLUMES=()
[ -n "${LIVETALKING_MODELS_DIR:-}" ] && EXTRA_VOLUMES+=(-v "${LIVETALKING_MODELS_DIR}:/root/metahuman-stream/checkpoints")
[ -n "${LIVETALKING_DATA_DIR:-}" ]   && EXTRA_VOLUMES+=(-v "${LIVETALKING_DATA_DIR}:/root/metahuman-stream/data")

# --tts azure 必需：挂载 AzureTTS 模块 + 幂等接线脚本(给 musereal.py 注入 azure 分支)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AZURE_TTS_FILE="${REPO_ROOT}/infra/livetalking/ttsreal_azure.py"
PATCH_FILE="${REPO_ROOT}/infra/livetalking/patch-tts-azure.sh"
if [ "${TTS}" = "azure" ]; then
  if [ -f "$AZURE_TTS_FILE" ] && [ -f "$PATCH_FILE" ]; then
    EXTRA_VOLUMES+=(-v "${AZURE_TTS_FILE}:/root/metahuman-stream/ttsreal_azure.py:ro")
    EXTRA_VOLUMES+=(-v "${PATCH_FILE}:/root/metahuman-stream/patch-tts-azure.sh:ro")
  else
    echo "$(c_red "  缺 $AZURE_TTS_FILE 或 $PATCH_FILE，--tts azure 不可用。改 TTS=edgetts(会 403)或补文件后重跑。")"
    exit 1
  fi
fi

if [ -n "${LIVETALKING_CMD:-}" ]; then
  # shellcheck disable=SC2086
  set -- ${LIVETALKING_CMD}
  docker run -d --name "$CONTAINER" --gpus "$GPU" --network=host \
    --restart unless-stopped \
    -e AZURE_SPEECH_KEY="$AZURE_KEY" \
    -e AZURE_TTS_REGION="$AZURE_REGION" \
    "${EXTRA_VOLUMES[@]}" \
    "$IMAGE" "$@"
else
  docker run -d --name "$CONTAINER" --gpus "$GPU" --network=host \
    --restart unless-stopped \
    -e AZURE_SPEECH_KEY="$AZURE_KEY" \
    -e AZURE_TTS_REGION="$AZURE_REGION" \
    "${EXTRA_VOLUMES[@]}" \
    "$IMAGE" \
    bash -c "source /root/miniconda3/etc/profile.d/conda.sh 2>/dev/null; conda activate base 2>/dev/null; cd /root/metahuman-stream && sed -i 's/, 8000), app/, ${LT_WS_PORT}), app/' app.py && { [ ! -f patch-tts-azure.sh ] || bash patch-tts-azure.sh; } && python -u app.py --model ${MODEL} --tts ${TTS} --transport ${TRANSPORT} ${MODEL_ARGS} --listenport ${LT_PORT}"
fi

sleep 3

# 注入 WebRTC 播放页到容器 web/（aiohttp 静态服务，与 /offer 同源，免 CORS）
VIEWER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lt-viewer.html"
if [ -f "$VIEWER" ]; then
  docker cp "$VIEWER" "$CONTAINER:/root/metahuman-stream/web/lt-viewer.html" >/dev/null 2>&1 \
    && echo "$(c_dim '  已注入播放页 lt-viewer.html（浏览器开 http://<IP>:')${LT_PORT}$(c_dim '/lt-viewer.html）')"
fi

echo
echo "$(c_grn '== 容器已启动（端口对应：SynLive=8018，LiveTalking=8028）==')"
echo "  ⭐ 数字人画面/网页/WebRTC/SynLive 控制 都在 TCP ${LT_PORT}（aiohttp：/offer、/human、静态页 web/，带 CORS）"
echo "     ${LT_WS_PORT} 是老的 WS 端口，避让用，不用管。"
echo "  浏览器看数字人 : http://<本机IP>:${LT_PORT}/lt-viewer.html"
echo "  本机自测      : http://localhost:${LT_PORT}/lt-viewer.html"
echo "  日志          : docker logs -f ${CONTAINER}"
echo
echo "$(c_yel '平台要开放的端口（WebRTC 看画面）:')"
echo "  TCP ${LT_PORT}（网页+信令+控制）、以及一段 UDP（WebRTC 媒体，如 30000-65535）"
echo
echo "$(c_yel 'SynLive 后端 .env（host 网络，同机）：')"
echo "  LIVETALKING_URL=http://host.docker.internal:${LT_PORT}"
[ -n "$SRS_HOST" ] && echo "$(c_yel '浏览器观看（经 SRS）：http://<SynLive主机>:8080/live/avatar.flv')"
echo
echo "$(c_dim '提示：app.py 参数 / 镜像 tag 随版本可能变化；若启动失败，')"
echo "$(c_dim '      看 docker logs 后按当时官方文档用 LIVETALKING_CMD / LIVETALKING_IMAGE_TAG 覆盖。')"
