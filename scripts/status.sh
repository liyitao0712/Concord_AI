#!/bin/bash

# Concord AI - 状态查看脚本
# 用法: ./scripts/status.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - 服务状态"
echo "=========================================="

echo ""
echo "Docker 容器:"
echo "------------------------------------------"
docker-compose ps

echo ""
echo "端口占用:"
echo "------------------------------------------"
echo "  PostgreSQL: 5432"
echo "  Redis:      6379"
echo "  FastAPI:    8000"

echo ""
echo "健康检查:"
echo "------------------------------------------"

# 检查 FastAPI
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  FastAPI:    运行中"
else
    echo "  FastAPI:    未运行"
fi

# 检查 PostgreSQL
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "  PostgreSQL: 运行中"
else
    echo "  PostgreSQL: 未运行"
fi

# 检查 Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo "  Redis:      运行中"
else
    echo "  Redis:      未运行"
fi

echo ""
