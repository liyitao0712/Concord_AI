#!/bin/bash

# Concord AI - 状态查看脚本
# 用法: ./scripts/status.sh
#
# 显示所有服务的运行状态：
# - Docker 容器（PostgreSQL、Redis、Temporal、Temporal UI、Celery）
# - FastAPI 后端
# - Temporal Worker
# - Next.js 前端

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - 服务状态"
echo "=========================================="

# Docker 容器状态
echo ""
echo "Docker 容器:"
echo "------------------------------------------"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps

# 端口占用
echo ""
echo "端口映射:"
echo "------------------------------------------"
echo "  PostgreSQL:  5432"
echo "  Redis:       6379"
echo "  Temporal:    7233"
echo "  Temporal UI: 8080"
echo "  Flower:      5555 (Celery 监控，需启动)"
echo "  FastAPI:     8000"
echo "  Frontend:    3000"

# 健康检查
echo ""
echo "健康检查:"
echo "------------------------------------------"

# 检查 PostgreSQL
if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "  PostgreSQL:     [运行中]"
else
    echo "  PostgreSQL:     [未运行]"
fi

# 检查 Redis
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "  Redis:          [运行中]"
else
    echo "  Redis:          [未运行]"
fi

# 检查 Temporal
if docker compose exec -T temporal sh -c 'temporal operator cluster health --address $(hostname -i):7233' > /dev/null 2>&1; then
    echo "  Temporal:       [运行中]"
else
    echo "  Temporal:       [未运行/启动中]"
fi

# 检查 Temporal UI
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "  Temporal UI:    [运行中] http://localhost:8080"
else
    echo "  Temporal UI:    [未运行]"
fi

# 检查 Celery 服务（本地运行）
CELERY_STATUS=$(./scripts/celery.sh status 2>&1)

# 检查 Celery Beat
if echo "$CELERY_STATUS" | grep -q "Celery Beat:.*运行中"; then
    BEAT_PID=$(echo "$CELERY_STATUS" | grep "Celery Beat" | grep -o "PID: [0-9]*" | cut -d' ' -f2)
    echo "  Celery Beat:    [运行中] (PID: $BEAT_PID)"
else
    echo "  Celery Beat:    [未运行] (定时调度器)"
fi

# 检查 Celery Worker
if echo "$CELERY_STATUS" | grep -q "Celery Worker:.*运行中"; then
    WORKER_PID=$(echo "$CELERY_STATUS" | grep "Celery Worker" | grep -o "PID: [0-9]*" | cut -d' ' -f2)
    echo "  Celery Worker:  [运行中] (PID: $WORKER_PID)"
else
    echo "  Celery Worker:  [未运行] (任务执行器)"
fi

# 检查 Flower（可选）
if echo "$CELERY_STATUS" | grep -q "Flower:.*运行中"; then
    FLOWER_PID=$(echo "$CELERY_STATUS" | grep "Flower" | grep -o "PID: [0-9]*" | cut -d' ' -f2)
    echo "  Flower:         [运行中] http://localhost:5555 (PID: $FLOWER_PID)"
elif curl -s http://localhost:5555 > /dev/null 2>&1; then
    echo "  Flower:         [运行中] http://localhost:5555"
else
    echo "  Flower:         [未运行] (可选，监控面板)"
fi

# 检查 FastAPI
FASTAPI_PID=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$FASTAPI_PID" ]; then
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  FastAPI:        [运行中] http://localhost:8000 (PID: $FASTAPI_PID)"
    else
        echo "  FastAPI:        [端口占用但无响应] (PID: $FASTAPI_PID)"
    fi
else
    echo "  FastAPI:        [未运行]"
fi

# 检查 Temporal Worker
WORKER_PID=$(pgrep -f "app.workflows.worker" 2>/dev/null || true)
if [ -n "$WORKER_PID" ]; then
    echo "  Temporal Worker:[运行中] (PID: $WORKER_PID)"
else
    echo "  Temporal Worker:[未运行]"
fi


# 检查前端
FRONTEND_PID=$(lsof -ti :3000 2>/dev/null || true)
if [ -n "$FRONTEND_PID" ]; then
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "  Frontend:       [运行中] http://localhost:3000 (PID: $FRONTEND_PID)"
    else
        echo "  Frontend:       [启动中] (PID: $FRONTEND_PID)"
    fi
else
    echo "  Frontend:       [未运行]"
fi

# 日志文件
echo ""
echo "日志文件:"
echo "------------------------------------------"
if [ -d "logs" ]; then
    ls -la logs/*.log 2>/dev/null || echo "  暂无日志文件"
else
    echo "  logs 目录不存在"
fi

echo ""
echo "提示:"
echo "  - 启动服务: ./scripts/start.sh"
echo "  - 停止服务: ./scripts/stop.sh"
echo "  - 查看日志: ./scripts/logs.sh [服务名]"
echo "  - Celery 监控: docker-compose --profile monitoring up -d flower"
echo ""
