#!/bin/bash

# Concord AI - 重启脚本
# 用法: ./scripts/restart.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  重启 Concord AI"
echo "=========================================="

# 停止服务
echo ""
echo "[1/2] 停止服务..."
docker-compose down

# 启动服务
echo ""
echo "[2/2] 启动服务..."
docker-compose up -d

# 等待容器
sleep 3

echo ""
echo "Docker 容器已重启。"
docker-compose ps

echo ""
echo "如需启动 FastAPI 服务，请运行:"
echo "  cd backend && source venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
