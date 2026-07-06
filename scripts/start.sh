#!/usr/bin/env bash
# SynLive 启动：拉起 docker 栈（后端 + 前端 + Caddy 反代）。
# 所有配置统一读【根目录 .env】（与 .env.example 同级）。
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
  echo "$(c_yel "已从 .env.example 生成 $ENV，请填好密钥后重跑。")"
fi
set -a; source "$ENV"; set +a

command -v docker >/dev/null || { echo "$(c_red '未安装 docker')"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "$(c_red 'docker compose 不可用')"; exit 1; }

ACCESS_PORT="${ACCESS_PORT:-8018}"

echo "$(c_dim '== 启动 docker 栈 ==')"
docker compose -f infra/docker-compose.yml --env-file .env up -d

echo "$(c_dim '== 等待反代就绪 ==')"
ok=0
for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:${ACCESS_PORT}/health" >/dev/null 2>&1 && { ok=1; break; }
  sleep 1
done
[ "$ok" = 1 ] && echo "$(c_grn '就绪 ✔')" || echo "$(c_red '未就绪：docker compose -f infra/docker-compose.yml logs proxy api')"

echo; echo "$(c_dim '== 服务状态 ==')"
docker compose -f infra/docker-compose.yml ps --format 'table {{.Service}}\t{{.Status}}' || true

echo; echo "$(c_grn '入口')"
echo "  前端 : http://localhost:${ACCESS_PORT}/app/live"
echo "  文档 : http://localhost:${ACCESS_PORT}/docs"

if ! grep -q "^AZURE_SERVICE_KEY=.\+" "$ENV" 2>/dev/null; then
  echo "$(c_yel '⚠ .env 里 AZURE_SERVICE_KEY 为空，TTS 不可用')"
fi
if ! grep -q "^LITELLM_LLM_API_KEY=.\+" "$ENV" 2>/dev/null; then
  echo "$(c_yel '⚠ .env 里 LITELLM_LLM_API_KEY 为空，LLM 不可用')"
fi
