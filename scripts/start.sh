#!/bin/bash

# Concord AI - 启动脚本
# 用法: ./scripts/start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  启动 Concord AI"
echo "=========================================="

# 1. 启动 Docker 容器
echo ""
echo "[1/3] 启动 Docker 容器..."
docker-compose up -d

# 等待容器健康
echo "等待容器就绪..."
sleep 3

# 检查容器状态
if ! docker-compose ps | grep -q "healthy"; then
    echo "警告: 部分容器可能尚未就绪"
    docker-compose ps
fi

# 2. 激活虚拟环境
echo ""
echo "[2/3] 激活虚拟环境..."
cd backend

if [ ! -d "venv" ]; then
    echo "错误: 未找到虚拟环境，请先运行 ./scripts/setup.sh"
    exit 1
fi

source venv/bin/activate

# 3. 启动 FastAPI 服务
echo ""
echo "[3/3] 启动 FastAPI 服务..."
echo ""
echo "=========================================="
echo "  服务地址: http://localhost:8000"
echo "  API 文档: http://localhost:8000/docs"
echo "  按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
