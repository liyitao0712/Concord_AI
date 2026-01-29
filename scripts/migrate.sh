#!/bin/bash

# Concord AI - 数据库迁移脚本
# 用法:
#   ./scripts/migrate.sh                    # 执行迁移
#   ./scripts/migrate.sh create "描述信息"   # 创建新迁移
#   ./scripts/migrate.sh down               # 回滚上一次迁移

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/backend"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "错误: 未找到虚拟环境，请先运行 ./scripts/setup.sh"
    exit 1
fi

ACTION=${1:-upgrade}
MESSAGE=$2

case $ACTION in
    upgrade|up)
        echo "执行数据库迁移..."
        alembic upgrade head
        echo "迁移完成。"
        ;;
    downgrade|down)
        echo "回滚上一次迁移..."
        alembic downgrade -1
        echo "回滚完成。"
        ;;
    create|new)
        if [ -z "$MESSAGE" ]; then
            echo "错误: 请提供迁移描述"
            echo "用法: ./scripts/migrate.sh create \"你的描述\""
            exit 1
        fi
        echo "创建新迁移: $MESSAGE"
        alembic revision --autogenerate -m "$MESSAGE"
        echo "迁移文件已创建，请检查 alembic/versions/ 目录"
        ;;
    history)
        echo "迁移历史:"
        alembic history
        ;;
    current)
        echo "当前迁移版本:"
        alembic current
        ;;
    *)
        echo "用法: ./scripts/migrate.sh [命令]"
        echo ""
        echo "可用命令:"
        echo "  upgrade, up     执行所有待处理的迁移（默认）"
        echo "  downgrade, down 回滚上一次迁移"
        echo "  create, new     创建新迁移（需要描述信息）"
        echo "  history         查看迁移历史"
        echo "  current         查看当前迁移版本"
        ;;
esac
