#!/bin/bash

# Concord AI - 一键部署脚本
# 用法: ./scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Concord AI - 一键部署"
echo "=========================================="

# 1. 检查依赖
echo ""
echo "[1/6] 检查系统依赖..."

if ! command -v docker &> /dev/null; then
    echo "错误: 未安装 Docker，请先安装 Docker。"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "错误: 未安装 Python3，请先安装 Python 3.11+。"
    exit 1
fi

echo "  - Docker: 已安装"
echo "  - Python3: 已安装"

# 2. 创建 .env 文件
echo ""
echo "[2/6] 配置环境变量..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "  已从 .env.example 创建 .env 文件"
    echo "  请编辑 .env 文件，填入你的 API 密钥！"
else
    echo "  .env 文件已存在"
fi

# 3. 启动 Docker 容器
echo ""
echo "[3/6] 启动 Docker 容器..."
docker-compose up -d

# 等待容器就绪
echo "  等待容器就绪..."
sleep 5

# 4. 创建虚拟环境
echo ""
echo "[4/6] 创建 Python 虚拟环境..."
cd backend

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  虚拟环境创建成功"
else
    echo "  虚拟环境已存在"
fi

# 5. 安装依赖
echo ""
echo "[5/6] 安装 Python 依赖..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# 6. 验证安装
echo ""
echo "[6/6] 验证安装..."

# 检查 Docker 容器
if docker-compose ps | grep -q "healthy"; then
    echo "  - Docker 容器: 正常"
else
    echo "  - Docker 容器: 启动中（可能需要稍等）"
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo ""
echo "后续步骤:"
echo "  1. 编辑 .env 文件，填入你的 API 密钥"
echo "  2. 运行: ./scripts/start.sh"
echo ""
