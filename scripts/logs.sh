#!/bin/bash

# Concord AI - 日志查看脚本
# 用法:
#   ./scripts/logs.sh              # 查看所有 Docker 服务日志
#   ./scripts/logs.sh postgres     # 只看 PostgreSQL 日志
#   ./scripts/logs.sh redis        # 只看 Redis 日志
#   ./scripts/logs.sh temporal     # 只看 Temporal Server 日志
#   ./scripts/logs.sh temporal-ui  # 只看 Temporal UI 日志
#   ./scripts/logs.sh celery-beat  # 只看 Celery Beat 日志
#   ./scripts/logs.sh celery-worker # 只看 Celery Worker 日志
#   ./scripts/logs.sh flower       # 只看 Flower 日志
#   ./scripts/logs.sh api          # 只看 FastAPI 日志
#   ./scripts/logs.sh worker       # 只看 Temporal Worker 日志
#   ./scripts/logs.sh frontend     # 只看前端日志
#   ./scripts/logs.sh all          # 查看所有应用日志

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

SERVICE=$1

case "$SERVICE" in
    "api")
        echo "查看 FastAPI 日志 (按 Ctrl+C 退出)..."
        if [ -f "logs/api.log" ]; then
            tail -f logs/api.log
        else
            echo "错误: logs/api.log 不存在"
            echo "提示: 使用 ./scripts/start.sh --bg 启动后台服务"
        fi
        ;;
    "worker")
        echo "查看 Temporal Worker 日志 (按 Ctrl+C 退出)..."
        if [ -f "logs/worker.log" ]; then
            tail -f logs/worker.log
        else
            echo "错误: logs/worker.log 不存在"
            echo "提示: 使用 ./scripts/start.sh 启动服务"
        fi
        ;;
    "frontend")
        echo "查看前端日志 (按 Ctrl+C 退出)..."
        if [ -f "logs/frontend.log" ]; then
            tail -f logs/frontend.log
        else
            echo "错误: logs/frontend.log 不存在"
            echo "提示: 使用 ./scripts/start.sh 启动服务"
        fi
        ;;
    "all")
        echo "查看所有应用日志 (按 Ctrl+C 退出)..."
        echo "=========================================="
        if [ -d "logs" ]; then
            tail -f logs/*.log 2>/dev/null || echo "暂无日志文件"
        else
            echo "logs 目录不存在"
        fi
        ;;
    "celery-beat")
        echo "查看 Celery Beat 日志 (按 Ctrl+C 退出)..."
        if [ -f "logs/celery-beat.log" ]; then
            tail -f logs/celery-beat.log
        else
            echo "日志文件不存在: logs/celery-beat.log"
            echo "请先启动 Celery: ./scripts/celery.sh start"
        fi
        ;;
    "celery-worker")
        echo "查看 Celery Worker 日志 (按 Ctrl+C 退出)..."
        if [ -f "logs/celery-worker.log" ]; then
            tail -f logs/celery-worker.log
        else
            echo "日志文件不存在: logs/celery-worker.log"
            echo "请先启动 Celery: ./scripts/celery.sh start"
        fi
        ;;
    "flower")
        echo "查看 Flower 日志 (按 Ctrl+C 退出)..."
        if [ -f "logs/celery-flower.log" ]; then
            tail -f logs/celery-flower.log
        else
            echo "日志文件不存在: logs/celery-flower.log"
            echo "请先启动 Flower: ./scripts/celery.sh flower"
        fi
        ;;
    "celery")
        echo "查看所有 Celery 服务日志 (按 Ctrl+C 退出)..."
        ./scripts/celery.sh logs
        ;;
    "postgres"|"redis"|"temporal"|"temporal-ui")
        echo "查看 $SERVICE 日志 (按 Ctrl+C 退出)..."
        docker compose logs -f "$SERVICE"
        ;;
    "")
        echo "查看所有 Docker 服务日志 (按 Ctrl+C 退出)..."
        docker compose logs -f
        ;;
    *)
        echo "用法: ./scripts/logs.sh [服务名]"
        echo ""
        echo "可用的服务名："
        echo "  Docker 服务："
        echo "    postgres      - PostgreSQL 数据库"
        echo "    redis         - Redis 缓存"
        echo "    temporal      - Temporal Server"
        echo "    temporal-ui   - Temporal Web UI"
        echo ""
        echo "  Celery 服务（本地）："
        echo "    celery-beat   - Celery Beat 定时调度器"
        echo "    celery-worker - Celery Worker 任务执行器"
        echo "    flower        - Celery 监控面板"
        echo "    celery        - 所有 Celery 服务"
        echo ""
        echo "  应用服务："
        echo "    api           - FastAPI 后端"
        echo "    worker        - Temporal Worker"
        echo "    frontend      - Next.js 前端"
        echo "    all           - 所有应用日志"
        echo ""
        echo "  不带参数则显示所有 Docker 服务日志"
        ;;
esac
