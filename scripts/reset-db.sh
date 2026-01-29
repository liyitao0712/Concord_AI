#!/bin/bash

# Concord AI - 重置数据库脚本
# 用法: ./scripts/reset-db.sh
# 警告: 此操作会删除所有数据！

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - 重置数据库"
echo "=========================================="
echo ""
echo "警告: 此操作会删除数据库中的所有数据！"
echo ""
read -p "确定要继续吗？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "已取消。"
    exit 0
fi

echo ""
echo "[1/3] 停止容器..."
docker-compose down

echo ""
echo "[2/3] 删除数据库卷..."
docker volume rm concord_ai_postgres_data 2>/dev/null || true

echo ""
echo "[3/3] 重启容器..."
docker-compose up -d

# 等待 PostgreSQL 就绪
echo "等待 PostgreSQL 就绪..."
sleep 5

echo ""
echo "=========================================="
echo "  数据库重置完成！"
echo "=========================================="
echo ""
echo "数据库已恢复到初始状态。"
echo "如需运行迁移，请执行:"
echo "  cd backend && source venv/bin/activate"
echo "  alembic upgrade head"
echo ""
