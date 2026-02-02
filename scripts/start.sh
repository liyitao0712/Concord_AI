#!/bin/bash

# Concord AI - 启动脚本
# 用法:
#   ./scripts/start.sh           # 启动所有服务（前台运行后端）
#   ./scripts/start.sh --bg      # 所有服务后台运行
#   ./scripts/start.sh --api     # 只启动后端 API
#   ./scripts/start.sh --worker  # 只启动 Temporal Worker
#   ./scripts/start.sh --frontend # 只启动前端
#
# 服务列表：
# - Docker 容器（PostgreSQL、Redis、Temporal、Temporal UI）
# - Celery Beat/Worker（邮件轮询、定时任务）
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
    esac
done

echo "=========================================="
echo "  启动 Concord AI"
echo "=========================================="

# 1. 启动 Docker 容器
echo ""
echo "[1/4] 启动 Docker 容器..."
docker compose up -d

# 等待容器就绪
echo -n "  等待容器就绪"
for i in {1..10}; do
    if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo " 完成"
        break
    fi
    echo -n "."
    sleep 1
done

# 2. 检查虚拟环境
if [ ! -d "backend/venv" ]; then
    echo "错误: 未找到虚拟环境，请先运行 ./scripts/setup.sh"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 2.5 更新后端依赖（确保新增的依赖被安装）
echo ""
echo "[2/5] 更新后端依赖..."
cd backend
source venv/bin/activate
pip install -r requirements.txt --quiet 2>/dev/null || pip install -r requirements.txt
echo "  依赖更新完成"

# 执行数据库迁移
echo ""
echo "[2.5/5] 检查数据库迁移..."
if alembic current 2>/dev/null | grep -q "(head)"; then
    echo "  数据库已是最新版本"
else
    echo "  执行待处理的迁移..."
    alembic upgrade head
    echo "  数据库迁移完成"
fi
cd "$PROJECT_ROOT"

# 2.7 启动 Celery 服务
if [ "$RUN_MODE" = "all" ]; then
    echo ""
    echo "[2.7/5] 启动 Celery 服务..."
    ./scripts/celery.sh start > /dev/null 2>&1 || {
        echo "  Celery 启动失败，请查看日志: logs/celery-*.log"
    }
fi

# 3. 启动服务
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "worker" ]; then
    echo ""
    echo "[2/4] 启动 Temporal Worker..."

    # 停止已有的 Worker
    WORKER_PID=$(pgrep -f "app.temporal.worker" 2>/dev/null || true)
    if [ -n "$WORKER_PID" ]; then
        kill $WORKER_PID 2>/dev/null || true
        sleep 1
    fi

    # 启动 Worker（后台运行）
    cd backend
    source venv/bin/activate
    nohup python -m app.temporal.worker > ../logs/worker.log 2>&1 &
    WORKER_PID=$!
    echo "  Temporal Worker 已启动 (PID: $WORKER_PID)"
    echo "  日志: logs/worker.log"
    cd "$PROJECT_ROOT"
fi

if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "frontend" ]; then
    echo ""
    echo "[3/4] 启动前端..."

    if [ -d "frontend" ] && command -v npm &> /dev/null; then
        # 停止已有的前端
        FRONTEND_PID=$(lsof -ti :3000 2>/dev/null || true)
        if [ -n "$FRONTEND_PID" ]; then
            kill $FRONTEND_PID 2>/dev/null || true
            sleep 1
        fi

        cd frontend
        nohup npm run dev > ../logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo "  前端已启动 (PID: $FRONTEND_PID)"
        echo "  日志: logs/frontend.log"
        cd "$PROJECT_ROOT"
    else
        echo "  跳过（frontend 目录不存在或 npm 未安装）"
    fi
fi

# 4. 启动 FastAPI 后端
if [ "$RUN_MODE" = "all" ] || [ "$RUN_MODE" = "api" ]; then
    echo ""
    echo "[4/4] 启动 FastAPI 后端..."
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
        echo "  日志: logs/api.log"
        echo ""
        echo "查看日志: tail -f logs/api.log"
        echo "停止服务: ./scripts/stop.sh"
    else
        echo "  按 Ctrl+C 停止服务"
        echo ""
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    fi
fi
