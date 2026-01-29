# Concord AI - MVP 开发计划

> **目标**: 邮件分析 → 订单分析 → 项目分析
> **开发模式**: 人机协作，分模块推进
> **创建日期**: 2026-01-29

---

## 一、MVP 范围定义

### 1.1 核心功能

```
┌─────────────────────────────────────────────────────────────────┐
│                         MVP 功能范围                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入：邮件（IMAP 拉取）                                         │
│     ↓                                                           │
│  处理：                                                         │
│     ├── 邮件解析（提取发件人、主题、正文、附件）                  │
│     ├── 意图分类（询价/订单/项目/其他）                          │
│     ├── 实体提取（客户、产品、数量、日期等）                      │
│     └── 结构化输出（JSON 格式）                                  │
│     ↓                                                           │
│  输出：                                                         │
│     ├── 订单信息结构化                                          │
│     ├── 项目信息结构化                                          │
│     └── 存储到数据库                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 MVP 不包含

- [ ] 前端界面（先用 API + 日志验证）
- [ ] 审批流程（先自动处理）
- [ ] 飞书/Webhook 集成（先只做邮件）
- [ ] 向量检索/RAG（Phase 2）
- [ ] 报价单生成（Phase 2）

### 1.3 成功标准

```
收到一封询价邮件 → 系统自动解析 → 提取出结构化的订单/项目信息 → 存入数据库
```

---

## 二、模块划分

### 2.1 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Module 1: 基础设施        ← 最先开发，其他模块依赖它            │
│  ├── 项目结构                                                   │
│  ├── Docker Compose                                             │
│  ├── FastAPI 骨架                                               │
│  ├── PostgreSQL + Alembic                                       │
│  └── Redis                                                      │
│           ↓                                                     │
│  Module 2: 认证与配置      ← 可以和 Module 3 并行               │
│  ├── JWT 认证                                                   │
│  ├── 环境变量管理                                               │
│  └── 日志配置                                                   │
│           ↓                                                     │
│  Module 3: LLM 服务        ← 可以和 Module 2 并行               │
│  ├── LiteLLM 集成                                               │
│  ├── Prompt 管理                                                │
│  └── 统一调用接口                                               │
│           ↓                                                     │
│  Module 4: 邮件服务                                             │
│  ├── IMAP 连接                                                  │
│  ├── 邮件拉取                                                   │
│  ├── 邮件解析                                                   │
│  └── APScheduler 定时拉取                                       │
│           ↓                                                     │
│  Module 5: 分析 Agent                                           │
│  ├── 意图分类 Agent                                             │
│  ├── 订单分析 Agent                                             │
│  └── 项目分析 Agent                                             │
│           ↓                                                     │
│  Module 6: 数据模型与存储                                        │
│  ├── 客户表                                                     │
│  ├── 订单表                                                     │
│  ├── 项目表                                                     │
│  └── 邮件记录表                                                 │
│           ↓                                                     │
│  Module 7: 端到端集成                                           │
│  └── 完整流程串联测试                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 模块详情

| 模块 | 主要文件 | 依赖 | 可并行 |
|------|----------|------|--------|
| **M1 基础设施** | docker-compose.yml, main.py, database.py | 无 | - |
| **M2 认证配置** | auth.py, config.py, logging.py | M1 | 可与 M3 并行 |
| **M3 LLM服务** | llm_service.py, prompts/ | M1 | 可与 M2 并行 |
| **M4 邮件服务** | email_service.py, scheduler.py | M1, M3 | - |
| **M5 分析Agent** | intent_agent.py, order_agent.py, project_agent.py | M3, M4 | - |
| **M6 数据模型** | models/*.py, alembic/ | M1 | 可提前做 |
| **M7 集成测试** | tests/e2e/ | 全部 | - |

---

## 三、开发计划

### 3.1 时间线概览

```
Week 1: M1 基础设施 + M6 数据模型（并行）
Week 2: M2 认证 + M3 LLM服务（并行）
Week 3: M4 邮件服务
Week 4: M5 分析 Agent
Week 5: M7 集成 + 调试优化
```

### 3.2 详细任务清单

#### Module 1: 基础设施 (Day 1-3)

| # | 任务 | 产出文件 | 状态 |
|---|------|----------|------|
| 1.1 | 创建项目目录结构 | backend/, alembic/ | [ ] |
| 1.2 | 编写 docker-compose.yml | docker-compose.yml | [ ] |
| 1.3 | FastAPI 入口和路由结构 | app/main.py, app/api/ | [ ] |
| 1.4 | 数据库连接配置 | app/core/database.py | [ ] |
| 1.5 | Redis 连接配置 | app/core/redis.py | [ ] |
| 1.6 | Alembic 初始化 | alembic/, alembic.ini | [ ] |
| 1.7 | 健康检查接口 | app/api/health.py | [ ] |

**验收标准**: `docker-compose up` 后，访问 `http://localhost:8000/health` 返回 OK

#### Module 2: 认证与配置 (Day 4-5)

| # | 任务 | 产出文件 | 状态 |
|---|------|----------|------|
| 2.1 | 环境变量管理 | app/core/config.py | [ ] |
| 2.2 | 日志配置 | app/core/logging.py | [ ] |
| 2.3 | 用户模型 | app/models/user.py | [ ] |
| 2.4 | JWT 认证实现 | app/core/security.py | [ ] |
| 2.5 | 登录/注册接口 | app/api/auth.py | [ ] |

**验收标准**: 可以注册用户、登录获取 token、用 token 访问受保护接口

#### Module 3: LLM 服务 (Day 4-5, 与 M2 并行)

| # | 任务 | 产出文件 | 状态 |
|---|------|----------|------|
| 3.1 | LiteLLM 封装 | app/services/llm_service.py | [ ] |
| 3.2 | Prompt 模板管理 | app/prompts/*.py | [ ] |
| 3.3 | LLM 调用测试接口 | app/api/llm.py | [ ] |

**验收标准**: 调用 `/api/llm/test` 可以正常返回 Claude 响应

#### Module 4: 邮件服务 (Day 6-8)

| # | 任务 | 产出文件 | 状态 |
|---|------|----------|------|
| 4.1 | IMAP 连接封装 | app/services/email/imap_client.py | [ ] |
| 4.2 | 邮件解析器 | app/services/email/parser.py | [ ] |
| 4.3 | 邮件拉取服务 | app/services/email/fetcher.py | [ ] |
| 4.4 | APScheduler 集成 | app/services/scheduler.py | [ ] |
| 4.5 | 邮件存储 | app/models/email.py | [ ] |

**验收标准**: 启动服务后，每分钟自动拉取新邮件并存入数据库

#### Module 5: 分析 Agent (Day 9-12)

| # | 任务 | 产出文件 | 状态 |
|---|------|----------|------|
| 5.1 | Agent 基类 | app/agents/base.py | [ ] |
| 5.2 | 意图分类 Agent | app/agents/intent_classifier.py | [ ] |
| 5.3 | 订单分析 Agent | app/agents/order_analyzer.py | [ ] |
| 5.4 | 项目分析 Agent | app/agents/project_analyzer.py | [ ] |
| 5.5 | Agent 调度器 | app/services/agent_dispatcher.py | [ ] |

**验收标准**: 输入邮件内容，能正确分类意图并提取结构化信息

#### Module 6: 数据模型 (可提前，Day 1-2)

| # | 任务 | 产出文件 | 状态 |
|---|------|----------|------|
| 6.1 | 客户模型 | app/models/customer.py | [ ] |
| 6.2 | 产品模型 | app/models/product.py | [ ] |
| 6.3 | 订单模型 | app/models/order.py | [ ] |
| 6.4 | 项目模型 | app/models/project.py | [ ] |
| 6.5 | 生成迁移脚本 | alembic/versions/*.py | [ ] |

**验收标准**: `alembic upgrade head` 成功创建所有表

#### Module 7: 端到端集成 (Day 13-15)

| # | 任务 | 产出文件 | 状态 |
|---|------|----------|------|
| 7.1 | 完整流程串联 | app/services/pipeline.py | [ ] |
| 7.2 | E2E 测试用例 | tests/e2e/test_email_flow.py | [ ] |
| 7.3 | 示例邮件测试 | tests/fixtures/sample_emails/ | [ ] |
| 7.4 | 日志和调试优化 | - | [ ] |

**验收标准**: 发送测试邮件 → 系统自动处理 → 数据库中出现结构化记录

---

## 四、协作模式

### 4.1 我们的配合方式

```
┌─────────────────────────────────────────────────────────────────┐
│                        协作流程                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 你：指定要开发的模块（如 "开始 M1 基础设施"）                 │
│     ↓                                                           │
│  2. 我：输出该模块的所有代码文件                                 │
│     ↓                                                           │
│  3. 你：运行代码，反馈结果                                       │
│     ├── 成功 → 进入下一个任务                                   │
│     └── 报错 → 把错误信息发给我                                  │
│     ↓                                                           │
│  4. 我：修复问题 / 继续下一个任务                                │
│     ↓                                                           │
│  5. 循环直到模块完成                                             │
│     ↓                                                           │
│  6. 你：确认模块完成，更新任务状态                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 并行开发（可选）

如果你想加快速度，可以：

```
会话 A（当前）                    会话 B（新开）
    │                                │
    ├── M1 基础设施                  │
    │       ↓                        │
    ├── M2 认证          ←──────────→ M3 LLM服务
    │       ↓                        │       ↓
    ├── M4 邮件服务                  │
    │       ↓                        │
    └── M5 分析Agent ←───────────────┘
```

并行时注意：
- M2 和 M3 可以同时开发（都只依赖 M1）
- 合并代码时我会帮你处理冲突

### 4.3 沟通模板

**开始新模块时你说：**
```
开始 M1 基础设施
```

**代码运行成功时你说：**
```
M1.1 完成，继续
```

**遇到错误时你说：**
```
M1.1 报错：
[粘贴错误信息]
```

**想跳过或调整时你说：**
```
M1.3 先跳过，后面再做
```
或
```
M4 改成用 POP3 而不是 IMAP
```

### 4.4 代码输出规范

我输出代码时会：

1. **明确文件路径**
```python
# app/core/database.py

from sqlalchemy.ext.asyncio import ...
```

2. **说明需要你做的操作**
```
请运行: docker-compose up -d
然后访问: http://localhost:8000/health
```

3. **给出验收方法**
```
预期输出: {"status": "ok", "database": "connected"}
```

---

## 五、环境准备

### 5.1 你需要准备的

在开始之前，请确认：

| 项目 | 状态 | 说明 |
|------|------|------|
| Docker Desktop | [ ] | 用于运行 PostgreSQL、Redis |
| Python 3.11+ | [ ] | 后端开发 |
| 测试邮箱 | [ ] | 用于测试邮件拉取（需开启 IMAP） |
| Claude API Key | [ ] | 用于 LLM 调用 |
| 阿里云 OSS（可选）| [ ] | 附件存储，MVP 可先用本地 |

### 5.2 测试邮箱配置

建议用一个专门的测试邮箱，需要：
- 开启 IMAP 服务
- 获取授权码（不是登录密码）
- 常见邮箱的 IMAP 服务器：
  - QQ邮箱: imap.qq.com:993
  - 163邮箱: imap.163.com:993
  - Gmail: imap.gmail.com:993

### 5.3 环境变量清单

MVP 阶段需要的环境变量：

```bash
# .env

# 数据库
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/concord

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM
ANTHROPIC_API_KEY=sk-ant-xxx

# 邮件（测试用）
IMAP_HOST=imap.qq.com
IMAP_PORT=993
IMAP_USER=your_email@qq.com
IMAP_PASSWORD=your_auth_code

# JWT
JWT_SECRET=your-secret-key-change-in-production
```

---

## 六、开始开发

当你准备好后，告诉我：

```
环境已准备好，开始 M1 基础设施
```

我会立即输出 M1 的第一个任务（1.1 创建项目目录结构）的代码。

---

## 附录：目录结构预览

```
concord-ai/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
│
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # FastAPI 入口
│       │
│       ├── api/                    # API 路由
│       │   ├── __init__.py
│       │   ├── health.py
│       │   ├── auth.py
│       │   └── llm.py
│       │
│       ├── core/                   # 核心配置
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── database.py
│       │   ├── redis.py
│       │   ├── security.py
│       │   └── logging.py
│       │
│       ├── models/                 # 数据模型
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── customer.py
│       │   ├── order.py
│       │   ├── project.py
│       │   └── email.py
│       │
│       ├── schemas/                # Pydantic 模式
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── order.py
│       │   └── project.py
│       │
│       ├── services/               # 业务服务
│       │   ├── __init__.py
│       │   ├── llm_service.py
│       │   ├── scheduler.py
│       │   └── email/
│       │       ├── __init__.py
│       │       ├── imap_client.py
│       │       ├── parser.py
│       │       └── fetcher.py
│       │
│       ├── agents/                 # 分析 Agent
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── intent_classifier.py
│       │   ├── order_analyzer.py
│       │   └── project_analyzer.py
│       │
│       └── prompts/                # Prompt 模板
│           ├── __init__.py
│           ├── intent.py
│           ├── order.py
│           └── project.py
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── unit/
    └── e2e/
        └── test_email_flow.py
```
