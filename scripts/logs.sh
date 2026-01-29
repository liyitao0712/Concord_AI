#!/bin/bash

# Concord AI - 日志查看脚本
# 用法:
#   ./scripts/logs.sh          # 查看所有服务日志
#   ./scripts/logs.sh postgres # 只看 PostgreSQL 日志
#   ./scripts/logs.sh redis    # 只看 Redis 日志

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

SERVICE=$1

if [ -z "$SERVICE" ]; then
    echo "查看所有服务日志 (按 Ctrl+C 退出)..."
    docker-compose logs -f
else
    echo "查看 $SERVICE 日志 (按 Ctrl+C 退出)..."
    docker-compose logs -f "$SERVICE"
fi
