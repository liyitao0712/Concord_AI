#!/bin/bash

# Concord AI - 重启脚本
# 用法:
#   ./scripts/restart.sh        # 重启所有服务（前台运行后端）
#   ./scripts/restart.sh --bg   # 所有服务后台运行
#   ./scripts/restart.sh --api  # 只重启后端 API
#   ./scripts/restart.sh --worker # 只重启 Temporal Worker
#   ./scripts/restart.sh --frontend # 只重启前端
#   ./scripts/restart.sh --celery # 只重启 Celery 服务
#
# 重启的服务：
# - Docker 容器（PostgreSQL、Redis、Temporal、Celery Beat/Worker）
# - FastAPI 后端（端口 8000）
# - Temporal Worker（处理工作流）
# - Next.js 前端（端口 3000）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 解析参数
RUN_MODE="all"
BACKGROUND=false

for arg in "$@"; do
    case $arg in
        --bg)
            BACKGROUND=true
            ;;
        --api)
            RUN_MODE="api"
            ;;
        --worker)
            RUN_MODE="worker"
            ;;
        --frontend)
            RUN_MODE="frontend"
            ;;
        --celery)
            RUN_MODE="celery"
            ;;
    esac
done

echo "=========================================="
echo "  重启 Concord AI"
echo "=========================================="

# 1. 停止 FastAPI 服务
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "api" ]; then
    echo ""
    echo "[1/6] 停止 FastAPI 服务..."

    FASTAPI_PID=$(lsof -ti :8000 2>/dev/null || true)
    if [ -n "$FASTAPI_PID" ]; then
        kill $FASTAPI_PID 2>/dev/null || true
        echo "  FastAPI 已停止 (PID: $FASTAPI_PID)"
        sleep 1
    else
        echo "  FastAPI 未运行"
    fi
fi

# 2. 停止 Temporal Worker
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "worker" ]; then
    echo ""
    echo "[2/6] 停止 Temporal Worker..."

    WORKER_PID=$(pgrep -f "app.workflows.worker" 2>/dev/null || true)
    if [ -n "$WORKER_PID" ]; then
        kill $WORKER_PID 2>/dev/null || true
        echo "  Temporal Worker 已停止 (PID: $WORKER_PID)"
        sleep 1
    else
        echo "  Temporal Worker 未运行"
    fi
fi

# 3. 停止前端
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "frontend" ]; then
    echo ""
    echo "[3/5] 停止前端服务..."

    FRONTEND_PID=$(lsof -ti :3000 2>/dev/null || true)
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo "  前端已停止 (PID: $FRONTEND_PID)"
        sleep 1
    else
        echo "  前端未运行"
    fi
fi

# 4. 重启 Docker 容器（包括 Celery）
if [ "$RUN_MODE" = "all" ]; then
    echo ""
    echo "[4/5] 重启 Docker 容器（包括 Celery Beat/Worker）..."
    docker compose down
    docker compose up -d

    # 等待容器就绪
    echo -n "  等待容器就绪"
    for i in {1..15}; do
        if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
            echo " 完成"
            break
        fi
        echo -n "."
        sleep 1
    done
fi

# 检查虚拟环境
if [ ! -d "backend/venv" ]; then
    echo "错误: 未找到虚拟环境，请先运行 ./scripts/setup.sh"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 4.5 重启 Celery（单独重启 Celery 时）
if [ "$RUN_MODE" = "celery" ]; then
    echo ""
    echo "重启 Celery 服务..."
    ./scripts/celery.sh restart
    echo ""
    echo "查看日志: ./scripts/celery.sh logs"
    exit 0
fi

# 更新后端依赖（确保新增的依赖被安装）
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "api" ]; then
    echo ""
    echo "[4.5/5] 更新后端依赖..."
    cd backend
    source venv/bin/activate
    pip install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt
    echo "  依赖更新完成"

    # 执行数据库迁移
    echo ""
    echo "[4.6/5] 检查数据库迁移..."
    if alembic current 2>/dev/null | grep -q "(head)"; then
        echo "  数据库已是最新版本"
    else
        echo "  执行待处理的迁移..."
        alembic upgrade head
        echo "  数据库迁移完成"
    fi
    cd "$PROJECT_ROOT"
fi

# 5. 启动 Temporal Worker
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "worker" ]; then
    echo ""
    echo "[5/5] 启动 Temporal Worker..."

    cd backend
    source venv/bin/activate
    nohup python -m app.workflows.worker > ../logs/worker.log 2>&1 &
    WORKER_PID=$!
    echo "  Temporal Worker 已启动 (PID: $WORKER_PID)"
    cd "$PROJECT_ROOT"
fi

# 6. 启动前端
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "frontend" ]; then
    echo ""
    echo "[6/6] 启动前端..."

    if [ -d "frontend" ] && command -v npm &> /dev/null; then
        cd frontend
        nohup npm run dev > ../logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo "  前端已启动 (PID: $FRONTEND_PID)"
        cd "$PROJECT_ROOT"
    else
        echo "  跳过（frontend 目录不存在或 npm 未安装）"
    fi
fi

# 7. 启动 FastAPI
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "api" ]; then
    echo ""
    echo "=========================================="
    echo "  服务地址"
    echo "=========================================="
    echo ""
    echo "  - 后端 API:    http://localhost:8000"
    echo "  - API 文档:    http://localhost:8000/docs"
    echo "  - 前端:        http://localhost:3000"
    echo "  - Temporal UI: http://localhost:8080"
    echo "  - Flower:      http://localhost:5555 (需启动)"
    echo ""

    cd backend
    source venv/bin/activate

    if [ "$BACKGROUND" = true ]; then
        nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../logs/api.log 2>&1 &
        API_PID=$!
        echo "  FastAPI 已后台启动 (PID: $API_PID)"
        echo ""
        echo "查看日志: tail -f logs/api.log"
        echo "停止服务: ./scripts/stop.sh"
    else
        echo "  按 Ctrl+C 停止服务"
        echo ""
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    fi
fi
