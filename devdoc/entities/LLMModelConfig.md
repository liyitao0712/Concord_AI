# LLMModelConfig LLM 模型配置

## 概述

LLMModelConfig 是 LLM 模型配置实体，管理系统中可用的 AI 模型（通过 LiteLLM 调用）。包含 API Key、端点、使用统计等信息。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| model_id | String(100) | LiteLLM 模型 ID（唯一，如 openai/gpt-4） |
| provider | String(50) | 提供商 (openai/anthropic/deepseek 等) |
| model_name | String(100) | 模型显示名称 |
| api_key | Text | API Key（加密存储） |
| api_endpoint | Text | 自定义 API 端点 |
| total_requests | Integer | 总请求次数 |
| total_tokens | BigInteger | 总 token 消耗 |
| last_used_at | DateTime | 最后使用时间 |
| is_enabled | Boolean | 是否启用 |
| is_configured | Boolean | 是否已配置（API Key 已设置） |
| description | Text | 描述 |
| parameters | JSON | 模型参数 (temperature, max_tokens 等) |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/llm-configs | 模型配置列表 |
| POST | /admin/llm-configs | 添加模型配置 |
| PUT | /admin/llm-configs/{id} | 更新配置 |
| DELETE | /admin/llm-configs/{id} | 删除配置 |
| POST | /admin/llm-configs/{id}/test | 测试连通性 |

## 相关文件

- Model: `backend/app/models/llm_model_config.py`
- Gateway: `backend/app/llm/gateway.py`
- API: `backend/app/api/llm_configs.py`
- Frontend: `frontend/src/app/admin/llm-configs/page.tsx`
