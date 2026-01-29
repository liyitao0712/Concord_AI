#!/bin/bash

# Concord AI - 停止脚本
# 用法: ./scripts/stop.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  停止 Concord AI"
echo "=========================================="

# 停止 Docker 容器
echo ""
echo "停止 Docker 容器..."
docker-compose down

echo ""
echo "所有服务已停止。"
