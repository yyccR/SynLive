#!/usr/bin/env bash
# SynLive 一键启动：拉起后端 docker 栈（postgres/redis/qdrant/minio/srs/api）
# 可选：--with-frontend 顺带启动 Next.js 前端（:3000）
#
# 密钥注入：若调用前在 shell 里 export 了 AZURE_SERVICE_KEY / LITELLM_LLM_API_KEY，
# 脚本会自动写进 apps/api/.env；否则请手动编辑该文件填入。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

c_red() { printf '\033[31m%s\033[0m' "$1"; }
c_grn() { printf '\033[32m%s\033[0m' "$1"; }
c_yel() { printf '\033[33m%s\033[0m' "$1"; }
c_dim() { printf '\033[2m%s\033[0m' "$1"; }

WITH_FRONTEND=0
[ "${1:-}" = "--with-frontend" ] && WITH_FRONTEND=1

echo "$(c_dim '== 检查 docker ==')"
command -v docker >/dev/null || { echo "$(c_red '未安装 docker，请先安装 Docker Desktop')"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "$(c_red 'docker compose 不可用')"; exit 1; }

ensure_env() {
  local target="$1" example="$2"
  if [ ! -f "$target" ]; then
    cp "$example" "$target"
    echo "$(c_dim "已生成 $target（来自 $example）")"
  fi
}
echo "$(c_dim '== 生成 .env（如缺失）==')"
ensure_env "apps/api/.env" "apps/api/.env.example"
ensure_env "infra/.env" "infra/.env.example"

# 把 shell 里的密钥写进 .env（仅当该行值为空时填充）
set_kv() {
  local file="$1" key="$2" val="$3"
  [ -z "$val" ] && return 0
  if grep -q "^${key}=" "$file"; then
    local cur
    cur="$(grep "^${key}=" "$file" | head -1 | cut -d= -f2-)"
    [ -n "$cur" ] && return 0   # 已有值，不覆盖
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$file" && rm -f "${file}.bak"
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
}
echo "$(c_dim '== 注入密钥（若环境变量已提供）==')"
set_kv "apps/api/.env" "AZURE_SERVICE_KEY" "${AZURE_SERVICE_KEY:-}"
set_kv "apps/api/.env" "LITELLM_LLM_API_KEY" "${LITELLM_LLM_API_KEY:-}"
set_kv "infra/.env" "AZURE_SERVICE_KEY" "${AZURE_SERVICE_KEY:-}"

echo "$(c_dim '== 启动后端 docker 栈 ==')"
( cd infra && docker compose up -d postgres redis qdrant minio srs api )

echo "$(c_dim '== 等待 API 就绪 ==')"
ok=0
for _ in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then ok=1; break; fi
  sleep 1
done
[ "$ok" = 1 ] && echo "$(c_grn 'API 已就绪 ✔')" || echo "$(c_red 'API 未在 40s 内就绪，查看：cd infra && docker compose logs api')"

echo
echo "$(c_dim '== 服务状态 ==')"
( cd infra && docker compose ps --format 'table {{.Service}}\t{{.Status}}' ) || true

echo
echo "$(c_grn '== 入口 ==')"
echo "  API 文档   : http://localhost:8000/docs"
echo "  健康检查   : http://localhost:8000/health/ready"
echo "  MinIO 控制台: http://localhost:9001  (minioadmin/minioadmin)"
echo "  Qdrant 面板 : http://localhost:6333/dashboard"

# 密钥校验
if ! grep -q "^AZURE_SERVICE_KEY=.\+" apps/api/.env; then
  echo "$(c_yel '⚠ apps/api/.env 里 AZURE_SERVICE_KEY 为空，TTS 不可用，请手动填入。')"
fi
if ! grep -q "^LITELLM_LLM_API_KEY=.\+" apps/api/.env; then
  echo "$(c_yel '⚠ apps/api/.env 里 LITELLM_LLM_API_KEY 为空，LLM 不可用，请手动填入。')"
fi

if [ "$WITH_FRONTEND" = 1 ]; then
  echo "$(c_dim '== 启动前端 (:3000) ==')"
  [ -d node_modules ] || npm install
  nohup npm run dev > /tmp/synlive_web.log 2>&1 &
  echo "  前端日志: /tmp/synlive_web.log"
  echo "  打开: http://localhost:3000/app/live"
else
  echo "$(c_dim '前端（另开终端）：npm run dev → http://localhost:3000/app/live')"
fi
