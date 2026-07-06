#!/usr/bin/env bash
# ============================================================================
# 在 GPU 机器上一键部署 LiveTalking（数字人渲染节点）。
# 前置：NVIDIA GPU + CUDA、docker、nvidia-container-toolkit（--gpus 可用）。
#
# 它会：
#   1) 拉取 LiveTalking 预构建镜像
#   2) 用 LiveTalking 自带 azuretts 插件（与本后端共用同一把 Azure Key）
#   3) 渲染画面推流 RTMP 到 SynLive 的 SRS（可选，见 SRS_HOST）
#   4) 暴露 HTTP :8010 供 SynLive 后��调用 /human
#
# 用法示例：
#   1) 在脚本同目录新建 .env 填 AZURE_SPEECH_KEY=... 等，然后直接 ./deploy-livetalking.sh
#   2) 或命令行临时传：AZURE_SPEECH_KEY=xxxx SRS_HOST=1.2.3.4 ./deploy-livetalking.sh
#
# 跨机接入：部署起来后，在 SynLive 后端的 .env 设
#   LIVETALKING_URL=http://<本机IP>:8010
# 浏览器看画面：http://<SynLive主机>:8080/live/avatar.flv （经 SRS 中转）
# ============================================================================
set -euo pipefail

# 自动加载脚本同目录的 .env（把 AZURE_SPEECH_KEY 等填进去即可）
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.env"
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
AZURE_KEY="${AZURE_SPEECH_KEY:-${AZURE_SERVICE_KEY:-}}"
AZURE_REGION="${AZURE_TTS_REGION:-${AZURE_SERVICE_REGION:-eastasia}}"
IMAGE_TAG="${LIVETALKING_IMAGE_TAG:-latest}"
IMAGE="${LIVETALKING_IMAGE:-registry.cn-beijing.aliyuncs.com/codewithgpu2/lipku-metahuman-stream:${IMAGE_TAG}}"
SRS_HOST="${SRS_HOST:-}"                                      # 填了就推流到 rtmp://SRS_HOST:1935/live/avatar
MODELS_DIR="${MODELS_DIR:-$PWD/livetalking-models}"
DATA_DIR="${DATA_DIR:-$PWD/livetalking-data}"
CONTAINER="${CONTAINER:-livetalking}"

echo "$(c_dim '== 前置检查 ==')"
[ -n "$AZURE_KEY" ] || { echo "$(c_red '请提供 AZURE_SPEECH_KEY（或 AZURE_SERVICE_KEY）')"; exit 1; }
command -v docker >/dev/null || { echo "$(c_red '未安装 docker')"; exit 1; }
if ! docker run --rm --gpus all busybox true >/dev/null 2>&1; then
  echo "$(c_red 'GPU 或 nvidia-container-toolkit 不可用（--gpus all 失败）')"
  echo "$(c_yel '  安装：https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html')"
  exit 1
fi
echo "$(c_grn 'GPU 可用 ✔')"

echo "$(c_dim '== 准备目录 ==')"
mkdir -p "$MODELS_DIR" "$DATA_DIR"

echo "$(c_dim '== 拉取镜像（首次较大，请耐心）==')"
docker pull "$IMAGE"

# ---- 启动命令 ----
# 注意：不同 LiveTalking 版本，app.py 的参数/路径可能略有差异。
# 若镜像 entrypoint 已是启动命令，改用 LIVETALKING_CMD 覆盖；或改 config.yaml。
CMD="${LIVETALKING_CMD:-python app.py --model ${MODEL} --tts ${TTS}}"
if [ -n "$SRS_HOST" ]; then
  # 推流到 SynLive 的 SRS，浏览器经 SRS 低延迟观看，无需开 UDP/WebRTC 给浏览器
  CMD="$CMD --publish_url rtmp://${SRS_HOST}:1935/live/avatar"
fi

echo "$(c_dim '== 启动 LiveTalking ==')"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
eval "docker run -d --name ${CONTAINER} --gpus all --network=host \
  --restart unless-stopped \
  -e AZURE_SPEECH_KEY='${AZURE_KEY}' \
  -e AZURE_TTS_REGION='${AZURE_REGION}' \
  -v '${MODELS_DIR}':/livetalking/checkpoints \
  -v '${DATA_DIR}':/livetalking/data \
  '${IMAGE}' ${CMD}"

sleep 3
echo
echo "$(c_grn '== 部署完成 ==')"
echo "  本机 LiveTalking HTTP : http://<本机IP>:8010"
echo "  日志                   : docker logs -f ${CONTAINER}"
echo
echo "$(c_yel '在 SynLive 后端 .env 设置（跨机接入）：')"
echo "  LIVETALKING_URL=http://<本机IP>:8010"
[ -n "$SRS_HOST" ] && echo "$(c_yel '浏览器观看（经 SRS）：http://<SynLive主机>:8080/live/avatar.flv')"
echo
echo "$(c_dim '提示：app.py 参数 / --publish_url / 镜像 tag 随版本可能变化，')"
echo "$(c_dim '      若启动失败，查 docker logs 后按当时官方文档微调 LIVETALKING_CMD。')"
