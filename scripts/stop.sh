#!/usr/bin/env bash
# 停止 SynLive 后端栈（保留数据 volume）。
#   --purge  连同数据 volume 一起删除（慎用，会清空数据库/向量库/对象存储）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
( cd "$ROOT/infra" && \
  if [ "${1:-}" = "--purge" ]; then
    docker compose down -v
  else
    docker compose down
  fi )
