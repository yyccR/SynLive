#!/usr/bin/env bash
# ============================================================================
# 在一台机器（GPU 机/服务器）上一键部署【整套 SynLive】：
#   后端栈（postgres/redis/qdrant/minio/srs/api）+ 前端(web) + Caddy 反代(:8018)
# 浏览器只需访问 http://<本机IP>:8018  （/api 经反代到后端，同源免 CORS）
#
# LiveTalking 单独用 deploy-livetalking.sh 部署（--network=host，本脚本会让
# 后端通过 host.docker.internal:8010 访问它）。
#
# 用法：
#   1) 在脚本同目录新建 .env 填 AZURE_SERVICE_KEY / LITELLM_LLM_API_KEY（可选 ACCESS_HOST）
#   2) ./deploy-full.sh
# ============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 自动加载脚本同目录 .env
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.env"
[ -f "$ENV_FILE" ] && { set -a; source "$ENV_FILE"; set +a; }

c_red() { printf '\033[31m%s\033[0m' "$1"; }
c_grn() { printf '\033[32m%s\033[0m' "$1"; }
c_yel() { printf '\033[33m%s\033[0m' "$1"; }
c_dim() { printf '\033[2m%s\033[0m' "$1"; }

ACCESS_PORT="${ACCESS_PORT:-8018}"
# 推断本机可达 IP（用户可 ACCESS_HOST=... 覆盖）
if [ -z "${ACCESS_HOST:-}" ]; then
  ACCESS_HOST="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi
ACCESS_HOST="${ACCESS_HOST:-127.0.0.1}"

echo "$(c_dim '== 检查 docker ==')"
command -v docker >/dev/null || { echo "$(c_red '未安装 docker')"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "$(c_red 'docker compose 不可用')"; exit 1; }

# 写入/更新某个 .env 的键值（已有非空值则跳过，除非 FORCE=1）
set_kv() {
  local file="$1" key="$2" val="$3"
  [ -z "$val" ] && return 0
  if grep -q "^${key}=" "$file"; then
    local cur; cur="$(grep "^${key}=" "$file" | head -1 | cut -d= -f2-)"
    [ -n "$cur" ] && [ "${FORCE:-0}" != 1 ] && return 0
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$file" && rm -f "${file}.bak"
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
}

echo "$(c_dim '== 生成并填充 .env ==')"
[ -f apps/api/.env ] || cp apps/api/.env.example apps/api/.env
[ -f infra/.env ] || cp infra/.env.example infra/.env
set_kv apps/api/.env AZURE_SERVICE_KEY "${AZURE_SERVICE_KEY:-}"
set_kv apps/api/.env LITELLM_LLM_API_KEY "${LITELLM_LLM_API_KEY:-}"
set_kv apps/api/.env AZURE_SERVICE_REGION "${AZURE_SERVICE_REGION:-eastasia}"
# 同源访问，CORS 放宽到访问入口（保险）
set_kv apps/api/.env CORS_ORIGINS "http://${ACCESS_HOST}:${ACCESS_PORT},http://localhost:${ACCESS_PORT},http://localhost:3000"
# 后端经 host-gateway 访问宿主机上的 LiveTalking
FORCE=1 set_kv infra/.env LIVETALKING_URL "http://host.docker.internal:8010"
FORCE=1 set_kv infra/.env ACCESS_PORT "$ACCESS_PORT"

echo "$(c_dim '== 构建并启动整套服务（首次会构建 api + 前端镜像，请耐心）==')"
( cd infra && docker compose up -d --build )

echo "$(c_dim '== 等待反代 :8018 就绪 ==')"
ok=0
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${ACCESS_PORT}/health" >/dev/null 2>&1; then ok=1; break; fi
  sleep 1
done
[ "$ok" = 1 ] && echo "$(c_grn '服务就绪 ✔')" || echo "$(c_red '未就绪，查看：cd infra && docker compose logs proxy api')"

echo
echo "$(c_dim '== 服务状态 ==')"
( cd infra && docker compose ps --format 'table {{.Service}}\t{{.Status}}' ) || true

echo
echo "$(c_grn '==================== 部署完成 ====================')"
echo "  浏览器打开 : http://${ACCESS_HOST}:${ACCESS_PORT}/app/live"
echo "  API 文档    : http://${ACCESS_HOST}:${ACCESS_PORT}/docs"
echo "$(c_yel '若密钥未填：编辑 apps/api/.env 填 AZURE_SERVICE_KEY / LITELLM_LLM_API_KEY 后')"
echo "$(c_yel '           cd infra && docker compose up -d api 重启 api。')"
echo
echo "$(c_dim '下一步：部署 LiveTalking（host 网络）让数字人真正开口/动嘴：')"
echo "$(c_dim '  AZURE_SPEECH_KEY=xxx ./deploy-livetalking.sh')"
echo "$(c_dim '（LiveTalking 起来后，后端会自动经 host.docker.internal:8010 接上，无需改配置）')"
