#!/bin/bash

# Concord AI - Celery 服务管理脚本
# 用法:
#   ./scripts/celery.sh start      # 启动所有 Celery 服务
#   ./scripts/celery.sh stop       # 停止所有 Celery 服务
#   ./scripts/celery.sh restart    # 重启所有 Celery 服务
#   ./scripts/celery.sh status     # 查看服务状态
#   ./scripts/celery.sh logs       # 查看日志
#   ./scripts/celery.sh flower     # 启动 Flower 监控面板
#
# Celery 服务包括：
# - Beat:   定时任务调度器（负责触发定时任务）
# - Worker: 任务执行器（负责执行任务）
# - Flower: 监控面板（可选，查看任务状态）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/logs/pids"

# 创建目录
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

cd "$PROJECT_ROOT"

# PID 文件路径
BEAT_PID_FILE="$PID_DIR/celery-beat.pid"
WORKER_PID_FILE="$PID_DIR/celery-worker.pid"
FLOWER_PID_FILE="$PID_DIR/celery-flower.pid"

# 日志文件路径
BEAT_LOG="$LOG_DIR/celery-beat.log"
WORKER_LOG="$LOG_DIR/celery-worker.log"
FLOWER_LOG="$LOG_DIR/celery-flower.log"

# ==================== 辅助函数 ====================

# 检查进程是否在运行
is_running() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            # PID 文件存在但进程不存在，清理 PID 文件
            rm -f "$pid_file"
            return 1
        fi
    fi
    return 1
}

# 获取进程 PID
get_pid() {
    local pid_file=$1
    if [ -f "$pid_file" ]; then
        cat "$pid_file"
    else
        echo ""
    fi
}

# 停止进程
stop_process() {
    local name=$1
    local pid_file=$2

    if is_running "$pid_file"; then
        local pid=$(get_pid "$pid_file")
        echo "  停止 $name (PID: $pid)..."

        # 先杀子进程树（确保守护进程包裹的实际 worker 也被停止）
        pkill -P "$pid" 2>/dev/null || true
        kill "$pid" 2>/dev/null || true

        # 等待进程结束
        for i in {1..10}; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                echo "  $name 已停止"
                rm -f "$pid_file"
                return 0
            fi
            sleep 1
        done

        # 强制终止
        echo "  强制终止 $name..."
        pkill -9 -P "$pid" 2>/dev/null || true
        kill -9 "$pid" 2>/dev/null || true
        rm -f "$pid_file"
    else
        echo "  $name 未运行"
        # 清理可能残留的 celery worker 进程
        if [ "$name" = "Celery Worker" ]; then
            local stale_pids=$(pgrep -f "celery.*worker.*app.celery_app" 2>/dev/null || true)
            if [ -n "$stale_pids" ]; then
                echo "  清理残留的 Worker 进程: $stale_pids"
                echo "$stale_pids" | xargs kill 2>/dev/null || true
            fi
        fi
    fi
}

# 启动进程
start_process() {
    local name=$1
    local pid_file=$2
    local log_file=$3
    local command=$4

    if is_running "$pid_file"; then
        local pid=$(get_pid "$pid_file")
        echo "  $name 已在运行 (PID: $pid)"
        return 0
    fi

    echo "  启动 $name..."

    # 切换到 backend 目录并激活虚拟环境
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate

    # 设置 macOS fork 安全环境变量
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

    # 启动进程
    nohup $command > "$log_file" 2>&1 &
    local pid=$!
    echo "$pid" > "$pid_file"

    # 等待一下确保进程启动
    sleep 2

    if ps -p "$pid" > /dev/null 2>&1; then
        echo "  $name 已启动 (PID: $pid)"
        echo "  日志: $log_file"
    else
        echo "  $name 启动失败，请查看日志: $log_file"
        rm -f "$pid_file"
        return 1
    fi

    cd "$PROJECT_ROOT"
}

# 启动带自动重启守护的进程（用于 Worker）
start_process_supervised() {
    local name=$1
    local pid_file=$2
    local log_file=$3
    local command=$4
    local max_retries=100          # 最大连续重启次数
    local base_delay=5             # 基础重启延迟（秒）
    local max_delay=60             # 最大重启延迟（秒）
    local healthy_threshold=120    # 运行超过此秒数则重置重启计数

    if is_running "$pid_file"; then
        local pid=$(get_pid "$pid_file")
        echo "  $name 已在运行 (PID: $pid)"
        return 0
    fi

    echo "  启动 $name（带自动重启守护）..."

    # 切换到 backend 目录并激活虚拟环境
    cd "$PROJECT_ROOT/backend"
    source venv/bin/activate

    # 设置 macOS fork 安全环境变量
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

    # 守护包装：崩溃后自动重启，带退避延迟
    nohup bash -c "
        RETRY_COUNT=0
        DELAY=$base_delay
        while [ \$RETRY_COUNT -lt $max_retries ]; do
            START_TIME=\$(date +%s)
            echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] [Supervisor] 启动 $name (第 \$((RETRY_COUNT+1)) 次)\" >> \"$log_file\"
            $command >> \"$log_file\" 2>&1
            EXIT_CODE=\$?
            END_TIME=\$(date +%s)
            RUN_DURATION=\$((END_TIME - START_TIME))

            # 如果是正常退出（比如收到 stop 信号），不重启
            if [ \$EXIT_CODE -eq 0 ]; then
                echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] [Supervisor] $name 正常退出，不再重启\" >> \"$log_file\"
                break
            fi

            # 如果运行时间足够长，说明之前是稳定的，重置计数器
            if [ \$RUN_DURATION -ge $healthy_threshold ]; then
                RETRY_COUNT=0
                DELAY=$base_delay
            else
                RETRY_COUNT=\$((RETRY_COUNT + 1))
                # 退避延迟：每次翻倍，不超过上限
                DELAY=\$((DELAY * 2))
                if [ \$DELAY -gt $max_delay ]; then
                    DELAY=$max_delay
                fi
            fi

            echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] [Supervisor] $name 异常退出 (code=\$EXIT_CODE, 运行了 \${RUN_DURATION}s)，\${DELAY}s 后重启...\" >> \"$log_file\"
            sleep \$DELAY
        done

        if [ \$RETRY_COUNT -ge $max_retries ]; then
            echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] [Supervisor] $name 连续崩溃 $max_retries 次，放弃重启\" >> \"$log_file\"
        fi
    " > /dev/null 2>&1 &

    local pid=$!
    echo "$pid" > "$pid_file"

    sleep 2

    if ps -p "$pid" > /dev/null 2>&1; then
        echo "  $name 已启动 (PID: $pid，带自动重启守护)"
        echo "  日志: $log_file"
    else
        echo "  $name 启动失败，请查看日志: $log_file"
        rm -f "$pid_file"
        return 1
    fi

    cd "$PROJECT_ROOT"
}

# ==================== 命令处理 ====================

case "${1:-start}" in
    start)
        echo "=========================================="
        echo "  启动 Celery 服务"
        echo "=========================================="
        echo ""

        # 检查虚拟环境
        if [ ! -d "$PROJECT_ROOT/backend/venv" ]; then
            echo "错误: 未找到虚拟环境，请先运行 ./scripts/setup.sh"
            exit 1
        fi

        # 启动 Celery Beat
        start_process \
            "Celery Beat" \
            "$BEAT_PID_FILE" \
            "$BEAT_LOG" \
            "celery -A app.celery_app beat --loglevel=info"

        # 启动 Celery Worker（带自动重启守护）
        start_process_supervised \
            "Celery Worker" \
            "$WORKER_PID_FILE" \
            "$WORKER_LOG" \
            "celery -A app.celery_app worker --loglevel=info --concurrency=10 -Q default,email,workflow"

        echo ""
        echo "Celery 服务已启动"
        echo ""
        echo "查看状态: ./scripts/celery.sh status"
        echo "查看日志: ./scripts/celery.sh logs"
        echo "停止服务: ./scripts/celery.sh stop"
        echo ""
        ;;

    stop)
        echo "=========================================="
        echo "  停止 Celery 服务"
        echo "=========================================="
        echo ""

        stop_process "Celery Worker" "$WORKER_PID_FILE"
        stop_process "Celery Beat" "$BEAT_PID_FILE"
        stop_process "Flower" "$FLOWER_PID_FILE"

        echo ""
        echo "Celery 服务已停止"
        echo ""
        ;;

    restart)
        echo "=========================================="
        echo "  重启 Celery 服务"
        echo "=========================================="
        echo ""

        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        echo "=========================================="
        echo "  Celery 服务状态"
        echo "=========================================="
        echo ""

        # Celery Beat
        if is_running "$BEAT_PID_FILE"; then
            beat_pid=$(get_pid "$BEAT_PID_FILE")
            echo "  Celery Beat:   运行中 (PID: $beat_pid)"
        else
            echo "  Celery Beat:   已停止"
        fi

        # Celery Worker
        if is_running "$WORKER_PID_FILE"; then
            worker_pid=$(get_pid "$WORKER_PID_FILE")
            echo "  Celery Worker: 运行中 (PID: $worker_pid)"
        else
            echo "  Celery Worker: 已停止"
        fi

        # Flower
        if is_running "$FLOWER_PID_FILE"; then
            flower_pid=$(get_pid "$FLOWER_PID_FILE")
            echo "  Flower:        运行中 (PID: $flower_pid) - http://localhost:5555"
        else
            echo "  Flower:        已停止"
        fi

        echo ""
        ;;

    logs)
        echo "=========================================="
        echo "  Celery 日志"
        echo "=========================================="
        echo ""
        echo "按 Ctrl+C 停止查看日志"
        echo ""

        # 同时查看 Beat 和 Worker 日志
        tail -f "$BEAT_LOG" "$WORKER_LOG" 2>/dev/null || {
            echo "日志文件不存在，请先启动 Celery 服务"
            exit 1
        }
        ;;

    flower)
        echo "=========================================="
        echo "  启动 Flower 监控面板"
        echo "=========================================="
        echo ""

        # 检查虚拟环境
        if [ ! -d "$PROJECT_ROOT/backend/venv" ]; then
            echo "错误: 未找到虚拟环境，请先运行 ./scripts/setup.sh"
            exit 1
        fi

        # 启动 Flower
        start_process \
            "Flower" \
            "$FLOWER_PID_FILE" \
            "$FLOWER_LOG" \
            "celery -A app.celery_app flower --port=5555"

        echo ""
        echo "Flower 已启动: http://localhost:5555"
        echo ""
        ;;

    *)
        echo "用法: $0 {start|stop|restart|status|logs|flower}"
        echo ""
        echo "命令说明:"
        echo "  start   - 启动 Celery Beat 和 Worker"
        echo "  stop    - 停止所有 Celery 服务"
        echo "  restart - 重启所有 Celery 服务"
        echo "  status  - 查看服务状态"
        echo "  logs    - 查看实时日志"
        echo "  flower  - 启动 Flower 监控面板"
        echo ""
        exit 1
        ;;
esac
