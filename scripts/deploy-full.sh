#!/usr/bin/env bash
# ============================================================================
# 在一台机器（GPU 机/服务器）上一键部署【整套 SynLive】：
#   后端栈（postgres/redis/qdrant/minio/api）+ 前端(web) + Caddy 反代(:ACCESS_PORT)
# 浏览器只需访问 http://<ACCESS_HOST>:<ACCESS_PORT>/app/live
# 所有配置统一读【根目录 .env】（与 .env.example 同级）。
# LiveTalking 用 deploy-livetalking.sh 单独部署（host 网络）。
# ============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

c_red() { printf '\033[31m%s\033[0m' "$1"; }
c_grn() { printf '\033[32m%s\033[0m' "$1"; }
c_yel() { printf '\033[33m%s\033[0m' "$1"; }
c_dim() { printf '\033[2m%s\033[0m' "$1"; }

ENV="$ROOT/.env"
if [ ! -f "$ENV" ]; then
  cp .env.example "$ENV" 2>/dev/null || true
  echo "$(c_red '未找到根目录 .env。已从 .env.example 生成一份，请编辑填好密钥后再运行：')"
  echo "  vi $ENV"
  exit 1
fi
set -a; source "$ENV"; set +a

command -v docker >/dev/null || { echo "$(c_red '未安装 docker')"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "$(c_red 'docker compose 不可用')"; exit 1; }

ACCESS_PORT="${ACCESS_PORT:-8018}"
[ -z "${ACCESS_HOST:-}" ] && ACCESS_HOST="$(hostname -I 2>/dev/null | awk '{print $1}')"
ACCESS_HOST="${ACCESS_HOST:-127.0.0.1}"

echo "$(c_dim '== 检查密钥 ==')"
miss=0
[ -n "${AZURE_SERVICE_KEY:-}" ] || { echo "$(c_yel '  ⚠ AZURE_SERVICE_KEY 未填 → TTS 不可用')"; miss=1; }
[ -n "${LITELLM_LLM_API_KEY:-}" ] || { echo "$(c_yel '  ⚠ LITELLM_LLM_API_KEY 未填 → LLM 不可用')"; miss=1; }

echo "$(c_dim '== 构建并启动整套服务（首次构建 api/前端镜像，请耐心）==')"
docker compose -f infra/docker-compose.yml --env-file .env up -d --build

echo "$(c_dim '== 等待反代就绪 ==')"
ok=0
for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${ACCESS_PORT}/health" >/dev/null 2>&1 && { ok=1; break; }
  sleep 1
done
[ "$ok" = 1 ] && echo "$(c_grn '服务就绪 ✔')" || echo "$(c_red '未就绪：docker compose -f infra/docker-compose.yml logs proxy api')"

echo; echo "$(c_dim '== 服务状态 ==')"
docker compose -f infra/docker-compose.yml ps --format 'table {{.Service}}\t{{.Status}}' || true

echo; echo "$(c_grn '==================== 部署完成 ====================')"
echo "  浏览器打开 : http://${ACCESS_HOST}:${ACCESS_PORT}/app/live"
echo "  API 文档    : http://${ACCESS_HOST}:${ACCESS_PORT}/docs"
echo "  就绪检查    : http://${ACCESS_HOST}:${ACCESS_PORT}/health/ready"
[ "$miss" = 1 ] && echo "$(c_yel '  密钥未填全：编辑根目录 .env 后重跑本脚本。')"
echo
echo "$(c_dim '下一步：起 LiveTalking（host 网络）让数字人动嘴：')"
echo "$(c_dim '  ./scripts/deploy-livetalking.sh   （AZURE_SPEECH_KEY 在同一个 .env）')"
