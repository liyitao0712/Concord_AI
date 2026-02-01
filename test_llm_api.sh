#!/bin/bash
# 测试 LLM 模型配置 API

echo "=========================================="
echo "测试 LLM 模型配置 API"
echo "=========================================="
echo ""

# 不需要认证的测试端点
echo "[1] 测试健康检查..."
curl -s http://localhost:8000/health | python3 -m json.tool
echo ""

# 列出所有模型（需要认证，但先测试是否返回401）
echo "[2] 测试模型列表 API（应返回401）..."
curl -s http://localhost:8000/admin/llm/models
echo ""
echo ""

# 测试特定提供商的模型
echo "[3] 测试 Gemini 模型列表（应返回401）..."
curl -s "http://localhost:8000/admin/llm/models?provider=gemini"
echo ""
echo ""

echo "=========================================="
echo "测试完成"
echo "=========================================="
echo ""
echo "提示：需要先登录获取 token 才能访问 /admin/* 接口"
echo "登录命令："
echo "  curl -X POST http://localhost:8000/api/auth/login \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"email\": \"your@email.com\", \"password\": \"yourpassword\"}'"
