# Prompt 提示词模板

## 概述

Prompt 是 LLM 提示词模板实体，支持数据库优先 + 代码默认值回退的双层架构。PromptHistory 记录每次修改的历史版本。

## 数据模型

### Prompt（提示词模板）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| name | String(100) | 模板名称（唯一索引，如 email_summarizer） |
| category | String(50) | 分类 (agent/tool/general) |
| display_name | String(200) | 显示名称 |
| content | Text | 模板内容（支持 {{variable}} 占位符） |
| variables | JSON | 变量定义 {变量名: 说明} |
| description | Text | 描述 |
| version | Integer | 版本号 |
| is_active | Boolean | 是否启用 |
| model_hint | String(50) | 推荐使用的模型 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |
| created_by | UUID | 创建人 ID |
| updated_by | UUID | 更新人 ID |

### PromptHistory（修改历史）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| prompt_id | UUID | 关联 Prompt ID |
| prompt_name | String(100) | Prompt 名称 |
| content | Text | 当时的内容 |
| variables | JSON | 当时的变量 |
| version | Integer | 版本号 |
| changed_at | DateTime | 修改时间 |
| changed_by | UUID | 修改人 ID |
| change_reason | String(500) | 修改原因 |

## 加载优先级

1. 数据库中的 Prompt（5 分钟缓存）
2. `backend/app/llm/prompts/defaults.py` 中的默认值

## 命名规范

- `{agent_name}_system` — Agent 的 system prompt
- `{agent_name}` — Agent 的 user prompt 模板
- `{tool_name}` — Tool 的 prompt 模板

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/prompts | 模板列表 |
| GET | /admin/prompts/{name} | 获取模板 |
| PUT | /admin/prompts/{name} | 更新模板 |
| POST | /admin/prompts/{name}/reset | 重置为默认值 |
| GET | /admin/prompts/{name}/history | 修改历史 |

## 相关文件

- Model: `backend/app/models/prompt.py`
- Manager: `backend/app/llm/prompts/manager.py`
- Defaults: `backend/app/llm/prompts/defaults.py`
- API: `backend/app/api/prompts.py`
- Frontend: `frontend/src/app/admin/prompts/page.tsx`
