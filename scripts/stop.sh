#!/bin/bash

# Concord AI - 停止脚本
# 用法:
#   ./scripts/stop.sh         # 停止所有服务
#   ./scripts/stop.sh --keep  # 保留 Docker 容器，只停止应用
#
# 停止的服务：
# - FastAPI 后端（端口 8000）
# - Temporal Worker
# - Next.js 前端（端口 3000）
# - Celery Beat/Worker
# - Docker 容器

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 解析参数
KEEP_DOCKER=false

for arg in "$@"; do
    case $arg in
        --keep)
            KEEP_DOCKER=true
            ;;
    esac
done

echo "=========================================="
echo "  停止 Concord AI"
echo "=========================================="

# 1. 停止 FastAPI 服务
echo ""
echo "[1/4] 停止 FastAPI 服务..."

FASTAPI_PID=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$FASTAPI_PID" ]; then
    kill $FASTAPI_PID 2>/dev/null || true
    echo "  FastAPI 已停止 (PID: $FASTAPI_PID)"
else
    echo "  FastAPI 未运行"
fi

# 2. 停止 Temporal Worker
echo ""
echo "[2/4] 停止 Temporal Worker..."

WORKER_PID=$(pgrep -f "app.workflows.worker" 2>/dev/null || true)
if [ -n "$WORKER_PID" ]; then
    kill $WORKER_PID 2>/dev/null || true
    echo "  Temporal Worker 已停止 (PID: $WORKER_PID)"
else
    echo "  Temporal Worker 未运行"
fi

# 3. 停止前端
echo ""
echo "[3/4] 停止前端服务..."

FRONTEND_PID=$(lsof -ti :3000 2>/dev/null || true)
if [ -n "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null || true
    echo "  前端已停止 (PID: $FRONTEND_PID)"
else
    echo "  前端未运行"
fi

# 4. 停止 Celery 服务
echo ""
echo "[4/5] 停止 Celery 服务..."
./scripts/celery.sh stop > /dev/null 2>&1 || echo "  Celery 未运行"

# 5. 停止 Docker 容器
echo ""
echo "[5/5] 停止 Docker 容器..."

if [ "$KEEP_DOCKER" = true ]; then
    echo "  跳过（使用了 --keep 参数）"
else
    docker compose down
    echo "  Docker 容器已停止"
fi

echo ""
echo "=========================================="
echo "  所有服务已停止"
echo "=========================================="

if [ "$KEEP_DOCKER" = true ]; then
    echo ""
    echo "提示: Docker 容器仍在运行，使用以下命令停止："
    echo "      docker compose down"
fi
