# LLM 管理完整手册

> Concord AI 的 LLM 管理系统详细说明
> 合并自: LLM_MANUAL.md + LLM_ARCHITECTURE_REVIEW.md

---

## 目录

1. [概述](#1-概述)
2. [数据库表结构](#2-数据库表结构)
3. [LLM 模型管理](#3-llm-模型管理)
4. [Prompt 模板管理](#4-prompt-模板管理)
5. [API 接口](#5-api-接口)
6. [使用指南](#6-使用指南)
7. [故障排查](#7-故障排查)
8. [最佳实践](#8-最佳实践)
9. [附录](#9-附录)
10. [架构审查与改进建议](#10-架构审查与改进建议)

---

## 1. 概述

Concord AI 的 LLM 管理系统提供了完整的 AI 模型和 Prompt 模板管理能力，支持：

- **多模型管理**：支持 Anthropic、OpenAI、Gemini、Qwen 等多个 LLM 提供商
- **动态配置**：无需重启服务即可切换模型和修改 Prompt
- **使用统计**：自动记录每个模型的请求次数和 Token 消耗
- **版本控制**：Prompt 修改自动记录历史，支持回滚
- **在线测试**：后台可直接测试模型连接和 Prompt 渲染

---

## 2. 数据库表结构

### 2.1 LLM 模型配置表

**表名**: `llm_model_configs`

**用途**: 管理所有可用的 LLM 模型配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36) | 主键 UUID |
| `model_id` | String(100) | 模型标识（如 `gemini/gemini-1.5-pro`）|
| `provider` | String(50) | 提供商（anthropic, openai, gemini, qwen 等）|
| `model_name` | String(100) | 显示名称（如 "Gemini 1.5 Pro"）|
| `api_key` | Text | API 密钥（敏感，加密存储）|
| `api_endpoint` | Text | 自定义 API 端点（可选）|
| `total_requests` | Integer | 总请求次数 |
| `total_tokens` | BigInteger | 总消耗 Token 数 |
| `last_used_at` | DateTime | 最后使用时间 |
| `is_enabled` | Boolean | 是否启用 |
| `is_configured` | Boolean | 是否已配置（有 API Key）|
| `description` | Text | 模型描述 |
| `parameters` | JSON | 默认参数（temperature, max_tokens 等）|
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

**索引**:
- `model_id` - 唯一索引
- `provider` - 普通索引
- `is_enabled` - 普通索引
- `is_configured` - 普通索引

---

### 2.2 Prompt 模板表

**表名**: `prompts`

**用途**: 存储所有 Agent 和 Tool 的 Prompt 模板

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36) | 主键 UUID |
| `name` | String(100) | Prompt 名称（唯一，如 `email_summarizer`）|
| `category` | String(50) | 分类（agent, tool, template, system）|
| `display_name` | String(200) | 显示名称 |
| `content` | Text | Prompt 内容模板 |
| `variables` | JSON | 变量定义（变量名 -> 说明）|
| `description` | Text | 描述 |
| `is_active` | Boolean | 是否激活 |
| `version` | Integer | 版本号（每次修改自增）|
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

**索引**:
- `name` - 唯一索引
- `category` - 普通索引
- `is_active` - 普通索引

**Category 说明**:
- `agent`: Agent 的系统提示词（如 chat_agent, email_analyzer）
- `tool`: Tool 调用 LLM 的提示词（如 summarizer, translator）
- `template`: 通用模板（如邮件回复模板）
- `system`: 系统级提示（如错误处理）

---

### 2.3 Prompt 历史版本表

**表名**: `prompt_history`

**用途**: 记录 Prompt 的修改历史，支持版本回滚

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | String(36) | 主键 UUID |
| `prompt_id` | String(36) | 关联的 Prompt ID |
| `version` | Integer | 历史版本号 |
| `content` | Text | 历史 Prompt 内容 |
| `changed_by` | String(100) | 修改人（管理员邮箱）|
| `change_reason` | Text | 修改原因 |
| `created_at` | DateTime | 修改时间 |

**索引**:
- `prompt_id` - 普通索引
- `prompt_id, version` - 联合唯一索引

**功能**: 每次通过后台修改 Prompt 时，自动创建历史记录

---

## 3. LLM 模型管理

### 3.1 支持的模型

系统当前支持以下 LLM 提供商和模型：

#### Anthropic (Claude)
| Model ID | 显示名称 | 说明 |
|----------|---------|------|
| `claude-sonnet-4-20250514` | Claude Sonnet 4 | 最新旗舰模型 |
| `claude-3-5-sonnet-20241022` | Claude 3.5 Sonnet | 高性能通用模型 |
| `claude-3-opus-20240229` | Claude 3 Opus | 最强大，适合复杂任务 |
| `claude-3-haiku-20240307` | Claude 3 Haiku | 最快速，适合简单任务 |

#### OpenAI (GPT)
| Model ID | 显示名称 | 说明 |
|----------|---------|------|
| `gpt-4o` | GPT-4o | 多模态模型 |
| `gpt-4-turbo` | GPT-4 Turbo | 更快更便宜 |
| `gpt-3.5-turbo` | GPT-3.5 Turbo | 性价比高 |

#### Google (Gemini)
| Model ID | 显示名称 | 说明 |
|----------|---------|------|
| `gemini/gemini-1.5-pro` | Gemini 1.5 Pro | 高性能模型 |
| `gemini/gemini-1.5-flash` | Gemini 1.5 Flash | 快速响应 |

#### Alibaba (Qwen/通义千问)
| Model ID | 显示名称 | 说明 |
|----------|---------|------|
| `qwen/qwen-max` | 通义千问 Max | 旗舰模型 |
| `qwen/qwen-plus` | 通义千问 Plus | 高性价比 |

---

### 3.2 模型配置流程

#### 步骤 1: 获取 API Key

1. **Anthropic**: https://console.anthropic.com
2. **OpenAI**: https://platform.openai.com
3. **Google**: https://makersuite.google.com/app/apikey
4. **Alibaba**: https://dashscope.console.aliyun.com

#### 步骤 2: 在后台配置

1. 登录管理后台: http://localhost:3000/admin
2. 进入 "LLM 配置" 页面
3. 选择要配置的模型
4. 填写 API Key
5. （可选）设置默认参数（temperature, max_tokens）
6. 点击 "保存配置"

#### 步骤 3: 测试连接

1. 点击 "测试连接" 按钮
2. 系统会发送一个简单的测试请求
3. 成功则显示模型响应
4. 失败则显示错误信息

---

### 3.3 使用统计

系统自动记录每个模型的使用情况：

- **总请求次数** (`total_requests`): 累计调用次数
- **总 Token 消耗** (`total_tokens`): 累计消耗的 Token 数
- **最后使用时间** (`last_used_at`): 最近一次调用时间

查看统计：
```bash
GET /admin/llm/models/stats/usage
```

返回示例：
```json
{
  "stats": [
    {
      "model_id": "claude-sonnet-4-20250514",
      "model_name": "Claude Sonnet 4",
      "provider": "anthropic",
      "total_requests": 1234,
      "total_tokens": 456789,
      "last_used_at": "2026-02-01T10:30:00Z"
    }
  ],
  "total_requests": 5678,
  "total_tokens": 1234567
}
```

---

## 4. Prompt 模板管理

### 4.1 当前 Prompt 清单

系统预置了 **8 个 Prompt 模板**：

#### Agent Prompts (6个)

| Name | Display Name | 用途 |
|------|-------------|------|
| `router_agent` | 路由分类器 | 分析消息意图，决定路由到哪个 Agent |
| `chat_agent` | 聊天助手 | 通用对话助手的系统提示 |
| `intent_classifier` | 意图分类器 | 快速分类用户意图 |
| `email_analyzer` | 邮件分析器 | 分析邮件内容，提取关键信息 |
| `email_summarizer` | 邮件摘要分析器 | 分析外贸邮件，提取意图、产品、金额等 |
| `quote_agent` | 报价生成器 | 根据询价生成报价单 |

#### Tool Prompts (2个)

| Name | Display Name | 用途 |
|------|-------------|------|
| `summarizer` | 通用摘要生成器 | 生成文本摘要（可被多个 Agent 调用）|
| `translator` | 翻译器 | 文本翻译（多语言支持）|

---

### 4.2 Prompt 变量机制

#### 变量语法

使用 `{{变量名}}` 语法定义变量：

```
你是一个邮件分析助手。

发件人: {{sender}}
主题: {{subject}}
内容: {{content}}

请分析以上邮件...
```

#### 变量定义

在 Prompt 的 `variables` 字段中定义：

```json
{
  "sender": "发件人邮箱",
  "subject": "邮件主题",
  "content": "邮件正文"
}
```

#### 变量渲染

调用时传入变量值：

```python
from app.llm.prompts import render_prompt

prompt = await render_prompt(
    "email_summarizer",
    sender="test@example.com",
    subject="询价",
    content="请问产品A的价格？"
)
```

---

### 4.3 Prompt 加载机制

**优先级**（从高到低）：

1. **数据库中的 Prompt**（可在后台修改）
2. **defaults.py 中的定义**（代码默认值）
3. **Agent 类中的 `_default_system_prompt()`**（硬编码 fallback）

**加载流程**：

```python
# BaseAgent 中的实现 (app/agents/base.py:245-251)
async def _get_system_prompt(self) -> str:
    if self.prompt_name:
        # 1. 尝试从数据库加载
        prompt = await prompt_manager.get_prompt(self.prompt_name)
        if prompt:
            return prompt
    # 2. 使用默认值
    return self._default_system_prompt()
```

**缓存机制**：
- Prompt 从数据库加载后缓存 **5 分钟**
- 修改 Prompt 后自动清除缓存
- 下次请求时重新加载新 Prompt

---

### 4.4 Prompt 版本控制

#### 自动版本记录

每次通过后台修改 Prompt 时：
1. Prompt 的 `version` 字段自增
2. 自动在 `prompt_history` 表创建历史记录
3. 记录修改人和修改时间

#### 查看历史版本

```bash
# API 查询（TODO: 待实现）
GET /admin/prompts/{name}/history
```

#### 版本回滚

```bash
# API 回滚（TODO: 待实现）
POST /admin/prompts/{name}/rollback
{
  "version": 3
}
```

---

## 5. API 接口

### 5.1 LLM 模型管理 API

**路由前缀**: `/admin/llm/models`

**权限**: 需要管理员权限

#### 获取模型列表

```bash
GET /admin/llm/models
  ?provider=anthropic        # 可选：按提供商筛选
  &is_enabled=true           # 可选：只显示已启用
  &is_configured=true        # 可选：只显示已配置

Authorization: Bearer <admin_token>
```

响应：
```json
{
  "items": [
    {
      "id": "uuid",
      "model_id": "claude-sonnet-4-20250514",
      "provider": "anthropic",
      "model_name": "Claude Sonnet 4",
      "api_key_preview": "sk-a...xyz",
      "is_enabled": true,
      "is_configured": true,
      "total_requests": 123,
      "total_tokens": 45678
    }
  ],
  "total": 10
}
```

#### 获取单个模型

```bash
GET /admin/llm/models/{model_id}

Authorization: Bearer <admin_token>
```

#### 更新模型配置

```bash
PUT /admin/llm/models/{model_id}

Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "api_key": "sk-ant-xxx",
  "api_endpoint": "https://...",
  "is_enabled": true,
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 2048
  }
}
```

#### 测试模型连接

```bash
POST /admin/llm/models/{model_id}/test

Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "test_prompt": "你好"
}
```

响应：
```json
{
  "success": true,
  "response": "你好！我是 Claude，很高兴认识你。",
  "model_used": "claude-sonnet-4-20250514",
  "tokens_used": 15
}
```

#### 获取使用统计

```bash
GET /admin/llm/models/stats/usage

Authorization: Bearer <admin_token>
```

---

### 5.2 Prompt 管理 API

**路由前缀**: `/admin/prompts`

**权限**: 需要管理员权限

#### 获取 Prompt 列表

```bash
GET /admin/prompts
  ?category=agent            # 可选：按分类筛选
  &is_active=true            # 可选：只显示激活的

Authorization: Bearer <admin_token>
```

响应：
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "email_summarizer",
      "category": "agent",
      "display_name": "邮件摘要分析器",
      "content": "你是一个专业的...",
      "variables": {
        "sender": "发件人邮箱",
        "subject": "邮件主题"
      },
      "is_active": true,
      "version": 3
    }
  ],
  "total": 8
}
```

#### 获取单个 Prompt

```bash
GET /admin/prompts/{prompt_name}

Authorization: Bearer <admin_token>
```

#### 更新 Prompt

```bash
PUT /admin/prompts/{prompt_name}

Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "content": "新的 Prompt 内容 {{variable}}",
  "display_name": "新名称",
  "description": "新描述",
  "variables": {
    "variable": "变量说明"
  },
  "is_active": true
}
```

响应：更新后的 Prompt 对象（version 已自增）

#### 测试 Prompt 渲染

```bash
POST /admin/prompts/{prompt_name}/test

Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "variables": {
    "sender": "test@example.com",
    "subject": "询价"
  }
}
```

响应：
```json
{
  "rendered": "你是一个专业的...\n发件人: test@example.com\n主题: 询价",
  "variables_used": ["sender", "subject"],
  "missing_variables": ["content"]
}
```

#### 初始化默认 Prompt

```bash
POST /admin/prompts/init-defaults

Authorization: Bearer <admin_token>
```

功能：将 `defaults.py` 中定义的所有 Prompt 同步到数据库

响应：
```json
{
  "success": true,
  "detail": "默认 Prompt 已初始化",
  "total_prompts": 8
}
```

---

### 5.3 LLM 调用 API（用户接口）

**路由前缀**: `/api/llm`

**权限**: 需要用户登录

#### 普通对话

```bash
POST /api/llm/chat

Authorization: Bearer <user_token>
Content-Type: application/json

{
  "message": "你好，请介绍一下自己",
  "system_prompt": "你是一个友好的助手",
  "model": "claude-3-haiku-20240307",
  "temperature": 0.7
}
```

响应：
```json
{
  "response": "你好！我是 Claude...",
  "model": "claude-3-haiku-20240307"
}
```

#### 流式对话（SSE）

```bash
POST /api/llm/stream

Authorization: Bearer <user_token>
Content-Type: application/json

{
  "message": "写一首关于春天的诗",
  "model": "claude-sonnet-4-20250514"
}
```

响应（SSE 格式）：
```
data: 春

data: 风

data: 拂

data: 面

...

data: [DONE]
```

#### 意图分类

```bash
POST /api/llm/classify

Authorization: Bearer <user_token>
Content-Type: application/json

{
  "content": "请问产品A的价格是多少？"
}
```

响应：
```json
{
  "intent": "inquiry",
  "confidence": 0.95,
  "keywords": ["价格", "产品A"],
  "raw_response": "{...}"
}
```

---

## 6. 使用指南

### 6.1 快速开始

#### 1. 配置第一个 LLM 模型

```bash
# 1. 登录管理后台
open http://localhost:3000/admin/login

# 2. 进入 LLM 配置
# 导航到: 管理后台 > LLM 配置

# 3. 选择 Claude Sonnet 4
# 填写 API Key: sk-ant-xxx
# 点击 "保存配置"

# 4. 测试连接
# 点击 "测试连接"，验证配置正确
```

#### 2. 使用 LLM 对话

```python
from app.services.llm_service import llm_service

# 普通对话
response = await llm_service.chat(
    message="你好",
    system_prompt="你是一个友好的助手"
)
print(response)

# 流式对话
async for chunk in llm_service.chat_stream(message="写一首诗"):
    print(chunk, end="", flush=True)
```

#### 3. 使用 Agent（自动使用 Prompt）

```python
from app.agents.registry import agent_registry

# 调用 Email Summarizer Agent
result = await agent_registry.run(
    "email_summarizer",
    input_data={
        "sender": "customer@example.com",
        "subject": "询价",
        "body_text": "请问产品A的价格？"
    }
)

print(result.data)  # 分析结果
```

---

### 6.2 修改 Prompt

#### 方式一：通过后台管理界面

1. 登录管理后台
2. 进入 "Prompt 管理"
3. 找到要修改的 Prompt（如 `email_summarizer`）
4. 点击 "编辑"
5. 修改 `content` 内容
6. 点击 "保存"

修改后立即生效（最多 5 分钟缓存延迟）

#### 方式二：通过 API

```bash
curl -X PUT http://localhost:8000/admin/prompts/email_summarizer \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "你是一个专业的邮件分析助手...",
    "description": "更新后的描述"
  }'
```

---

### 6.3 添加新变量到 Prompt

#### 场景：想要在邮件分析中增加 `company` 变量

1. 修改 Prompt 内容，添加变量：
   ```
   发件人: {{sender}}
   公司: {{company}}   <-- 新增
   主题: {{subject}}
   ```

2. 更新 `variables` 定义：
   ```json
   {
     "sender": "发件人邮箱",
     "company": "发件人公司",
     "subject": "邮件主题"
   }
   ```

3. 修改调用代码，传入新变量：
   ```python
   result = await agent_registry.run(
       "email_summarizer",
       input_data={
           "sender": "customer@example.com",
           "company": "ABC Corp",
           "subject": "询价"
       }
   )
   ```

---

### 6.4 切换默认模型

#### 方式一：环境变量（全局）

```bash
# .env
DEFAULT_LLM_MODEL=claude-3-haiku-20240307
```

#### 方式二：运行时指定（单次）

```python
response = await llm_service.chat(
    message="你好",
    model="gpt-4o"  # 覆盖默认模型
)
```

#### 方式三：Agent 配置（Agent 级别）

```python
class MyAgent(BaseAgent):
    model = "claude-3-haiku-20240307"  # 该 Agent 使用特定模型
```

---

### 6.5 监控 Token 使用

#### 查看总体统计

```bash
curl http://localhost:8000/admin/llm/models/stats/usage \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### 查看单个模型统计

```bash
curl http://localhost:8000/admin/llm/models/claude-sonnet-4-20250514 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## 7. 故障排查

### 问题 1: 修改 Prompt 后不生效

**原因**: Prompt 有 5 分钟缓存

**解决**:
1. 等待 5 分钟让缓存过期
2. 或重启服务立即生效

### 问题 2: LLM 调用失败

**检查清单**:
1. API Key 是否正确配置？
2. 模型是否已启用（`is_enabled=true`）？
3. 网络是否可以访问 LLM 提供商？
4. 查看日志：`./scripts/logs.sh api`

### 问题 3: Agent 使用的是旧 Prompt

**原因**: Agent 可能有硬编码的 fallback

**解决**:
1. 确认 Agent 设置了 `prompt_name`
2. 确认数据库中有对应的 Prompt
3. 查看日志确认是否从数据库加载

---

## 8. 最佳实践

### 8.1 Prompt 编写建议

1. **明确角色**：开头明确 AI 的角色
   ```
   你是一个专业的邮件分析助手。
   ```

2. **结构化输出**：要求 JSON 输出，便于解析
   ```
   请以 JSON 格式返回：
   {"intent": "...", "confidence": 0.95}
   ```

3. **提供示例**：在 Prompt 中给出示例输出
   ```
   ## 示例
   输入: "请问价格？"
   输出: {"intent": "inquiry", "confidence": 0.9}
   ```

4. **使用约束**：明确禁止什么
   ```
   ## 约束
   - 只输出 JSON，不要解释
   - confidence 必须在 0-1 之间
   ```

### 8.2 模型选择建议

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 简单分类 | Claude 3 Haiku | 快速、便宜 |
| 邮件分析 | Claude 3.5 Sonnet | 准确度高 |
| 复杂推理 | Claude 3 Opus | 最强大 |
| 代码生成 | GPT-4 Turbo | 编程能力强 |
| 成本优先 | GPT-3.5 Turbo | 性价比最高 |

### 8.3 变量命名规范

- 使用 **snake_case**：`sender_name`（不是 `senderName`）
- 名称要 **描述性强**：`email_subject`（不是 `s`）
- 避免 **保留字**：不要用 `content`、`data` 等通用词

---

## 9. 附录

### 9.1 完整 API 列表

#### LLM 模型管理
```
GET    /admin/llm/models              # 模型列表
GET    /admin/llm/models/{model_id}   # 模型详情
PUT    /admin/llm/models/{model_id}   # 更新配置
POST   /admin/llm/models/{model_id}/test  # 测试连接
GET    /admin/llm/models/stats/usage  # 使用统计
```

#### Prompt 管理
```
GET    /admin/prompts                 # Prompt 列表
GET    /admin/prompts/{name}          # Prompt 详情
PUT    /admin/prompts/{name}          # 更新 Prompt
POST   /admin/prompts/{name}/test     # 测试渲染
POST   /admin/prompts/init-defaults   # 初始化默认值
```

#### LLM 调用
```
POST   /api/llm/chat      # 普通对话
POST   /api/llm/stream    # 流式对话
POST   /api/llm/classify  # 意图分类
```

### 9.2 相关文件

| 文件 | 说明 |
|------|------|
| `app/models/llm_model_config.py` | LLM 模型配置数据模型 |
| `app/models/prompt.py` | Prompt 和历史数据模型 |
| `app/api/llm_models.py` | LLM 模型管理 API |
| `app/api/prompts.py` | Prompt 管理 API |
| `app/api/llm.py` | LLM 调用 API |
| `app/llm/prompts/defaults.py` | 默认 Prompt 定义 |
| `app/llm/prompts/manager.py` | Prompt 管理器 |
| `app/services/llm_service.py` | LLM 服务封装 |
| `app/agents/base.py` | Agent 基类（Prompt 加载）|

---

## 10. 架构审查与改进建议

> 以下内容来自 LLM 架构审查报告 (2026-02-01)

### 10.1 当前状况总览

#### 优点

1. **基本日志记录**：所有 LLM 调用都有基本的日志输出
2. **性能追踪**：记录了耗时、Token 使用量
3. **错误处理**：有完整的 try-catch 和错误日志
4. **支持流式输出**：Gateway 和 Service 都支持 SSE

#### 发现的问题

| 问题 | 严重程度 | 影响范围 |
|------|---------|---------|
| **两个并存的 LLM 封装层** | 高 | 全局架构 |
| **缺少 LLM 调用日志表** | 中 | 监控和审计 |
| **没有统一的调用拦截器** | 中 | Token 统计不完整 |
| **使用统计未入库** | 中 | 数据丢失风险 |
| **缺少调用链追踪** | 中 | 问题定位困难 |

---

### 10.2 双封装层问题 (LLMGateway vs LLMService)

**现状**：

```
项目中存在两个 LLM 封装：

1. LLMGateway (app/llm/gateway.py)
   - 使用者：BaseAgent, RouterAgent, ChatAgent 等
   - 特点：功能全面，支持 tools、JSON 模式

2. LLMService (app/services/llm_service.py)
   - 使用者：API 层 (app/api/llm.py)
   - 特点：简单封装，面向 API 调用
```

**问题**：
- 维护两套代码，容易不一致
- 日志格式不统一
- Token 统计分散，无法汇总
- 新功能要在两处添加

**建议**：
```
方案 A：统一为 LLMGateway（推荐）
- 废弃 LLMService
- API 层改用 LLMGateway
- 理由：LLMGateway 功能更完善

方案 B：统一为 LLMService
- 废弃 LLMGateway
- BaseAgent 改用 LLMService
- 理由：LLMService 更简单

推荐方案 A，因为 LLMGateway 已支持 tools、JSON 模式等高级功能。
```

---

### 10.3 缺少 LLM 调用日志表

**现状**：

只有文件日志，没有数据库记录：
```python
# app/llm/gateway.py:163
logger.info(f"[LLM] 调用模型: {model}")
logger.info(f"[LLM] 完成，使用 {usage['total_tokens']} tokens")
```

**问题**：
- 无法查询历史调用记录
- 无法按用户/Agent/时间段统计
- 日志轮转后数据丢失
- 无法追溯成本

**建议**：

创建 `llm_call_logs` 表：

```python
# app/models/llm_call_log.py

class LLMCallLog(Base):
    __tablename__ = "llm_call_logs"

    id = Column(String(36), primary_key=True)

    # 调用信息
    model = Column(String(100), index=True)       # 使用的模型
    provider = Column(String(50), index=True)     # 提供商

    # 调用者信息
    caller_type = Column(String(50), index=True)  # agent / api / workflow
    caller_name = Column(String(100))             # agent 名称或 API 路径
    user_id = Column(String(36), nullable=True, index=True)  # 用户 ID

    # 请求内容
    system_prompt = Column(Text, nullable=True)   # 系统提示
    user_message = Column(Text)                   # 用户消息
    messages_count = Column(Integer, default=1)   # 消息数量（含历史）

    # 响应内容
    response_content = Column(Text)               # LLM 响应
    finish_reason = Column(String(50))            # 完成原因

    # 使用统计
    prompt_tokens = Column(Integer)               # 输入 Token
    completion_tokens = Column(Integer)           # 输出 Token
    total_tokens = Column(Integer, index=True)    # 总 Token

    # 性能指标
    latency_ms = Column(Integer)                  # 延迟（毫秒）

    # 状态
    status = Column(String(20), index=True)       # success / error
    error_message = Column(Text, nullable=True)   # 错误信息

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

**优点**：
- 可查询历史调用
- 可统计成本
- 可分析使用模式
- 可追踪问题
- 可生成报表

---

### 10.4 统一调用拦截器方案

**现状**：

每个调用点都手动记录日志：

```python
# app/llm/gateway.py:163-183
logger.info(f"[LLM] 调用模型: {model}")
# ... 调用 LLM ...
logger.info(f"[LLM] 完成，使用 {usage['total_tokens']} tokens")
```

**问题**：
- 重复代码
- 容易遗漏
- 不统一

**建议**：

创建装饰器统一拦截：

```python
# app/llm/interceptor.py

import functools
from typing import Optional
from contextlib import asynccontextmanager

class LLMCallInterceptor:
    """LLM 调用拦截器"""

    @staticmethod
    async def log_call(
        model: str,
        caller_type: str,
        caller_name: str,
        user_id: Optional[str],
        system_prompt: Optional[str],
        messages: list,
        response_content: str,
        usage: dict,
        latency_ms: int,
        status: str,
        error: Optional[str] = None,
    ):
        """记录 LLM 调用到数据库"""
        from app.core.database import async_session_maker
        from app.models.llm_call_log import LLMCallLog
        import uuid

        async with async_session_maker() as session:
            log = LLMCallLog(
                id=str(uuid.uuid4()),
                model=model,
                provider=model.split("/")[0] if "/" in model else "anthropic",
                caller_type=caller_type,
                caller_name=caller_name,
                user_id=user_id,
                system_prompt=system_prompt,
                user_message=messages[-1]["content"] if messages else "",
                messages_count=len(messages),
                response_content=response_content,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=latency_ms,
                status=status,
                error_message=error,
            )
            session.add(log)
            await session.commit()

    @staticmethod
    async def update_model_stats(model_id: str, tokens: int):
        """更新模型使用统计"""
        from app.core.database import async_session_maker
        from app.models.llm_model_config import LLMModelConfig
        from sqlalchemy import update

        async with async_session_maker() as session:
            stmt = (
                update(LLMModelConfig)
                .where(LLMModelConfig.model_id == model_id)
                .values(
                    total_requests=LLMModelConfig.total_requests + 1,
                    total_tokens=LLMModelConfig.total_tokens + tokens,
                    last_used_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()


@asynccontextmanager
async def track_llm_call(
    model: str,
    caller_type: str = "api",
    caller_name: str = "unknown",
    user_id: Optional[str] = None,
):
    """
    LLM 调用追踪上下文管理器

    用法：
        async with track_llm_call("claude-sonnet-4", "agent", "email_summarizer"):
            response = await llm.chat(...)
    """
    import time

    start_time = time.time()

    try:
        # 调用前记录
        logger.info(f"[LLM] {caller_type}:{caller_name} -> {model}")

        yield

        # 调用后记录
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[LLM] 完成，耗时 {latency_ms}ms")

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[LLM] 失败: {e}")
        raise
```

**使用示例**：

```python
# 在 LLMGateway.chat() 中
async def chat(self, message: str, **kwargs) -> LLMResponse:
    # ... 构建 messages ...

    start_time = time.time()

    try:
        response = await acompletion(...)
        latency_ms = int((time.time() - start_time) * 1000)

        # 记录到数据库
        await LLMCallInterceptor.log_call(
            model=model,
            caller_type=getattr(self, "_caller_type", "api"),
            caller_name=getattr(self, "_caller_name", "unknown"),
            user_id=getattr(self, "_user_id", None),
            system_prompt=system,
            messages=messages,
            response_content=content,
            usage=usage,
            latency_ms=latency_ms,
            status="success",
        )

        # 更新模型统计
        await LLMCallInterceptor.update_model_stats(model, usage["total_tokens"])

        return LLMResponse(...)

    except Exception as e:
        # 记录错误
        await LLMCallInterceptor.log_call(..., status="error", error=str(e))
        raise
```

---

### 10.5 使用统计未实时入库

**现状**：

`llm_model_configs` 表有统计字段，但没有自动更新：

```sql
SELECT model_id, total_requests, total_tokens FROM llm_model_configs;
-- 结果：都是 0，因为没有自动更新机制
```

**建议**：

参见 [10.4 统一调用拦截器方案](#104-统一调用拦截器方案) 的解决方案，在拦截器中自动更新。

---

### 10.6 调用链追踪

**现状**：

无法追踪一个请求的完整调用链：

```
用户请求 -> API -> Agent -> LLM
                        ↓
                    Tool 调用 -> 数据库查询
```

**建议**：

添加 `trace_id` 字段：

```python
# 在 LLMCallLog 表添加
trace_id = Column(String(36), index=True)  # 追踪 ID
parent_call_id = Column(String(36), nullable=True)  # 父调用 ID

# 使用方式
import contextvars

# 创建上下文变量
current_trace_id = contextvars.ContextVar("trace_id", default=None)

# 在 FastAPI 中间件中设置
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    import uuid
    trace_id = str(uuid.uuid4())
    current_trace_id.set(trace_id)
    response = await call_next(request)
    return response

# 在 LLM 调用时自动获取
trace_id = current_trace_id.get()
```

---

### 10.7 优化建议总结与实施路线图

#### 优先级 P0（立即执行）

1. **创建 `llm_call_logs` 表**
   - 迁移文件：`alembic revision -m "add llm_call_logs table"`
   - 影响：可追溯所有 LLM 调用

2. **统一 LLM 入口为 `LLMGateway`**
   - 废弃 `LLMService`
   - API 层改用 `LLMGateway`
   - 影响：减少维护成本，统一日志

#### 优先级 P1（本周完成）

3. **添加 LLM 调用拦截器**
   - 创建 `app/llm/interceptor.py`
   - 在 `LLMGateway` 中集成
   - 影响：自动记录所有调用

4. **实时更新模型统计**
   - 每次调用自动更新 `llm_model_configs.total_requests` 和 `total_tokens`
   - 影响：准确的使用统计

#### 优先级 P2（下周完成）

5. **添加调用链追踪（Trace ID）**
   - 添加 FastAPI 中间件
   - LLM 日志记录 trace_id
   - 影响：可追踪完整调用链

6. **创建 LLM 使用统计 Dashboard**
   - 按模型统计
   - 按 Agent 统计
   - 按用户统计
   - 按时间段统计

#### 预期效果

实施后的改进：

| 指标 | 当前 | 优化后 |
|------|------|--------|
| LLM 调用可追溯性 | 无 | 100% 可查询 |
| Token 统计准确性 | 部分 | 实时准确 |
| 问题定位时间 | > 1 小时 | < 5 分钟 |
| 成本分析能力 | 无 | 完整报表 |
| 代码维护成本 | 高（两套） | 低（一套）|

#### 实施清单

**Step 1: 数据库迁移**

```bash
# 创建迁移
cd backend
alembic revision -m "add llm_call_logs table"

# 编辑迁移文件，添加表定义
# 执行迁移
alembic upgrade head
```

**Step 2: 创建模型和拦截器**

```bash
# 创建文件
touch app/models/llm_call_log.py
touch app/llm/interceptor.py
```

**Step 3: 修改 LLMGateway**

在 `app/llm/gateway.py` 的 `chat()` 方法中集成拦截器。

**Step 4: 废弃 LLMService**

```bash
# 查找所有使用 LLMService 的地方
grep -r "from app.services.llm_service import" app/

# 逐个替换为 LLMGateway
# ...

# 删除文件
rm app/services/llm_service.py
```

**Step 5: 测试验证**

```bash
# 调用一次 LLM
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "hello"}'

# 检查数据库
psql -d concord_ai -c "SELECT * FROM llm_call_logs ORDER BY created_at DESC LIMIT 1;"

# 检查模型统计是否更新
psql -d concord_ai -c "SELECT model_id, total_requests, total_tokens FROM llm_model_configs;"
```

---

### 相关文档

- [后端开发手册](BACKEND_HANDBOOK.md)
- [系统架构](../architecture/SYSTEM_OVERVIEW.md)

---

*最后更新: 2026-02-10*
*合并自: LLM_MANUAL.md (2026-02-01) + LLM_ARCHITECTURE_REVIEW.md (2026-02-01)*
