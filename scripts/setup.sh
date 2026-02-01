#!/bin/bash

# Concord AI - 一键部署脚本
# 用法: ./scripts/setup.sh
#
# 功能：
# 1. 检查系统依赖（Docker、Python、Node.js）
# 2. 创建环境变量文件
# 3. 启动 Docker 容器（PostgreSQL、Redis、Temporal）
# 4. 创建后端虚拟环境并安装依赖
# 5. 执行数据库迁移
# 6. 安装前端依赖
# 7. 验证安装
#
# 可选功能：
# - 飞书机器人集成（需要在管理后台配置 App ID/Secret）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - 一键部署"
echo "=========================================="

# 1. 检查依赖
echo ""
echo "[1/8] 检查系统依赖..."

if ! command -v docker &> /dev/null; then
    echo "错误: 未安装 Docker，请先安装 Docker。"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "错误: 未安装 Python3，请先安装 Python 3.11+。"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "警告: 未安装 Node.js，前端将无法启动。"
    echo "      请安装 Node.js 18+: https://nodejs.org/"
    HAS_NODE=false
else
    HAS_NODE=true
fi

echo "  - Docker:  已安装"
echo "  - Python3: 已安装"
if [ "$HAS_NODE" = true ]; then
    echo "  - Node.js: 已安装 ($(node --version))"
fi

# 2. 创建 .env 文件
echo ""
echo "[2/8] 配置环境变量..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  已从 .env.example 创建 .env 文件"
    else
        echo "  创建默认 .env 文件..."
        cat > .env << 'EOF'
# Concord AI 环境变量配置

# ==================== 基础配置 ====================
APP_NAME=Concord AI
DEBUG=true

# ==================== 数据库 ====================
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/concord

# ==================== Redis ====================
REDIS_URL=redis://localhost:6379/0

# ==================== JWT 认证 ====================
JWT_SECRET=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ==================== LLM API ====================
# 至少配置一个 LLM API Key
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# ==================== Temporal 工作流引擎 ====================
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=concord-main-queue

# ==================== 邮件配置（可选，也可在管理后台配置） ====================
# SMTP 发件
SMTP_HOST=
SMTP_PORT=465
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true

# IMAP 收件
IMAP_HOST=
IMAP_PORT=993
IMAP_USER=
IMAP_PASSWORD=
IMAP_USE_SSL=true

# ==================== 飞书机器人（可选） ====================
FEISHU_APP_ID=
FEISHU_APP_SECRET=

# ==================== 阿里云 OSS（可选） ====================
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=
EOF
    fi
    echo "  请编辑 .env 文件，填入你的 API 密钥！"
else
    echo "  .env 文件已存在"
fi

# 3. 启动 Docker 容器
echo ""
echo "[3/8] 启动 Docker 容器..."
docker compose up -d

# 4. 等待容器就绪
echo ""
echo "[4/8] 等待容器就绪..."

# 等待 PostgreSQL
echo -n "  PostgreSQL: "
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        echo "就绪"
        break
    fi
    echo -n "."
    sleep 1
done

# 等待 Redis
echo -n "  Redis:      "
for i in {1..10}; do
    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "就绪"
        break
    fi
    echo -n "."
    sleep 1
done

# 等待 Temporal（需要更长时间）
echo -n "  Temporal:   "
for i in {1..30}; do
    # 使用容器 IP 检查 Temporal 健康状态
    if docker compose exec -T temporal sh -c 'temporal operator cluster health --address $(hostname -i):7233' > /dev/null 2>&1; then
        echo "就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "超时（可稍后重试）"
    else
        echo -n "."
        sleep 2
    fi
done

# 5. 创建虚拟环境
echo ""
echo "[5/8] 创建 Python 虚拟环境..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  虚拟环境创建成功"
else
    echo "  虚拟环境已存在"
fi

# 6. 安装后端依赖
echo ""
echo "[6/8] 安装后端依赖..."
source venv/bin/activate
pip install -r requirements.txt --quiet
echo "  后端依赖安装完成"

# 7. 执行数据库迁移
echo ""
echo "[7/8] 执行数据库迁移..."
alembic upgrade head
echo "  数据库迁移完成"

cd "$PROJECT_ROOT"

# 8. 安装前端依赖
echo ""
echo "[8/8] 安装前端依赖..."
if [ "$HAS_NODE" = true ] && [ -d "frontend" ]; then
    cd frontend
    npm install --silent
    echo "  前端依赖安装完成"
    cd "$PROJECT_ROOT"
else
    echo "  跳过（Node.js 未安装或 frontend 目录不存在）"
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "服务地址："
echo "  - PostgreSQL:  localhost:5432"
echo "  - Redis:       localhost:6379"
echo "  - Temporal:    localhost:7233"
echo "  - Temporal UI: http://localhost:8080"
echo ""
echo "后续步骤："
echo "  1. 编辑 .env 文件，填入你的 API 密钥"
echo "  2. 创建管理员: cd backend && source venv/bin/activate && python ../scripts/create_admin.py"
echo "  3. 启动服务:   ./scripts/start.sh"
echo ""
echo "可选功能："
echo "  - 飞书机器人: 访问管理后台 -> 飞书配置，填写 App ID/Secret"
echo "  - 启动飞书 Worker: ./scripts/start.sh --feishu"
echo ""
