# Concord AI - 开发计划

> **基于**: FINAL_TECHNICAL_SPEC.md v1.2
> **开发模式**: 按 Phase 推进，人机协作
> **更新日期**: 2026-01-30

---

## 一、架构概览

严格遵循 TECH SPEC 的 8 层架构：

```
┌─────────────────────────────────────────────────────────────────┐
│  用户端: Web | Chatbox | 飞书 | Webhook | 邮件(IMAP)            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ① API Layer (FastAPI)                                          │
│     + Adapters (各渠道 → UnifiedEvent)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ② Message Layer (Redis Streams / Pub/Sub / Cache)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ③ Workflow Engine (Temporal)                                   │
│     流程编排 | 状态持久化 | 失败重试 | 审批等待                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ④ Agent Layer (LangGraph)                                      │
│     Agent = LLM + Prompt + Tools                                │
└─────────────────────────────────────────────────────────────────┘
                    ↓                   ↓
┌───────────────────────────┐ ┌───────────────────────────────────┐
│  ⑤ LLM Gateway (LiteLLM)  │ │  ⑥ Tools Layer                    │
│     Claude | GPT | 本地   │ │     邮件 | 数据库 | 文件 | HTTP   │
└───────────────────────────┘ │     飞书 | PDF                     │
                              └───────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑦ Storage Layer                                                │
│     PostgreSQL (+ pgvector) | Redis | 阿里云 OSS                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ⑧ Infrastructure: Docker Compose → Kubernetes                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、开发阶段（7 Phase / 10 周）

```
Phase 1 │ Phase 2 │ Phase 3   │ Phase 4 │ Phase 5   │ Phase 6   │ Phase 7
Week1-2 │ Week 3  │ Week 4-5  │ Week 6  │ Week 7    │ Week 8-9  │ Week 10
基础骨架 │Workflow │ Agent+Tool│ Chatbox │ 完整流程  │ 前端界面  │ 完善优化
```

---

## Phase 1: 基础骨架（Week 1-2）

### 目标
搭建 ① API Layer + ⑦ Storage Layer + ⑧ Infrastructure

### 任务清单

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 1.1 | 项目结构初始化 | 目录结构、.gitignore | [x] |
| 1.2 | Docker Compose | PostgreSQL + Redis + Backend | [x] |
| 1.3 | FastAPI 入口 | app/main.py, 路由结构 | [x] |
| 1.4 | 数据库底层 | core/database.py (asyncpg) | [x] |
| 1.5 | Redis 底层 | core/redis.py | [x] |
| 1.6 | Alembic 初始化 | alembic/, alembic.ini | [x] |
| 1.7 | 核心数据模型 | models/user.py | [x] |
| 1.8 | OSS 底层 | storage/oss.py | [x] |
| 1.9 | JWT 认证 | core/security.py, api/auth.py | [x] |
| 1.10 | 幂等性中间件 | core/idempotency.py | [x] |
| 1.11 | 健康检查 | api/health.py | [x] |
| 1.12 | 配置管理 | core/config.py (pydantic-settings) | [x] |
| 1.13 | 日志配置 | core/logging.py | [x] |
| 1.14 | 管理员后台 API | api/admin.py (用户管理、系统配置) | [x] |
| 1.15 | 初始管理员脚本 | scripts/create_admin.py | [x] |

> **Phase 1 已完成** ✅ (2026-01-30)

### 验收标准
```bash
docker-compose up -d
curl http://localhost:8000/health  # {"status": "ok", "database": "connected", "redis": "connected"}
curl http://localhost:8000/docs    # Swagger UI
```

---

## Phase 2: Workflow 集成（Week 3）

### 目标
搭建 ③ Workflow Engine (Temporal)

### 任务清单

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 2.1 | Temporal Server 部署 | docker-compose.yml 更新 | [x] |
| 2.2 | Temporal Worker | workflows/worker.py | [x] |
| 2.3 | Activity 基础 | workflows/activities/base.py | [x] |
| 2.4 | 第一个 Workflow（审批） | workflows/definitions/approval.py | [x] |
| 2.5 | Signal 处理（审批响应） | approve/reject signal | [x] |
| 2.6 | Temporal Schedules | workflows/schedules.py | [ ] |
| 2.7 | Workflow API | api/workflows.py (启动/查询/取消) | [x] |

> **Phase 2 已完成** ✅ (2026-01-30)
> 注：2.6 Temporal Schedules 待后续需要时实现

### 验收标准
```bash
# Temporal UI
http://localhost:8080

# 启动审批 Workflow
curl -X POST http://localhost:8000/api/workflows/approval \
  -d '{"entity_type": "quote", "entity_id": "123", "approvers": ["manager"]}'

# 发送审批 Signal
curl -X POST http://localhost:8000/api/workflows/{workflow_id}/approve
```

---

## Phase 3: Agent 层 + Tools（Week 4-5）

### 目标
搭建 ④ Agent Layer + ⑤ LLM Gateway + ⑥ Tools Layer

### 任务清单

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 3.1 | LiteLLM 集成 | llm/gateway.py | [x] |
| 3.2 | Prompt 模板 | llm/prompts/*.py | [x] |
| 3.3 | LangGraph Agent 基类 | agents/base.py | [x] |
| 3.4 | Agent 注册中心 | agents/registry.py | [x] |
| 3.5 | Tool 基类 | tools/base.py | [x] |
| 3.6 | Tool 注册中心 | tools/registry.py | [x] |
| 3.7 | 邮件底层 | storage/email.py (IMAP + SMTP) | [x] |
| 3.8 | 邮件 Tool | tools/email.py (调用 storage/email.py) | [x] |
| 3.9 | 数据库 Tool | tools/database.py (查询客户/产品) | [x] |
| 3.10 | HTTP Tool | tools/http.py (外部 API 调用) | [x] |
| 3.11 | 文件 Tool | tools/file.py (调用 storage/oss.py) | [x] |
| 3.12 | 邮件分析 Agent | agents/email_analyzer.py | [x] |
| 3.13 | Agent API | api/agents.py | [x] |

> **Phase 3 已完成** ✅ (2026-01-30)

### Tool 设计规范
```python
# tools/email.py - Tool 调用 Storage 底层实现
from tools.base import BaseTool, tool
from storage.email import smtp_send, imap_fetch  # 调用底层

class EmailTool(BaseTool):
    """邮件工具 - Agent 可调用"""

    @tool(
        name="send_email",
        description="发送一封邮件",
        parameters={
            "to": {"type": "string", "description": "收件人"},
            "subject": {"type": "string", "description": "主题"},
            "body": {"type": "string", "description": "正文"},
        }
    )
    async def send_email(self, to: str, subject: str, body: str) -> dict:
        message_id = await smtp_send(to, subject, body)  # 调用 storage 层
        return {"success": True, "message_id": message_id}

    @tool(name="read_emails", description="读取收件箱邮件")
    async def read_emails(self, folder: str = "INBOX", limit: int = 10) -> dict:
        emails = await imap_fetch(folder, limit)  # 调用 storage 层
        return {"emails": emails}
```

```python
# storage/email.py - 底层实现
import aiosmtplib
import aioimaplib

async def smtp_send(to: str, subject: str, body: str) -> str:
    """SMTP 发送邮件"""
    async with aiosmtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        # ... 构建并发送
        return message_id

async def imap_fetch(folder: str, limit: int, since: datetime = None) -> list[dict]:
    """IMAP 拉取邮件"""
    async with aioimaplib.IMAP4_SSL(settings.IMAP_HOST) as imap:
        await imap.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        # ... 拉取逻辑
        return emails
```

### 验收标准
```bash
# 调用 Agent 分析邮件
curl -X POST http://localhost:8000/api/agents/email_analyzer/run \
  -d '{"content": "我想询问产品A的价格，需要100个"}'

# 返回结构化结果
{
  "intent": "inquiry",
  "entities": {
    "product": "产品A",
    "quantity": 100
  }
}
```

---

## Phase 4: Chatbox + 飞书集成（Week 6）

### 目标
实现 Chatbox 对话功能（SSE 流式输出）+ 飞书机器人集成

### 任务清单

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 4.1 | 会话数据模型 | models/chat.py (session, message) | [x] |
| 4.2 | 对话 Agent | agents/chat_agent.py (含上下文管理) | [x] |
| 4.3 | SSE 端点 | api/chat.py (流式输出) | [x] |
| 4.4 | 消息历史 API | api/chat.py (获取历史) | [x] |
| 4.5 | 统一事件模型 | schemas/event.py (UnifiedEvent) | [x] |
| 4.6 | Adapter 基类 | adapters/base.py | [x] |
| 4.7 | 飞书适配器 | adapters/feishu.py | [x] |
| 4.8 | 飞书长连接 Worker | adapters/feishu_ws.py | [x] |
| 4.9 | 飞书配置 API | api/settings.py 更新 | [x] |
| 4.10 | 飞书配置页面 | admin/settings/feishu/page.tsx | [x] |
| 4.11 | Worker 自动启动 | main.py lifespan 集成 | [x] |

> **Phase 4 已完成** ✅ (2026-01-30)

### 关键设计
- 飞书 Worker 作为独立子进程运行（避免事件循环冲突）
- 服务启动时自动检查飞书配置，如已启用则自动启动 Worker
- LLM 设置从数据库同步加载到 Worker 进程

### 验收标准
```bash
# SSE 流式对话
curl -N http://localhost:8000/api/chat/stream \
  -d '{"session_id": "xxx", "message": "你好"}'

# 返回流式响应
data: {"type": "token", "content": "你"}
data: {"type": "token", "content": "好"}
data: {"type": "done", "message_id": "xxx"}
```

---

## Phase 5: 完整业务流程（Week 7）

### 目标
实现端到端的邮件处理流程

### 任务清单

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 5.1 | UnifiedEvent 模型 | schemas/event.py | [x] |
| 5.2 | Adapter 基类 | adapters/base.py | [x] |
| 5.3 | Email Adapter | adapters/email.py (邮件 → UnifiedEvent) | [x] |
| 5.4 | 邮件监听 | adapters/email_listener.py (APScheduler + IMAP) | [x] |
| 5.5 | 事件分发器 | messaging/dispatcher.py | [x] |
| 5.6 | Redis Streams | messaging/streams.py | [x] |
| 5.7 | 意图分类 Agent | agents/email_analyzer.py (IntentClassifierAgent) | [x] |
| 5.8 | 报价 Agent | agents/quote_agent.py | [x] |
| 5.9 | PDF Tool | tools/pdf.py | [x] |
| 5.10 | 邮件处理 Workflow | workflows/definitions/email_process.py | [x] |
| 5.11 | 邮件 Activity | workflows/activities/email.py | [x] |
| 5.12 | 事件记录表 | models/event.py | [x] |
| 5.13 | E2E 测试 | tests/e2e/test_email_flow.py | [ ] (待后续)

> **Phase 5 已完成** ✅ (2026-01-30)

### 完整数据流
```
邮件到达 (IMAP)
    ↓
Email Adapter → UnifiedEvent
    ↓
Redis Streams
    ↓
Event Dispatcher → 意图分类
    ↓
Temporal Workflow 启动
    ↓
├── 询价 → Quote Agent → 生成报价 → [审批] → 发送邮件
├── 订单 → Order Agent → 创建订单 → 通知
└── 其他 → 人工处理通知
```

### 验收标准
```bash
# 发送测试邮件到监听邮箱
# 系统自动：
# 1. 拉取邮件
# 2. 转换为 UnifiedEvent
# 3. 意图分类
# 4. 启动对应 Workflow
# 5. Agent 处理
# 6. 结果存入数据库
# 7. （如需审批）等待 Signal
# 8. 发送回复邮件
```

---

## Phase 6: 前端界面（Week 8-9）

### 目标
Next.js 前端实现

### 任务清单

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 6.1 | Next.js 初始化 | frontend/ 项目结构 | [x] |
| 6.2 | 认证页面 | app/login/page.tsx | [x] |
| 6.3 | Dashboard | app/admin/page.tsx (仪表盘) | [x] |
| 6.4 | Chatbox 组件 | components/ChatBox/ (SSE) | [x] |
| 6.5 | 审批管理 | app/admin/approvals/ | [x] |
| 6.6 | 任务列表 | app/tasks/ | [ ] (暂不需要) |
| 6.7 | 客户管理 | app/customers/ | [ ] (暂不需要) |
| 6.8 | **管理员后台** | app/admin/* (仅管理员可访问) | [x] |
| 6.9 | 管理员-用户管理 | app/admin/users/page.tsx | [x] |
| 6.10 | 管理员-系统配置 | app/admin/settings | [x] |
| 6.11 | 管理员-日志查看 | app/admin/logs | [x] |
| 6.12 | 管理员-工作流监控 | app/admin/monitor | [x] |
| 6.13 | 认证上下文 | contexts/AuthContext.tsx | [x] |
| 6.14 | API 工具库 | lib/api.ts | [x] |
| 6.15 | 首页重定向 | app/page.tsx | [x] |

> **Phase 6 已完成** ✅ (2026-01-30)

### 验收标准
- 可登录/注册
- Dashboard 显示任务统计
- Chatbox 可对话，流式显示
- 审批列表可操作
- **管理员可登录后台，普通用户无法访问**

---

## Phase 7: 完善优化（Week 10）

### 目标
测试、文档、优化

### 任务清单

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 7.1 | 单元测试 | tests/unit/ | [ ] |
| 7.2 | 集成测试 | tests/integration/ | [ ] |
| 7.3 | API 文档完善 | OpenAPI 补充描述 | [ ] |
| 7.4 | 部署文档 | docs/deployment.md | [ ] |
| 7.5 | 性能优化 | 慢查询、缓存优化 | [ ] |
| 7.6 | 错误处理完善 | 统一异常处理 | [ ] |

---

## 三、目录结构

**严格对应 8 层架构，删除模糊的 services/ 目录**

```
concord-ai/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  ① API Layer                               │
│       │  └─────────────────────────────────────────────┘
│       │
│       ├── api/                        # 路由处理
│       │   ├── auth.py
│       │   ├── health.py
│       │   ├── chat.py
│       │   ├── agents.py
│       │   └── workflows.py
│       │
│       ├── adapters/                   # 入口适配 + 监听
│       │   ├── base.py                 # 适配器基类
│       │   ├── email.py                # 邮件 → UnifiedEvent
│       │   ├── email_listener.py       # IMAP 定时拉取（调用 storage/email.py）
│       │   ├── feishu.py               # 飞书 → UnifiedEvent
│       │   └── webhook.py              # Webhook → UnifiedEvent
│       │
│       ├── core/                       # 中间件、配置、安全
│       │   ├── config.py               # pydantic-settings
│       │   ├── security.py             # JWT
│       │   ├── logging.py
│       │   └── idempotency.py          # 幂等性中间件
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  ② Message Layer                           │
│       │  └─────────────────────────────────────────────┘
│       │
│       ├── messaging/                  # Redis 消息层
│       │   ├── streams.py              # Redis Streams 操作
│       │   ├── pubsub.py               # Redis Pub/Sub
│       │   └── dispatcher.py           # 事件分发（路由到 Workflow）
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  ③ Workflow Engine (Temporal)              │
│       │  └─────────────────────────────────────────────┘
│       │
│       ├── workflows/
│       │   ├── worker.py               # Temporal Worker
│       │   ├── activities/             # Workflow Activities
│       │   │   ├── base.py
│       │   │   ├── email.py            # 邮件相关 Activity
│       │   │   └── notification.py     # 通知相关 Activity
│       │   ├── definitions/            # Workflow 定义
│       │   │   ├── approval.py
│       │   │   ├── email_process.py
│       │   │   └── quote_process.py
│       │   └── schedules.py            # Temporal Schedules
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  ④ Agent Layer (LangGraph)                 │
│       │  └─────────────────────────────────────────────┘
│       │
│       ├── agents/
│       │   ├── base.py                 # Agent 基类
│       │   ├── registry.py             # Agent 注册中心
│       │   ├── email_analyzer.py       # 邮件分析 Agent
│       │   ├── intent_classifier.py    # 意图分类 Agent
│       │   ├── quote_agent.py          # 报价 Agent
│       │   └── chat_agent.py           # 对话 Agent
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  ⑤ LLM Gateway                             │
│       │  └─────────────────────────────────────────────┘
│       │
│       ├── llm/
│       │   ├── gateway.py              # LiteLLM 统一封装
│       │   └── prompts/                # Prompt 模板
│       │       ├── intent.py
│       │       ├── quote.py
│       │       └── chat.py
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  ⑥ Tools Layer                             │
│       │  └─────────────────────────────────────────────┘
│       │
│       ├── tools/                      # Agent 可调用的工具
│       │   ├── base.py                 # Tool 基类 + 装饰器
│       │   ├── registry.py             # Tool 注册中心
│       │   ├── email.py                # 发送/读取邮件（调用 storage/email.py）
│       │   ├── database.py             # 查询客户/产品（调用 storage/database.py）
│       │   ├── http.py                 # 外部 API 调用
│       │   ├── file.py                 # 文件操作（调用 storage/oss.py）
│       │   └── pdf.py                  # PDF 生成
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  ⑦ Storage Layer                           │
│       │  └─────────────────────────────────────────────┘
│       │
│       ├── storage/                    # 外部资源访问（底层实现）
│       │   ├── database.py             # PostgreSQL 连接 + CRUD
│       │   ├── cache.py                # Redis 缓存操作
│       │   ├── oss.py                  # 阿里云 OSS
│       │   ├── vector.py               # pgvector 向量检索
│       │   └── email.py                # IMAP + SMTP 底层封装
│       │
│       ├── models/                     # SQLAlchemy 模型定义
│       │   ├── base.py
│       │   ├── user.py
│       │   ├── customer.py
│       │   ├── order.py
│       │   ├── quote.py
│       │   ├── chat.py
│       │   └── event.py
│       │
│       ├── schemas/                    # Pydantic 模式（跨层共享）
│       │   ├── user.py
│       │   ├── event.py                # UnifiedEvent
│       │   ├── chat.py
│       │   └── ...
│       │
│       │
│       │  ┌─────────────────────────────────────────────┐
│       │  │  独立模块：Ingest Pipeline                  │
│       │  └─────────────────────────────────────────────┘
│       │
│       └── ingest/                     # 文档摄入管道
│           ├── chunker.py              # 文本分块
│           ├── embedder.py             # Embedding 生成
│           └── pipeline.py             # 完整摄入流程
│
├── frontend/                           # Next.js 前端
│   └── ...
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

### 目录与架构层对应关系

| 目录 | 架构层 | 说明 |
|------|--------|------|
| `api/` | ① API Layer | 路由处理 |
| `adapters/` | ① API Layer | 入口适配、邮件监听 |
| `core/` | ① API Layer | 中间件、配置 |
| `messaging/` | ② Message Layer | Redis Streams/Pub/Sub |
| `workflows/` | ③ Workflow Engine | Temporal |
| `agents/` | ④ Agent Layer | LangGraph |
| `llm/` | ⑤ LLM Gateway | LiteLLM |
| `tools/` | ⑥ Tools Layer | Agent 可调用工具 |
| `storage/` | ⑦ Storage Layer | 外部资源访问 |
| `models/` | ⑦ Storage Layer | 数据模型定义 |
| `schemas/` | 跨层共享 | Pydantic 模式 |
| `ingest/` | 独立管道 | 文档摄入 |

### 层级调用关系

```
api/ ──────────────────────────────────────────────┐
adapters/ ─────────────────────────────────────────┤
                                                   ▼
                                            messaging/
                                                   │
                                                   ▼
                                            workflows/
                                                   │
                                                   ▼
                                             agents/
                                            ↙      ↘
                                        llm/      tools/
                                            ↘      ↙
                                            storage/
                                                   │
                                                   ▼
                                    ┌──────────────┴──────────────┐
                                    │  PostgreSQL  Redis  OSS     │
                                    │  邮件服务器   外部API        │
                                    └─────────────────────────────┘
```

---

## 四、关键设计说明

### 4.1 各层职责

| 层 | 目录 | 职责 | 调用者 |
|---|------|------|--------|
| **Adapter** | `adapters/` | 外部输入 → UnifiedEvent | API 路由、定时器 |
| **Tool** | `tools/` | Agent 可调用的能力（function calling schema） | Agent |
| **Storage** | `storage/` | 外部资源访问的底层实现 | Tool、Adapter、Workflow |

### 4.2 邮件相关代码分布

```
storage/email.py          # 底层实现：IMAP 连接、SMTP 发送
       ↑                        ↑
       │                        │
adapters/email_listener.py    tools/email.py
(定时拉取，被动触发)           (Agent 调用，主动触发)
```

```python
# storage/email.py - 底层实现
async def smtp_send(to: str, subject: str, body: str) -> str:
    """SMTP 发送邮件"""
    async with aiosmtplib.SMTP(...) as smtp:
        await smtp.send_message(message)
    return message_id

async def imap_fetch(folder: str, limit: int, since: datetime = None) -> list[dict]:
    """IMAP 拉取邮件"""
    async with aioimaplib.IMAP4_SSL(...) as imap:
        ...
    return emails
```

```python
# tools/email.py - Agent 接口
from storage.email import smtp_send, imap_fetch

class EmailTool(BaseTool):
    @tool(name="send_email", description="发送邮件")
    async def send_email(self, to: str, subject: str, body: str) -> dict:
        message_id = await smtp_send(to, subject, body)
        return {"success": True, "message_id": message_id}

    @tool(name="read_emails", description="读取邮件")
    async def read_emails(self, folder: str = "INBOX", limit: int = 10) -> dict:
        emails = await imap_fetch(folder, limit)
        return {"emails": emails}
```

```python
# adapters/email_listener.py - 定时监听
from storage.email import imap_fetch
from adapters.email import EmailAdapter

async def poll_new_emails():
    """APScheduler 定时调用"""
    emails = await imap_fetch("INBOX", limit=100, since=last_check)
    for email in emails:
        event = EmailAdapter().to_unified_event(email)
        await dispatcher.dispatch(event)
```

### 4.3 为什么删除 services/ 目录

原来的 `services/` 是个杂糅的"垃圾桶"，包含：
- llm_service.py → 现在放 `llm/gateway.py`
- storage.py → 现在放 `storage/oss.py`
- email_listener.py → 现在放 `adapters/email_listener.py`
- event_dispatcher.py → 现在放 `messaging/dispatcher.py`
- chat_service.py → 拆分到 `agents/chat_agent.py` + `storage/`
- scheduler.py → APScheduler 集成到 `adapters/email_listener.py`

**原则：每个文件都能对应到架构图的某一层，不允许模糊的"业务服务"。**

---

## 五、环境变量

```bash
# .env

# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/concord

# Redis
REDIS_URL=redis://localhost:6379/0

# Temporal
TEMPORAL_HOST=localhost:7233

# 阿里云 OSS
OSS_ACCESS_KEY=xxx
OSS_SECRET_KEY=xxx
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=concord-ai-files

# LLM
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# 邮件
IMAP_HOST=imap.qq.com
IMAP_PORT=993
IMAP_USER=your_email@qq.com
IMAP_PASSWORD=your_auth_code
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_auth_code

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## 六、开始开发

准备好后，告诉我：

```
开始 Phase 1
```

我会按顺序输出每个任务的代码。
