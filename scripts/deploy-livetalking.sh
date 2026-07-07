#!/usr/bin/env bash
# ============================================================================
# 在 GPU 机器上一键部署 LiveTalking（数字人渲染节点）。
# 前置：NVIDIA GPU + CUDA、docker、nvidia-container-toolkit（--gpus 可用）。
#
# 用 codewithgpu 预构建镜像（自带代码与模型，位于 /root/metahuman-stream）：
#   - 用 LiveTalking 自带 azuretts 插件（与本后端共用同一把 Azure Key）
#   - 渲染画面可推流 RTMP 到 SynLive 的 SRS（可选，见 SRS_HOST）
#   - 暴露 HTTP :8010 供 SynLive 后端调用 /human
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
TTS="${TTS:-azuretts}"                                       # 用自带 Azure 插件
TRANSPORT="${TRANSPORT:-webrtc}"                             # webrtc(浏览器直连)/rtcpush(推 SRS)/virtualcam
AZURE_KEY="${AZURE_SPEECH_KEY:-${AZURE_SERVICE_KEY:-}}"
AZURE_REGION="${AZURE_TTS_REGION:-${AZURE_SERVICE_REGION:-eastasia}}"
# 镜像 tag 是不透明 commit hash（无 latest），随版本变；取官方文档当前值
IMAGE_TAG="${LIVETALKING_IMAGE_TAG:-vjo1Y6NJ3N}"
IMAGE="${LIVETALKING_IMAGE:-registry.cn-beijing.aliyuncs.com/codewithgpu2/lipku-metahuman-stream:${IMAGE_TAG}}"
SRS_HOST="${SRS_HOST:-}"                                      # 填了就推流到 rtmp://SRS_HOST:1935/live/avatar
# 对外端口：容器内 LiveTalking HTTP 固定 8000，这里映射到宿主机的对外端口（默认 8028，避开 SynLive 的 8000）
LT_PORT="${LIVETALKING_PORT:-8028}"
LT_WS_PORT="${LIVETALKING_WS_PORT:-8010}"
CONTAINER="${CONTAINER:-livetalking}"

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

if [ -n "${LIVETALKING_CMD:-}" ]; then
  # shellcheck disable=SC2086
  set -- ${LIVETALKING_CMD}
  docker run -d --name "$CONTAINER" --gpus all --network=host \
    --restart unless-stopped \
    -e AZURE_SPEECH_KEY="$AZURE_KEY" \
    -e AZURE_TTS_REGION="$AZURE_REGION" \
    "${EXTRA_VOLUMES[@]}" \
    "$IMAGE" "$@"
else
  docker run -d --name "$CONTAINER" --gpus all --network=host \
    --restart unless-stopped \
    -e AZURE_SPEECH_KEY="$AZURE_KEY" \
    -e AZURE_TTS_REGION="$AZURE_REGION" \
    "${EXTRA_VOLUMES[@]}" \
    "$IMAGE" \
    bash -c "source /root/miniconda3/etc/profile.d/conda.sh 2>/dev/null; conda activate base 2>/dev/null; cd /root/metahuman-stream && sed -i 's/, 8000), app/, ${LT_PORT}), app/' app.py && python app.py --model ${MODEL} --tts ${TTS}"
fi

sleep 3
echo
echo "$(c_grn '== 容器已启动，看日志确认服务起来 ==')"
echo "  ⭐ 网页/数字人画面/WebRTC/SynLive 控制 都在 TCP 8010（aiohttp：/offer、/human、静态页 web/，带 CORS）"
echo "     ${LT_PORT} 只是老的 WebSocket 端口，看画面用不到。"
echo "  本机访问 : http://localhost:8010/webrtcapi.html"
echo "  日志     : docker logs -f ${CONTAINER}"
echo
echo "$(c_yel '平台要开放的端口（WebRTC 看画面）:')"
echo "  TCP 8010（网页+信令+控制）、以及一段 UDP（WebRTC 媒体，如 30000-65535）"
echo
echo "$(c_yel 'SynLive 后端 .env（host 网络，同机）：')"
echo "  LIVETALKING_URL=http://host.docker.internal:8010"
[ -n "$SRS_HOST" ] && echo "$(c_yel '浏览器观看（经 SRS）：http://<SynLive主机>:8080/live/avatar.flv')"
echo
echo "$(c_dim '提示：app.py 参数 / 镜像 tag 随版本可能变化；若启动失败，')"
echo "$(c_dim '      看 docker logs 后按当时官方文档用 LIVETALKING_CMD / LIVETALKING_IMAGE_TAG 覆盖。')"
