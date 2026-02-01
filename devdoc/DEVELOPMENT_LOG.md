# Concord AI - 开发记录

> 记录每次开发的内容、产出文件和验收状态

---

## 待改进汇总

> 记录讨论中发现的架构改进点，统一处理

### 1. ~~管理员 API 路由统一~~ ✅ 已完成 (2026-01-30)

**问题**：管理员相关的 API 路由前缀不统一

**已完成的改动**：
- 后端 `api/settings.py` 路由前缀改为 `/admin/settings`
- 前端 `lib/api.ts` 中 settingsApi 和 feishuApi 的请求路径已更新

---

### 2. Adapter Worker 统一管理

**问题**：长连接 Worker 管理分散

当前飞书长连接 Worker 是 FastAPI 启动时自动拉起的子进程（`workers/feishu_worker.py`）。如果未来接入更多渠道（钉钉、企微等），每个都有自己的长连接，管理会变得分散。

**建议**：

创建统一的 **Adapter Worker Manager**：

```python
# adapters/worker_manager.py
class AdapterWorkerManager:
    async def start_all()      # 启动所有已启用的 adapter worker
    async def stop_all()       # 停止所有 worker
    async def get_status()     # 获取各 worker 状态
    async def restart(name)    # 重启指定 worker
```

**改动范围**：
- 新建：`adapters/worker_manager.py`
- 修改：`main.py` 中的启动逻辑
- 修改：各 adapter 的 worker 统一注册

**优先级**：低（等有第二个长连接渠道时再做）

---

### 3. ~~ChatAgent 应使用 LangGraph~~ ✅ 已完成 (2026-01-30)

**问题**：ChatAgent 架构不符合技术规范

**已完成的改动**：
- ChatAgent 现在继承 BaseAgent，使用 `@register_agent` 装饰器注册
- 支持 tools 配置（默认为空，可通过 `enable_tools=True` 启用）
- 实现了 `process_output()` 抽象方法
- 保留了 Redis 上下文管理和流式输出功能
- 在 BaseAgent 中添加了 `run_stream()` 方法支持流式输出
- API 接口保持兼容，无需修改 `api/chat.py` 和 `workers/feishu_worker.py`

---

### 4. 支持多个飞书机器人

**问题**：当前只能连接一个飞书应用

配置只有一组 `app_id` + `app_secret`，Worker 是单例。

**建议**：

1. 配置模型改为列表：
```python
# 现在
feishu.app_id = "xxx"
feishu.app_secret = "xxx"

# 改成
feishu.apps = [
  {"name": "客服机器人", "app_id": "xxx", "app_secret": "xxx", "agent": "chat_agent"},
  {"name": "内部助手", "app_id": "yyy", "app_secret": "yyy", "agent": "internal_agent"},
]
```

2. Worker 管理：每个应用一个 Worker 进程

3. 前端配置页：支持添加/删除/编辑多个应用

**改动范围**：
- 修改：`models/settings.py`，支持多应用配置
- 修改：`workers/feishu_worker.py`，支持多 Worker
- 修改：`api/settings.py`，飞书配置 API
- 修改：前端飞书配置页面

**优先级**：中

---

### 5. ~~拆分 email_analyzer.py 中的 Agent~~ ✅ 已完成 (2026-01-30)

**问题**：一个文件包含多个 Agent 类

**已完成的改动**：
- 新建 `agents/intent_classifier.py`，包含 IntentClassifierAgent
- 从 `agents/email_analyzer.py` 移除 IntentClassifierAgent
- 更新 `agents/__init__.py` 导入新文件

---

### 7. ~~合并重复的飞书 Worker 实现~~ ✅ 已完成 (2026-01-31)

**问题**：飞书 Worker 存在两套重复实现

| 文件 | 行数 | 功能 |
|------|------|------|
| `adapters/feishu_ws.py` | 752 | 旧版实现，FastAPI 启动时自动拉起 |
| `workers/feishu_worker.py` | 474 | 新版实现，符合 BaseWorker 架构 |

**已完成的改动**：
- 将 `adapters/feishu_ws.py` 中的进程管理功能迁移到 `workers/feishu_worker.py`
  - `load_config_from_db()` / `load_config_from_db_sync()` - 从数据库加载配置
  - `is_feishu_enabled()` - 检查是否启用
  - `start_feishu_worker_if_enabled()` - FastAPI 启动时自动启动
  - `stop_feishu_worker()` - 停止 Worker
  - `get_feishu_worker_status()` - 获取状态
- 更新 `api/settings.py` 的 import 引用
- 归档旧文件到 `devdoc/archive/feishu_ws.py.archived`

---

*剩余 3 项待后续需要时处理（#2 Adapter Worker 统一管理、#4 支持多个飞书机器人、#6 邮件原始数据持久化）*

---

### 6. 邮件原始数据持久化

**问题**：邮件收取后未做持久化存储

当前邮件监听器收取邮件后直接转换为 `UnifiedEvent` 投递给处理流程，原始邮件内容（raw message）、附件等未做持久化。如果处理失败或需要重新处理，无法恢复原始数据。

**建议方案**：

1. **新增数据表**：

```python
# models/email_raw.py

class EmailRawMessage(Base):
    """邮件原始数据表"""
    __tablename__ = "email_raw_messages"

    id = Column(String(36), primary_key=True)  # UUID
    email_account_id = Column(Integer, ForeignKey("email_accounts.id"))
    message_id = Column(String(255), unique=True)  # IMAP Message-ID

    # 元数据
    sender = Column(String(255))
    recipients = Column(Text)  # JSON 数组
    subject = Column(String(500))
    received_at = Column(DateTime)

    # OSS 存储路径
    raw_oss_key = Column(String(500))  # emails/raw/{account_id}/{date}/{message_id}.eml

    # 状态
    processed = Column(Boolean, default=False)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class EmailAttachment(Base):
    """邮件附件表"""
    __tablename__ = "email_attachments"

    id = Column(String(36), primary_key=True)
    email_id = Column(String(36), ForeignKey("email_raw_messages.id"))

    filename = Column(String(255))
    content_type = Column(String(100))
    size = Column(Integer)

    # OSS 存储路径
    oss_key = Column(String(500))  # emails/attachments/{account_id}/{date}/{attachment_id}/{filename}

    # 是否为签名图片（通过 Content-ID 和 Content-Disposition 判断）
    is_signature = Column(Boolean, default=False)
    content_id = Column(String(255), nullable=True)  # <image001.png@xxx>

    created_at = Column(DateTime, default=datetime.utcnow)
```

2. **OSS 存储结构**：

```
emails/
├── raw/
│   └── {account_id}/
│       └── {YYYY-MM-DD}/
│           └── {message_id}.eml       # 原始 MIME 格式
└── attachments/
    └── {account_id}/
        └── {YYYY-MM-DD}/
            └── {attachment_id}/
                └── {filename}          # 实际文件
```

3. **签名图片检测逻辑**：

```python
def is_signature_image(part: email.message.Message) -> bool:
    """判断附件是否为签名图片"""
    content_disposition = part.get("Content-Disposition", "")
    content_id = part.get("Content-ID")
    content_type = part.get_content_type()

    # 条件1: 有 Content-ID（HTML 中通过 cid: 引用）
    # 条件2: Content-Disposition 为 inline
    # 条件3: 是图片类型
    if content_id and "inline" in content_disposition and content_type.startswith("image/"):
        return True
    return False
```

4. **处理流程改动**：

```
EmailListener._poll_account()
    ↓
imap_fetch() 获取邮件
    ↓
【新增】保存原始 .eml 到 OSS
    ↓
【新增】解析附件，过滤签名图片，保存到 OSS
    ↓
【新增】创建 EmailRawMessage + EmailAttachment 记录
    ↓
EmailAdapter.to_unified_event()
    ↓
EventDispatcher.dispatch()
```

**改动范围**：
- 新建：`models/email_raw.py`
- 修改：`adapters/email_listener.py`（增加持久化逻辑）
- 修改：`storage/email.py`（增加原始内容获取方法）
- 新建：数据库迁移文件

**优先级**：中（生产环境部署前需完成）

---

## 2026-01-30 - 待改进项处理 + 整体测试

### 开发内容

完成待改进项并进行全面功能测试：

1. **ChatAgent 重构**
   - 继承 BaseAgent，使用 `@register_agent` 装饰器
   - 支持 tools 配置（默认空，可启用）
   - 在 BaseAgent 添加 `run_stream()` 方法
   - 保留 Redis 上下文管理和流式输出

2. **API 路由统一**
   - `/settings/*` → `/admin/settings/*`
   - 前后端同步更新

3. **Agent 文件拆分**
   - 新建 `agents/intent_classifier.py`
   - 从 email_analyzer.py 移出 IntentClassifierAgent

4. **Bug 修复**
   - `AgentInfo.model` 类型改为 `Optional[str]`（修复 /api/agents 500 错误）

### 修改文件清单

```
backend/app/
├── agents/
│   ├── base.py                 # 添加 run_stream() 方法
│   ├── chat_agent.py           # 重写，继承 BaseAgent
│   ├── intent_classifier.py    # 新建，从 email_analyzer 拆分
│   ├── email_analyzer.py       # 移除 IntentClassifierAgent
│   └── __init__.py             # 添加 intent_classifier 导入
├── api/
│   ├── settings.py             # 路由前缀改为 /admin/settings
│   └── agents.py               # AgentInfo.model 改为 Optional
└── main.py                     # 更新路由注释

frontend/src/lib/
└── api.ts                      # settingsApi/feishuApi 路径更新
```

### 整体功能测试

#### 页面测试（11 个路由）
| 页面 | 状态 |
|------|------|
| / (首页重定向) | ✅ |
| /login | ✅ |
| /admin | ✅ |
| /admin/users | ✅ |
| /admin/approvals | ✅ |
| /admin/llm | ✅ |
| /admin/monitor | ✅ |
| /admin/logs | ✅ |
| /admin/settings | ✅ |
| /admin/settings/feishu | ✅ |
| /chat | ✅ |

#### API 测试（22 个端点）
| 类别 | 端点 | 状态 |
|------|------|------|
| 认证 | POST /api/auth/login | ✅ |
| 认证 | GET /api/auth/me | ✅ |
| 用户 | GET /admin/users | ✅ |
| 用户 | POST /admin/users | ✅ |
| 用户 | POST /admin/users/{id}/toggle | ✅ |
| 用户 | POST /admin/users/{id}/reset-password | ✅ |
| 用户 | DELETE /admin/users/{id} | ✅ |
| 统计 | GET /admin/stats | ✅ |
| 设置 | GET /admin/settings/llm | ✅ |
| 设置 | PUT /admin/settings/llm | ✅ |
| 设置 | GET /admin/settings/email | ✅ |
| 设置 | GET /admin/settings/feishu | ✅ |
| 设置 | GET /admin/settings/feishu/status | ✅ |
| 监控 | GET /admin/monitor/summary | ✅ |
| 监控 | GET /admin/monitor/workflows | ✅ |
| Agent | GET /api/agents | ✅ |
| Agent | POST /api/agents/classify/intent | ✅ |
| Chat | POST /api/chat/sessions | ✅ |
| Chat | GET /api/chat/sessions | ✅ |
| Chat | GET /api/chat/sessions/{id}/messages | ✅ |
| Chat | DELETE /api/chat/sessions/{id} | ✅ |

#### 功能验证
- ✅ 用户登录/登出
- ✅ 用户 CRUD 操作
- ✅ LLM 配置保存/更新
- ✅ 飞书 Worker 自动启动
- ✅ Agent 意图分类执行
- ✅ 会话创建/删除

### 文档更新

更新 `devdoc/MANUAL.md`：

1. **后端项目结构**
   - 添加 `chat_agent.py`, `intent_classifier.py`, `quote_agent.py`
   - 添加 `adapters/` 目录（飞书适配器）
   - 添加 `chat.py`, `admin_monitor.py` API 路由
   - 添加更多 models 和 schemas

2. **前端项目结构**
   - 添加 `/admin/llm`, `/admin/monitor`, `/admin/settings/feishu` 页面

3. **API 路由表**
   - 补全所有路由文件和前缀
   - 特别说明 settings 在 `/admin/settings/*` 下

4. **新增 Agent 架构章节 (8.5)**
   - BaseAgent 基类说明
   - `@register_agent` 注册机制
   - AgentResult 返回结构
   - 已注册 Agent 列表
   - 添加新 Agent 的步骤

5. **ChatAgent 文档更新**
   - 说明继承 BaseAgent 的新架构
   - 类结构和支持的方法

6. **设置 API 路径修正**
   - 所有 `/settings/*` 改为 `/admin/settings/*`

---

## 2026-01-29 - M1 基础设施搭建

### 开发内容

完成 MVP 开发计划中的 **Module 1: 基础设施**，包括：
- 项目目录结构创建
- Docker Compose 配置
- FastAPI 框架搭建
- 数据库连接配置（PostgreSQL + Alembic）
- Redis 连接配置
- 健康检查接口
- 运维脚本集合

### 产出文件清单

#### 项目根目录
```
Concord_AI/
├── .gitignore                 # Git 忽略配置
├── .env.example               # 环境变量模板
├── docker-compose.yml         # Docker 容器编排
└── README.md                  # 项目说明
```

#### 后端代码 (backend/)
```
backend/
├── requirements.txt           # Python 依赖
├── alembic.ini               # Alembic 配置
├── alembic/
│   ├── env.py                # Alembic 环境（异步支持）
│   ├── script.py.mako        # 迁移脚本模板
│   └── versions/             # 迁移版本目录
│
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI 入口
    ├── api/
    │   ├── __init__.py
    │   └── health.py         # 健康检查接口
    ├── core/
    │   ├── __init__.py
    │   ├── config.py         # 配置管理（Pydantic Settings）
    │   ├── database.py       # 数据库连接（AsyncPG + SQLAlchemy）
    │   └── redis.py          # Redis 连接
    ├── models/
    │   └── __init__.py
    ├── schemas/
    │   └── __init__.py
    ├── services/
    │   ├── __init__.py
    │   └── email/
    │       └── __init__.py
    ├── agents/
    │   └── __init__.py
    └── prompts/
        └── __init__.py
```

#### 运维脚本 (scripts/)
```
scripts/
├── setup.sh                  # 一键部署
├── start.sh                  # 启动服务
├── stop.sh                   # 停止服务
├── restart.sh                # 重启服务
├── status.sh                 # 查看状态
├── logs.sh                   # 查看日志
├── migrate.sh                # 数据库迁移
└── reset-db.sh               # 清空数据库
```

#### 测试目录 (tests/)
```
tests/
├── __init__.py
├── unit/                     # 单元测试
├── e2e/                      # 端到端测试
└── fixtures/                 # 测试数据
```

### 关键代码说明

#### 1. FastAPI 入口 (app/main.py)
- 使用 `lifespan` 管理应用生命周期
- 启动时连接 Redis
- 关闭时清理资源
- 配置 CORS 中间件

#### 2. 数据库配置 (app/core/database.py)
- 使用 `asyncpg` 异步驱动
- SQLAlchemy 2.0 异步模式
- 提供 `get_db` 依赖注入

#### 3. Redis 配置 (app/core/redis.py)
- 封装 `RedisClient` 类
- 提供常用方法（get/set/delete/exists）
- 支持连接池

#### 4. 健康检查 (app/api/health.py)
- `/health` - 基础健康检查
- `/health/detailed` - 详细检查（含数据库和 Redis 状态）

### 验收标准

| 检查项 | 预期结果 | 状态 |
|--------|----------|------|
| `docker-compose up -d` | PostgreSQL 和 Redis 容器启动 | [ ] |
| `./scripts/setup.sh` | 一键完成环境配置 | [ ] |
| `./scripts/start.sh` | 服务正常启动 | [ ] |
| `http://localhost:8000/health` | 返回 `{"status": "ok"}` | [ ] |
| `http://localhost:8000/health/detailed` | 显示数据库和 Redis 连接状态 | [ ] |
| `http://localhost:8000/docs` | 显示 Swagger API 文档 | [ ] |

### 下一步计划

- [ ] M2: 认证与配置（JWT 登录）
- [ ] M3: LLM 服务（LiteLLM 集成）
- [ ] M6: 数据模型（用户、客户、订单、项目表）

---

## 2026-01-29 - Git 初始化与文档完善

### 开发内容

1. **Git 仓库初始化**
   - 初始化 Git 仓库
   - 首次提交所有代码

2. **版本管理文档**
   - 创建 VERSION_MANIFEST.md 记录所有依赖版本

### Git 提交记录

```
commit 1efe8d9
Author: alexli
Date:   2026-01-29

feat: initialize project with M1 infrastructure

- Project structure with FastAPI backend
- Docker Compose for PostgreSQL and Redis
- Database connection with async SQLAlchemy + Alembic
- Redis client wrapper
- Health check endpoints
- Environment configuration with Pydantic Settings
- DevOps scripts (setup, start, stop, restart, migrate, etc.)
- Technical documentation (spec, MVP plan, dev log)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### 产出文件

| 文件 | 说明 |
|------|------|
| `devdoc/VERSION_MANIFEST.md` | 版本清单文档 |

### VERSION_MANIFEST.md 内容概要

记录了以下版本信息：
- **运行环境**: Python 3.11+, Docker 24+
- **容器镜像**: PostgreSQL 16-alpine, Redis 7-alpine
- **Python 依赖**: 20+ 个包的版本要求
- **未来依赖**: Phase 2 计划使用的包
- **前端依赖**: Next.js 14+ 等（未来）
- **版本更新策略**: 更新频率和流程

---

## 2026-01-29 - 文档中文化

### 开发内容

将所有运维脚本和项目 README 翻译为中文，提升中文用户体验。

### 修改文件

| 文件 | 改动说明 |
|------|----------|
| `README.md` | 完全中文化 |
| `scripts/setup.sh` | 注释和输出改为中文 |
| `scripts/start.sh` | 注释和输出改为中文 |
| `scripts/stop.sh` | 注释和输出改为中文 |
| `scripts/restart.sh` | 注释和输出改为中文 |
| `scripts/status.sh` | 注释和输出改为中文 |
| `scripts/logs.sh` | 注释和输出改为中文 |
| `scripts/migrate.sh` | 注释和输出改为中文 |
| `scripts/reset-db.sh` | 注释和输出改为中文 |

### Git 提交记录

```
commit 8e438d5
Author: alexli
Date:   2026-01-29

docs: 将脚本和 README 翻译为中文

- README.md 完全中文化
- 所有 scripts/ 目录下的脚本注释和输出改为中文
- 包括: setup.sh, start.sh, stop.sh, restart.sh, status.sh, logs.sh, migrate.sh, reset-db.sh

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## 开发约定

### 文件命名规范
- Python 文件：小写 + 下划线（snake_case）
- 类名：大驼峰（PascalCase）
- 函数/变量：小写 + 下划线（snake_case）

### Git 提交规范
```
feat: 新功能
fix: 修复 bug
docs: 文档更新
refactor: 重构
test: 测试相关
chore: 构建/工具相关
```

### 模块开发流程
1. 创建代码文件
2. 运行验证
3. 记录到本文档
4. 标记任务完成

---

## 2026-01-30 - M2 认证与配置 + M3 LLM 服务

### 开发内容

并行完成 MVP 开发计划中的：
- **M2: 认证与配置** - JWT 认证、日志系统、用户模型
- **M3: LLM 服务** - LiteLLM 集成、Prompt 模板、统一调用接口

### 产出文件清单

#### 核心模块 (app/core/)
```
app/core/
├── config.py      # 扩展：添加日志和 LLM 配置
├── logging.py     # 新建：日志系统（彩色输出 + JSON 格式）
└── security.py    # 新建：JWT 认证（密码哈希 + Token）
```

#### 数据模型 (app/models/)
```
app/models/
└── user.py        # 新建：用户模型（id, email, password_hash, name, role）
```

#### Schema 层 (app/schemas/)
```
app/schemas/
└── user.py        # 新建：用户相关的 Pydantic Schema
```

#### 服务层 (app/services/)
```
app/services/
└── llm_service.py # 新建：LLM 统一调用服务
```

#### Prompt 模板 (app/prompts/)
```
app/prompts/
├── __init__.py    # 更新：导出所有 Prompt
├── base.py        # 新建：Prompt 基类和通用模板
├── intent.py      # 新建：意图分类 Prompt
└── extraction.py  # 新建：实体提取 Prompt
```

#### API 路由 (app/api/)
```
app/api/
├── auth.py        # 新建：认证接口（注册/登录/刷新/获取用户）
└── llm.py         # 新建：LLM 测试接口（对话/流式/分类）
```

#### 数据库迁移 (alembic/)
```
alembic/
├── env.py                                    # 更新：导入 User 模型
└── versions/
    └── 4c9b36b333c5_create_users_table.py   # 新建：用户表迁移
```

### 关键代码说明

#### 1. 日志系统 (app/core/logging.py)
- **设计选择**：使用 Python 标准库 logging（为 Temporal SDK 兼容做准备）
- **ColoredFormatter**：开发环境彩色输出，便于调试
- **JSONFormatter**：生产环境 JSON 格式，便于 ELK 等日志分析
- **RequestLoggingMiddleware**：记录每个 HTTP 请求的方法、路径、耗时、状态码
- **log_execution 装饰器**：自动记录函数执行开始/结束/耗时

#### 2. JWT 认证 (app/core/security.py)
- **密码哈希**：bcrypt 算法，自动加盐
- **双 Token 机制**：
  - Access Token：15 分钟有效，用于 API 访问
  - Refresh Token：7 天有效，用于刷新 Access Token
- **依赖注入**：
  - `get_current_user`：获取当前登录用户
  - `get_current_admin_user`：获取管理员用户

#### 3. 用户模型 (app/models/user.py)
- **SQLAlchemy 2.0 风格**：使用 `Mapped` 类型注解
- **UUID 主键**：使用字符串格式的 UUID
- **自动时间戳**：`created_at` 自动填充，`updated_at` 更新时自动更新

#### 4. LLM 服务 (app/services/llm_service.py)
- **LiteLLM 封装**：统一调用 Claude、GPT 等模型
- **流式输出**：支持 SSE 实时返回
- **自动日志**：记录模型、Token 消耗、延迟等指标
- **依赖注入**：通过 `get_llm_service` 注入

#### 5. Prompt 模板系统 (app/prompts/)
- **PromptTemplate 类**：支持变量替换 `{variable}`
- **SystemPrompt 类**：结构化系统提示词（角色、指令、约束、示例）
- **预定义模板**：
  - `INTENT_CLASSIFIER_PROMPT`：意图分类
  - `ENTITY_EXTRACTION_PROMPT`：实体提取
  - `INQUIRY_EXTRACTION_PROMPT`：询价邮件提取
  - `ORDER_EXTRACTION_PROMPT`：订单信息提取

### 新增 API 接口

#### 认证接口 (/api/auth)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录，返回 Token |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET | `/api/auth/me` | 获取当前用户信息 |

#### LLM 接口 (/api/llm)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/llm/chat` | 普通对话，需认证 |
| POST | `/api/llm/stream` | 流式对话（SSE），需认证 |
| POST | `/api/llm/classify` | 意图分类，需认证 |

### 验收命令

```bash
# 1. 启动服务
./scripts/start.sh

# 2. 注册用户
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "123456", "name": "测试用户"}'

# 3. 登录获取 Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "123456"}'

# 4. 用 Token 访问受保护接口
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <access_token>"

# 5. 测试 LLM 对话（需要配置 ANTHROPIC_API_KEY）
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"message": "你好，请介绍一下自己"}'
```

### 下一步计划

- [ ] **管理员后台 API** (`api/admin.py`) - 仅管理员可访问
- [ ] **创建初始管理员脚本** (`scripts/create_admin.py`)
- [ ] M4: 邮件服务（IMAP 收件、邮件解析）
- [ ] M5: Agent 框架（LangGraph 集成）
- [ ] M6: 数据模型（客户、订单、项目表）

### 代码结构待重构（Phase 3 前完成）

当前结构与 FINAL_TECHNICAL_SPEC.md 规范有差异，计划在后续统一重构：

| 当前位置 | 规范位置 | 说明 |
|----------|----------|------|
| `core/database.py` | `storage/database.py` | 数据库连接 |
| `core/redis.py` | `storage/cache.py` | Redis 连接 |
| `services/llm_service.py` | `llm/gateway.py` | LLM 服务 |
| `prompts/` | `llm/prompts/` | Prompt 模板 |
| `services/` | 删除 | 不应存在此目录 |

---

## 2026-01-30 - Phase 1 完成 + 前端管理后台

### 开发内容

完成 Phase 1 剩余任务，并提前开发部分 Phase 6 前端界面：

1. **管理员后台 API** (`api/admin.py`)
2. **创建初始管理员脚本** (`scripts/create_admin.py`)
3. **阿里云 OSS 存储模块** (`storage/oss.py`)
4. **幂等性中间件** (`core/idempotency.py`)
5. **前端管理后台界面** (Next.js)
6. **前端首页重定向修复**

### 产出文件清单

#### 后端新增文件
```
backend/app/
├── api/
│   └── admin.py              # 管理员 API（用户管理、系统统计）
├── core/
│   └── idempotency.py        # 幂等性中间件（三层防护）
└── storage/
    ├── __init__.py           # 存储层模块导出
    └── oss.py                # 阿里云 OSS 文件存储

scripts/
└── create_admin.py           # 创建初始管理员脚本
```

#### 前端新增文件
```
frontend/src/
├── app/
│   ├── page.tsx              # 首页（自动重定向）
│   ├── login/
│   │   └── page.tsx          # 登录页
│   └── admin/
│       ├── layout.tsx        # 管理后台布局（侧边栏+顶栏）
│       ├── page.tsx          # 仪表盘（系统统计）
│       └── users/
│           └── page.tsx      # 用户管理（增删改查）
├── contexts/
│   └── AuthContext.tsx       # 认证上下文（登录状态管理）
└── lib/
    └── api.ts                # API 工具库（封装 fetch）
```

### 关键代码说明

#### 1. 管理员后台 API (`api/admin.py`)
- **系统统计** `/admin/stats`: 用户总数、活跃用户、今日新增
- **用户列表** `/admin/users`: 分页、搜索、筛选
- **用户 CRUD**: 创建、更新、删除用户
- **用户操作**: 启用/禁用、重置密码
- **权限检查**: 所有接口需要 `role=admin`

#### 2. 阿里云 OSS 存储 (`storage/oss.py`)
- **文件上传**: `upload()`, `upload_file()`
- **文件下载**: `download()`, `download_to_file()`
- **文件管理**: `delete()`, `exists()`, `list_objects()`
- **签名 URL**: `get_signed_url()` 生成临时访问链接
- **异步支持**: 使用 `asyncio.to_thread()` 避免阻塞

#### 3. 幂等性中间件 (`core/idempotency.py`)
实现三层防护：
- **第一层**: Request ID 快速去重（Redis 缓存）
- **第二层**: Redis 分布式锁（防止并发重复）
- **第三层**: 数据库唯一约束（最终保障）

使用方式：
```python
# 方式一：中间件（自动处理带 X-Idempotency-Key 的请求）
app.add_middleware(IdempotencyMiddleware)

# 方式二：装饰器
@idempotent(key_prefix="create_order")
async def create_order(order_data: dict):
    ...

# 方式三：手动检查
if not await check_idempotency("order", order_id):
    return {"message": "订单已处理"}
```

#### 4. 前端认证上下文 (`AuthContext.tsx`)
- 全局管理登录状态
- 自动检查 Token 有效性
- 提供 `login()`, `logout()` 方法

#### 5. 前端 API 工具库 (`lib/api.ts`)
- 封装 fetch，自动处理 Token
- 提供认证 API（登录、获取用户）
- 提供管理员 API（统计、用户管理）

### 新增 API 接口

#### 管理员接口 (/admin)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/stats` | 系统统计信息 |
| GET | `/admin/users` | 用户列表（分页、搜索） |
| GET | `/admin/users/{id}` | 获取单个用户 |
| POST | `/admin/users` | 创建新用户 |
| PUT | `/admin/users/{id}` | 更新用户信息 |
| DELETE | `/admin/users/{id}` | 删除用户 |
| POST | `/admin/users/{id}/toggle` | 启用/禁用用户 |
| POST | `/admin/users/{id}/reset-password` | 重置密码 |

### 环境变量更新

在 `.env` 中新增：
```bash
# 阿里云 OSS
OSS_ACCESS_KEY_ID=xxx
OSS_ACCESS_KEY_SECRET=xxx
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=concord-ai-files
```

### Phase 1 任务完成状态

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 1.1 | 项目结构初始化 | 目录结构、.gitignore | [x] |
| 1.2 | Docker Compose | PostgreSQL + Redis | [x] |
| 1.3 | FastAPI 入口 | app/main.py | [x] |
| 1.4 | 数据库底层 | core/database.py | [x] |
| 1.5 | Redis 底层 | core/redis.py | [x] |
| 1.6 | Alembic 初始化 | alembic/ | [x] |
| 1.7 | 核心数据模型 | models/user.py | [x] |
| 1.8 | OSS 底层 | storage/oss.py | [x] |
| 1.9 | JWT 认证 | core/security.py | [x] |
| 1.10 | 幂等性中间件 | core/idempotency.py | [x] |
| 1.11 | 健康检查 | api/health.py | [x] |
| 1.12 | 配置管理 | core/config.py | [x] |
| 1.13 | 日志配置 | core/logging.py | [x] |
| 1.14 | 管理员后台 API | api/admin.py | [x] |
| 1.15 | 初始管理员脚本 | scripts/create_admin.py | [x] |

### 验收命令

```bash
# 1. 启动服务
docker-compose up -d
./scripts/start.sh

# 2. 创建管理员
python scripts/create_admin.py

# 3. 启动前端
cd frontend && npm run dev

# 4. 访问测试
# - 首页: http://localhost:3000 （自动跳转）
# - 登录: http://localhost:3000/login
# - 后台: http://localhost:3000/admin

# 5. 测试账户
# 邮箱: admin@concordai.com
# 密码: admin123456
```

### 下一步计划

**Phase 2: Workflow 集成**
- [ ] 2.1 Temporal Server 部署
- [ ] 2.2 Temporal Worker 实现
- [ ] 2.3 Activity 基础
- [ ] 2.4 第一个 Workflow（审批）
- [ ] 2.5 Signal 处理
- [ ] 2.6 Temporal Schedules
- [ ] 2.7 Workflow API

### 代码结构待重构（Phase 3 前完成）

当前结构与 FINAL_TECHNICAL_SPEC.md 规范仍有差异：

| 当前位置 | 规范位置 | 说明 |
|----------|----------|------|
| `core/database.py` | `storage/database.py` | 数据库连接 |
| `core/redis.py` | `storage/cache.py` | Redis 连接 |
| `services/llm_service.py` | `llm/gateway.py` | LLM 服务 |
| `prompts/` | `llm/prompts/` | Prompt 模板 |
| `services/` | 删除 | 不应存在此目录 |

---

## 2026-01-30 - Phase 2: Workflow 集成（Temporal）

### 开发内容

完成 Phase 2 的工作流集成，包括：
- **Temporal Server 部署**：docker-compose 配置
- **Temporal Worker**：监听任务队列，执行 Workflow 和 Activity
- **Activity 基础模块**：通用 Activity（通知、日志）
- **审批工作流**：支持 Signal（通过/拒绝）和 Query（状态查询）
- **Workflow API**：HTTP 接口管理工作流

### 产出文件清单

#### Docker 配置
```
docker-compose.yml    # 新增 Temporal Server + UI 服务
```

#### 工作流模块 (app/workflows/)
```
app/workflows/
├── __init__.py                    # 模块导出
├── worker.py                      # Temporal Worker（监听队列执行任务）
├── client.py                      # Temporal Client（启动/查询/发信号）
├── activities/
│   ├── __init__.py                # Activity 导出
│   └── base.py                    # 基础 Activity（通知、日志）
└── definitions/
    ├── __init__.py                # Workflow 导出
    └── approval.py                # 审批工作流（Signal + Query）
```

#### API 路由
```
app/api/
└── workflows.py                   # Workflow HTTP API
```

### 关键代码说明

#### 1. Temporal Server 部署 (docker-compose.yml)
- **temporalio/auto-setup:1.24.2**: 自动创建数据库表
- **temporalio/ui:2.26.2**: Web 界面管理工作流
- 开发环境使用 SQLite 存储，生产环境建议 PostgreSQL

#### 2. Temporal Worker (workflows/worker.py)
```python
# 注册 Workflow 和 Activity
worker = Worker(
    client=client,
    task_queue="concord-main-queue",
    workflows=[ApprovalWorkflow],
    activities=[send_notification, log_workflow_event],
)

# 运行 Worker
await worker.run()
```

启动方式：
```bash
python -m app.workflows.worker
```

#### 3. 审批工作流 (workflows/definitions/approval.py)
```python
@workflow.defn
class ApprovalWorkflow:
    @workflow.run
    async def run(self, request: ApprovalRequest) -> ApprovalResult:
        # 1. 发送通知
        await workflow.execute_activity(send_notification, ...)
        # 2. 等待审批或超时
        await workflow.wait_condition(lambda: self._status != PENDING, timeout=24h)
        # 3. 返回结果
        return ApprovalResult(...)

    @workflow.signal
    async def approve(self, approver_id: str, comment: str):
        self._status = ApprovalStatus.APPROVED

    @workflow.signal
    async def reject(self, approver_id: str, comment: str):
        self._status = ApprovalStatus.REJECTED

    @workflow.query
    def get_status(self) -> ApprovalStatus:
        return self._status
```

#### 4. Temporal Client (workflows/client.py)
```python
# 启动工作流
handle = await start_workflow(
    ApprovalWorkflow.run,
    args=(approval_request,),
    id=f"approval-{request_id}",
)

# 发送信号
await handle.signal(ApprovalWorkflow.approve, approver_id, "同意")

# 查询状态
status = await handle.query(ApprovalWorkflow.get_status)
```

#### 5. 基础 Activity (workflows/activities/base.py)
- **send_notification**: 发送通知（邮件/短信/Webhook）
- **log_workflow_event**: 记录工作流事件

### 新增 API 接口

#### 工作流接口 (/api/workflows)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workflows/approval` | 创建审批工作流 |
| GET | `/api/workflows/{id}/status` | 查询工作流状态 |
| POST | `/api/workflows/{id}/approve` | 审批通过 |
| POST | `/api/workflows/{id}/reject` | 审批拒绝 |
| POST | `/api/workflows/{id}/cancel` | 取消工作流 |

### 配置更新

#### 环境变量 (config.py)
```python
# Temporal 配置
TEMPORAL_HOST: str = "localhost:7233"
TEMPORAL_NAMESPACE: str = "default"
TEMPORAL_TASK_QUEUE: str = "concord-main-queue"
```

#### 依赖更新 (requirements.txt)
```
temporalio>=1.4.0
```

### Phase 2 任务完成状态

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 2.1 | Temporal Server 部署 | docker-compose.yml 更新 | [x] |
| 2.2 | Temporal Worker | workflows/worker.py | [x] |
| 2.3 | Activity 基础 | workflows/activities/base.py | [x] |
| 2.4 | 第一个 Workflow（审批）| workflows/definitions/approval.py | [x] |
| 2.5 | Signal 处理（审批响应）| 集成在 approval.py | [x] |
| 2.6 | Temporal Schedules | 留待后续 | [ ] |
| 2.7 | Workflow API | api/workflows.py | [x] |

### 验收命令

```bash
# 1. 启动 Temporal Server
docker-compose up -d temporal temporal-ui

# 2. 等待 Temporal 启动（约30秒）
docker-compose logs -f temporal

# 3. 访问 Temporal UI
open http://localhost:8080

# 4. 启动 Temporal Worker（新终端）
cd backend
python -m app.workflows.worker

# 5. 测试工作流 API（需要先登录获取 Token）
# 创建审批工作流
curl -X POST http://localhost:8000/api/workflows/approval \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "request_id": "order-001",
    "request_type": "order_approval",
    "approver_id": "user-001",
    "approver_email": "approver@example.com",
    "title": "订单金额超限审批",
    "description": "订单金额 ¥50,000 超过限额",
    "amount": 50000
  }'

# 查询状态
curl http://localhost:8000/api/workflows/approval-order-001/status \
  -H "Authorization: Bearer <token>"

# 审批通过
curl -X POST http://localhost:8000/api/workflows/approval-order-001/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"comment": "同意"}'
```

### 下一步计划

**Phase 3: Agent 框架**
- [ ] 3.1 LangGraph 集成
- [ ] 3.2 Agent 基类
- [ ] 3.3 Tool 注册机制
- [ ] 3.4 第一个 Agent（邮件处理）

---

## 2026-01-30 - 运维脚本升级

### 开发内容

升级所有运维脚本，支持 Temporal 服务和前端的一键操作：
- 支持 Temporal Server 和 Worker 的启动/停止
- 支持前端服务的启动/停止
- 添加后台运行模式
- 添加应用日志管理

### 修改文件

| 文件 | 改动说明 |
|------|----------|
| `scripts/setup.sh` | 添加 Temporal 等待、前端依赖安装 |
| `scripts/start.sh` | 添加 Worker/前端启动、后台模式 |
| `scripts/stop.sh` | 添加 Worker/前端停止、--keep 参数 |
| `scripts/restart.sh` | 完整重启所有服务 |
| `scripts/status.sh` | 添加 Temporal/Worker/前端状态检查 |
| `scripts/logs.sh` | 添加应用日志查看支持 |

### 新增功能

#### 启动参数

```bash
./scripts/start.sh           # 启动所有服务（API 前台）
./scripts/start.sh --bg      # 所有服务后台运行
./scripts/start.sh --api     # 只启动后端 API
./scripts/start.sh --worker  # 只启动 Temporal Worker
./scripts/start.sh --frontend # 只启动前端
```

#### 日志查看

```bash
./scripts/logs.sh api        # FastAPI 日志
./scripts/logs.sh worker     # Temporal Worker 日志
./scripts/logs.sh frontend   # 前端日志
./scripts/logs.sh temporal   # Temporal Server 日志
./scripts/logs.sh all        # 所有应用日志
```

#### 日志文件位置

```
logs/
├── api.log        # FastAPI 后端日志
├── worker.log     # Temporal Worker 日志
└── frontend.log   # Next.js 前端日志
```

### 文档更新

- `MANUAL.md`: 添加第 16 章运维脚本文档

---

## 2026-01-30 - Phase 3: Agent 层 + Tools 完成

### 开发内容

完成 Phase 3 的 Agent 框架和 Tools 层，包括：
- **LLM Gateway**：使用 LiteLLM 统一多模型调用
- **Prompt 模板管理**：支持数据库管理 + 代码默认值
- **Agent 基类**：基于 LangGraph 的状态机式 Agent
- **Tool 基类**：自动生成 OpenAI/Anthropic function calling schema
- **4 个 Tool 实现**：数据库、HTTP、邮件、文件
- **2 个 Agent 实现**：邮件分析、意图分类
- **Agent API**：HTTP 接口调用 Agent

### 产出文件清单

#### LLM 网关 (app/llm/)
```
app/llm/
├── __init__.py                 # 模块导出
├── gateway.py                  # LiteLLM 封装（chat, stream, tools, json）
└── prompts/
    ├── __init__.py
    ├── defaults.py             # 默认 Prompt 模板
    └── manager.py              # Prompt 管理器（DB + 缓存）
```

#### Agent 层 (app/agents/)
```
app/agents/
├── __init__.py                 # 导入以触发注册
├── base.py                     # Agent 基类（LangGraph 状态机）
├── registry.py                 # Agent 注册中心
└── email_analyzer.py           # 邮件分析 + 意图分类 Agent
```

#### Tools 层 (app/tools/)
```
app/tools/
├── __init__.py                 # 导入以触发注册
├── base.py                     # Tool 基类 + @tool 装饰器
├── registry.py                 # Tool 注册中心
├── database.py                 # 数据库查询 Tool
├── http.py                     # HTTP 请求 Tool
├── email.py                    # 邮件收发 Tool
└── file.py                     # 文件操作 Tool
```

#### 存储层 (app/storage/)
```
app/storage/
└── email.py                    # IMAP/SMTP 底层实现
```

#### 数据模型 (app/models/)
```
app/models/
└── prompt.py                   # Prompt 模型（数据库存储）
```

#### API 路由 (app/api/)
```
app/api/
└── agents.py                   # Agent HTTP API
```

### 关键代码说明

#### 1. LLM Gateway (llm/gateway.py)
```python
class LLMGateway:
    async def chat(messages, model=None, **kwargs) -> str
    async def chat_stream(messages, model=None, **kwargs) -> AsyncIterator[str]
    async def chat_with_tools(messages, tools, model=None) -> dict
    async def chat_json(messages, model=None) -> dict
```

使用 LiteLLM 支持多种模型：
- Claude: claude-3-opus, claude-3-sonnet, claude-3-haiku
- GPT: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- 其他 LiteLLM 支持的模型

#### 2. Agent 基类 (agents/base.py)
基于 LangGraph 构建状态机：
```
START → think → should_continue? → execute_tools → think → ... → output → END
```

使用方式：
```python
@register_agent
class EmailAnalyzerAgent(BaseAgent):
    name = "email_analyzer"
    description = "分析邮件内容"
    model = "claude-3-haiku-20240307"
    prompt_template_name = "email_analyzer"
    tools = [DatabaseTool, HTTPTool]

    async def build_context(self, input_text: str) -> dict:
        return {"email_content": input_text}
```

#### 3. Tool 基类 (tools/base.py)
使用 `@tool` 装饰器自动生成 OpenAI schema：
```python
@register_tool
class DatabaseTool(BaseTool):
    name = "database"
    description = "查询数据库"

    @tool(
        name="search_customers",
        description="搜索客户信息",
        parameters={
            "keyword": {"type": "string", "description": "搜索关键词"},
        }
    )
    async def search_customers(self, keyword: str) -> list[dict]:
        ...
```

#### 4. Prompt 管理 (llm/prompts/manager.py)
双层管理：
- **数据库层**：支持管理员在后台修改
- **代码层**：提供默认值，数据库未配置时使用

```python
prompt_manager = PromptManager()
template = await prompt_manager.get_prompt("intent_classifier")
rendered = template.render(email_content=content)
```

#### 5. 邮件收发 (storage/email.py)
```python
# SMTP 发送
message_id = await smtp_send(to, subject, body, html_body=None, cc=None)

# IMAP 接收
emails = await imap_fetch(folder="INBOX", limit=10, since=None, unseen_only=False)

# 标记已读
await imap_mark_as_read(message_id)
```

### 新增 API 接口

#### Agent 接口 (/api/agents)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/agents` | 列出所有 Agent |
| GET | `/api/agents/{name}` | 获取 Agent 详情 |
| POST | `/api/agents/{name}/run` | 执行 Agent |
| POST | `/api/agents/classify/intent` | 快捷：意图分类 |
| POST | `/api/agents/analyze/email` | 快捷：邮件分析 |

### 配置更新

#### 环境变量 (config.py)
```python
# LLM
ANTHROPIC_API_KEY: str = ""
OPENAI_API_KEY: str = ""
DEFAULT_LLM_MODEL: str = "claude-sonnet-4-20250514"

# IMAP
IMAP_HOST: str = ""
IMAP_PORT: int = 993
IMAP_USER: str = ""
IMAP_PASSWORD: str = ""

# SMTP
SMTP_HOST: str = ""
SMTP_PORT: int = 465
SMTP_USER: str = ""
SMTP_PASSWORD: str = ""
SMTP_USE_TLS: bool = True
```

### Phase 3 任务完成状态

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 3.1 | LiteLLM 集成 | llm/gateway.py | [x] |
| 3.2 | Prompt 模板 | llm/prompts/*.py | [x] |
| 3.3 | LangGraph Agent 基类 | agents/base.py | [x] |
| 3.4 | Agent 注册中心 | agents/registry.py | [x] |
| 3.5 | Tool 基类 | tools/base.py | [x] |
| 3.6 | Tool 注册中心 | tools/registry.py | [x] |
| 3.7 | 邮件底层 | storage/email.py | [x] |
| 3.8 | 邮件 Tool | tools/email.py | [x] |
| 3.9 | 数据库 Tool | tools/database.py | [x] |
| 3.10 | HTTP Tool | tools/http.py | [x] |
| 3.11 | 文件 Tool | tools/file.py | [x] |
| 3.12 | 邮件分析 Agent | agents/email_analyzer.py | [x] |
| 3.13 | Agent API | api/agents.py | [x] |

### 验收命令

```bash
# 1. 配置 API Key
# 在 .env 中设置 ANTHROPIC_API_KEY

# 2. 重启服务
./scripts/restart.sh

# 3. 列出所有 Agent
curl http://localhost:8000/api/agents \
  -H "Authorization: Bearer <token>"

# 4. 测试意图分类
curl -X POST http://localhost:8000/api/agents/classify/intent \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"content": "我想询问产品A的价格，需要采购100个"}'

# 5. 测试邮件分析
curl -X POST http://localhost:8000/api/agents/analyze/email \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"content": "您好，我司需要采购以下产品..."}'
```

### 下一步计划

**Phase 4: Chatbox（Week 6）**
- [ ] 4.1 会话数据模型 (models/chat.py)
- [ ] 4.2 对话 Agent (agents/chat_agent.py)
- [ ] 4.3 SSE 端点 (api/chat.py)
- [ ] 4.4 消息历史 API

### 注意事项

1. **API Key 配置**：使用 LLM 功能需要在 `.env` 中配置 `ANTHROPIC_API_KEY`，或在管理后台设置
2. **邮件配置**：使用邮件功能需要配置 IMAP/SMTP 相关变量，或在管理后台设置
3. **模拟数据**：DatabaseTool 当前使用模拟数据，待 Customer/Product 模型创建后接入真实数据库

---

## 2026-01-30 - 管理后台系统设置页面

### 开发内容

为管理员后台添加系统设置功能，支持在界面中配置 LLM 和邮件服务：
- **LLM 配置**：选择默认模型、配置 API Key
- **邮件配置**：配置 SMTP/IMAP 服务器
- **数据库存储**：设置保存到数据库，优先于环境变量

### 产出文件清单

#### 后端新增
```
backend/app/
├── models/
│   └── settings.py             # 系统设置模型（key-value 存储）
├── api/
│   └── settings.py             # 系统设置 API（LLM/邮件配置）
└── llm/
    └── settings_loader.py      # LLM 设置加载器（从数据库加载）
```

#### 前端新增
```
frontend/src/
├── app/admin/settings/
│   └── page.tsx                # 系统设置页面
└── lib/
    └── api.ts                  # 添加 settingsApi
```

#### 数据库迁移
```
alembic/versions/
└── d89eca32582d_add_system_settings_table.py
```

### 关键代码说明

#### 1. 系统设置模型 (models/settings.py)
使用 key-value 形式存储，便于扩展：
- `key`: 设置键（如 llm.default_model）
- `value`: 设置值
- `category`: 分类（llm, email 等）
- `is_sensitive`: 是否敏感数据（前端只显示部分）

#### 2. 设置 API (api/settings.py)
- `GET /settings/llm` - 获取 LLM 配置
- `PUT /settings/llm` - 更新 LLM 配置
- `POST /settings/llm/test` - 测试 LLM 连接
- `GET /settings/email` - 获取邮件配置
- `PUT /settings/email` - 更新邮件配置

#### 3. 设置加载器 (llm/settings_loader.py)
```python
# 从数据库加载 LLM 设置并应用到环境变量
await apply_llm_settings(db)
```

Agent API 调用前会自动加载数据库中的设置，优先于环境变量。

#### 4. 前端设置页面 (admin/settings/page.tsx)
- Tab 切换：LLM 配置 / 邮件配置
- LLM 配置：模型选择卡片、API Key 输入、测试连接按钮
- 邮件配置：SMTP/IMAP 服务器配置表单

### 新增 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/settings/llm` | 获取 LLM 配置 |
| PUT | `/settings/llm` | 更新 LLM 配置 |
| POST | `/settings/llm/test` | 测试 LLM 连接 |
| GET | `/settings/email` | 获取邮件配置 |
| PUT | `/settings/email` | 更新邮件配置 |
| GET | `/settings/all` | 获取所有设置 |

### 支持的 LLM 模型

| 模型 ID | 名称 | 提供商 |
|---------|------|--------|
| claude-sonnet-4-20250514 | Claude Sonnet 4 | Anthropic |
| claude-3-5-sonnet-20241022 | Claude 3.5 Sonnet | Anthropic |
| claude-3-opus-20240229 | Claude 3 Opus | Anthropic |
| claude-3-sonnet-20240229 | Claude 3 Sonnet | Anthropic |
| claude-3-haiku-20240307 | Claude 3 Haiku | Anthropic |
| gpt-4o | GPT-4o | OpenAI |
| gpt-4-turbo | GPT-4 Turbo | OpenAI |
| gpt-4 | GPT-4 | OpenAI |
| gpt-3.5-turbo | GPT-3.5 Turbo | OpenAI |

### 验收步骤

```bash
# 1. 访问管理后台
http://localhost:3000/admin

# 2. 点击侧边栏"系统设置"

# 3. 在 LLM 配置标签页：
#    - 选择默认模型
#    - 输入 API Key
#    - 点击"测试连接"验证
#    - 点击"保存配置"

# 4. 在邮件配置标签页：
#    - 填写 SMTP/IMAP 服务器信息
#    - 点击"保存配置"
```

### 配置优先级

1. 数据库设置（最高优先级）
2. 环境变量 (.env)
3. 代码默认值（最低优先级）

这意味着管理员可以在后台随时修改配置，无需重启服务。

---

## 2026-01-30 - Phase 4: Chatbox + 飞书集成

### 开发内容

完成 Phase 4 的 Chatbox 和飞书集成，包括：
- **会话数据模型**：ChatSession 和 ChatMessage 表
- **Chat Agent**：支持多轮对话、流式输出、Redis 缓存上下文
- **Chat API**：SSE 流式对话接口
- **统一事件模型**：UnifiedEvent 和 Adapter 架构
- **飞书适配器**：FeishuClient + FeishuAdapter
- **飞书长连接 Worker**：使用 lark-oapi SDK WebSocket
- **飞书配置 API**：后端配置管理接口
- **飞书配置页面**：前端管理界面

### 产出文件清单

#### 后端新增文件
```
backend/app/
├── models/
│   └── chat.py                  # ChatSession + ChatMessage 模型
├── schemas/
│   ├── chat.py                  # Chat API Schema
│   └── event.py                 # UnifiedEvent 统一事件模型
├── agents/
│   └── chat_agent.py            # Chat Agent（流式对话）
├── api/
│   └── chat.py                  # Chat API（SSE 端点）
└── adapters/
    ├── __init__.py              # 适配器模块导出
    ├── base.py                  # BaseAdapter 基类
    ├── feishu.py                # FeishuClient + FeishuAdapter
    └── feishu_ws.py             # 飞书长连接 Worker

alembic/versions/
└── 79b66ba4fa2c_add_chat_tables.py  # 会话表迁移
```

#### 前端新增文件
```
frontend/src/
├── app/admin/settings/feishu/
│   └── page.tsx                 # 飞书配置页面
└── lib/
    └── api.ts                   # 新增 feishuApi
```

#### 脚本更新
```
scripts/
├── setup.sh                     # 添加飞书配置说明
├── start.sh                     # 添加 --feishu 参数
├── stop.sh                      # 添加飞书 Worker 停止
├── restart.sh                   # 添加飞书 Worker 重启
├── status.sh                    # 添加飞书 Worker 状态
└── logs.sh                      # 添加飞书日志查看
```

### 关键代码说明

#### 1. Chat Agent (agents/chat_agent.py)
```python
class ChatAgent:
    # 同步对话
    async def chat(session_id, message, **kwargs) -> ChatResult

    # 流式对话
    async def chat_stream(session_id, message, **kwargs) -> AsyncIterator[str]

    # 上下文管理（Redis 缓存，24h TTL）
    async def _get_context(session_id) -> list[dict]
    async def _save_context(session_id, messages) -> None
```

#### 2. 统一事件模型 (schemas/event.py)
```python
class UnifiedEvent(BaseModel):
    event_id: str
    event_type: Literal["chat", "email", "webhook", ...]
    source: Literal["web", "chatbox", "feishu", ...]
    content: str
    session_id: Optional[str]
    user_id: Optional[str]
    user_external_id: Optional[str]  # 如飞书 open_id
    ...
```

#### 3. 飞书适配器 (adapters/feishu.py)
```python
class FeishuClient:
    async def send_text(receive_id, receive_id_type, text)
    async def reply_message(message_id, msg_type, content)
    async def test_connection() -> bool

class FeishuAdapter(BaseAdapter):
    async def to_unified_event(raw_data) -> UnifiedEvent
    async def send_response(event, response, content)
```

#### 4. 飞书长连接 Worker (adapters/feishu_ws.py)
```python
class FeishuWSWorker:
    # 使用 lark-oapi SDK 建立 WebSocket 长连接
    async def start() -> None
    async def stop() -> None

# 启动方式
python -m app.adapters.feishu_ws
```

### 新增 API 接口

#### Chat 接口 (/api/chat)
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/sessions` | 创建会话 |
| GET | `/api/chat/sessions` | 会话列表 |
| GET | `/api/chat/sessions/{id}` | 会话详情 |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 |
| GET | `/api/chat/sessions/{id}/messages` | 消息历史 |
| POST | `/api/chat/send` | 非流式对话 |
| POST | `/api/chat/stream` | SSE 流式对话 |

#### 飞书配置接口 (/settings/feishu)
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/settings/feishu` | 获取飞书配置 |
| PUT | `/settings/feishu` | 更新飞书配置 |
| POST | `/settings/feishu/test` | 测试飞书连接 |

### 依赖更新 (requirements.txt)
```
sse-starlette>=1.6.0     # SSE 支持
lark-oapi>=1.3.0         # 飞书官方 SDK
```

### Phase 4 任务完成状态

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 4.1 | 会话数据模型 | models/chat.py | [x] |
| 4.2 | Chat Agent | agents/chat_agent.py | [x] |
| 4.3 | Chat API (SSE) | api/chat.py | [x] |
| 4.4 | 统一事件模型 | schemas/event.py | [x] |
| 4.5 | Adapter 基类 | adapters/base.py | [x] |
| 4.6 | 飞书适配器 | adapters/feishu.py | [x] |
| 4.7 | 飞书长连接 Worker | adapters/feishu_ws.py | [x] |
| 4.8 | 飞书配置 API | api/settings.py 更新 | [x] |
| 4.9 | 飞书配置页面 | admin/settings/feishu/page.tsx | [x] |

### 验收命令

```bash
# 1. 安装新依赖
cd backend && pip install -r requirements.txt

# 2. 执行数据库迁移
alembic upgrade head

# 3. 重启服务
./scripts/restart.sh --bg

# 4. 测试 SSE 端点
curl -N http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 5. 配置飞书
# 访问 http://localhost:3000/admin/settings/feishu
# 填写 App ID 和 App Secret

# 6. 启动飞书 Worker
./scripts/start.sh --feishu --bg

# 7. 查看飞书日志
./scripts/logs.sh feishu
```

### 架构图

```
用户端
├── Web Chatbox
│   └── POST /api/chat/stream (SSE)
│         ↓
│   └── ChatAgent.chat_stream()
│         ↓
│   └── LLMGateway.chat_stream()
│
└── 飞书机器人
    └── lark-oapi WebSocket 长连接
          ↓
    └── FeishuWSWorker
          ↓
    └── FeishuAdapter.to_unified_event()
          ↓
    └── ChatAgent.chat()
          ↓
    └── FeishuAdapter.send_response()
```

### 下一步计划

**Phase 5: 完整业务流程**

---

## 2026-01-30 - Phase 5: 完整业务流程

### 开发内容

完成 Phase 5 的端到端邮件处理流程，包括：
- **事件记录表** (`models/event.py`) - 事件审计和追踪
- **Redis Streams** (`messaging/streams.py`) - 事件流处理
- **Email Adapter** (`adapters/email.py`) - 邮件转换为 UnifiedEvent
- **事件分发器** (`messaging/dispatcher.py`) - 意图分类和 Workflow 路由
- **报价 Agent** (`agents/quote_agent.py`) - 询价分析和报价生成
- **PDF Tool** (`tools/pdf.py`) - 报价单 PDF 生成
- **邮件处理 Workflow** (`workflows/definitions/email_process.py`) - 邮件处理主流程
- **邮件 Activity** (`workflows/activities/email.py`) - 邮件相关 Activity
- **邮件监听器** (`adapters/email_listener.py`) - 定时拉取新邮件

### 产出文件清单

#### 消息层 (app/messaging/)
```
app/messaging/
├── __init__.py           # 模块导出
├── streams.py            # Redis Streams 事件流
└── dispatcher.py         # 事件分发器
```

#### 适配器层 (app/adapters/)
```
app/adapters/
├── email.py              # 邮件适配器
└── email_listener.py     # 邮件监听器
```

#### Agent 层 (app/agents/)
```
app/agents/
└── quote_agent.py        # 报价 Agent
```

#### Tools 层 (app/tools/)
```
app/tools/
└── pdf.py                # PDF 生成工具
```

#### Workflow 层 (app/workflows/)
```
app/workflows/
├── activities/
│   └── email.py          # 邮件相关 Activity
└── definitions/
    └── email_process.py  # 邮件处理 Workflow
```

#### 数据模型 (app/models/)
```
app/models/
└── event.py              # 事件记录模型
```

#### 数据库迁移
```
alembic/versions/
└── a1b2c3d4e5f6_add_events_table.py
```

### 关键代码说明

#### 1. 事件流处理 (messaging/streams.py)
- 使用 Redis Streams 实现可靠事件队列
- 支持消费者组，多 Worker 协作处理
- 提供消息确认（ACK）机制

#### 2. 事件分发器 (messaging/dispatcher.py)
- 幂等性检查（通过 idempotency_key）
- 保存事件到数据库
- 调用意图分类 Agent
- 根据意图启动对应 Workflow

#### 3. 邮件处理 Workflow (workflows/definitions/email_process.py)
- 根据意图路由（inquiry/order/complaint/follow_up/other）
- 调用报价 Agent 生成报价
- 支持审批子流程（金额超阈值）
- 发送回复邮件

#### 4. 报价 Agent (agents/quote_agent.py)
- 分析询价邮件内容
- 调用工具查询产品价格
- 生成报价单 PDF
- 建议回复内容

#### 5. 邮件监听器 (adapters/email_listener.py)
- 使用 APScheduler 定时任务
- Redis 保存检查点
- 分布式锁防止重复处理

### 完整数据流

```
邮件到达 (IMAP)
    ↓
EmailListener (定时轮询)
    ↓
EmailAdapter.to_unified_event()
    ↓
Redis Streams (持久化)
    ↓
EventDispatcher.dispatch()
    ├── 幂等性检查
    ├── 保存到 events 表
    ├── 意图分类 (IntentClassifierAgent)
    └── 启动 Workflow
           ↓
EmailProcessWorkflow
    ├── inquiry → QuoteAgent → (审批) → 发送报价邮件
    ├── order → OrderAgent → 创建订单
    ├── complaint → 升级处理
    └── other → 人工处理
```

### Phase 5 任务完成状态

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 5.1 | UnifiedEvent 模型 | schemas/event.py | [x] (Phase 4 完成) |
| 5.2 | Adapter 基类 | adapters/base.py | [x] (Phase 4 完成) |
| 5.3 | Email Adapter | adapters/email.py | [x] |
| 5.4 | 邮件监听 | adapters/email_listener.py | [x] |
| 5.5 | 事件分发器 | messaging/dispatcher.py | [x] |
| 5.6 | Redis Streams | messaging/streams.py | [x] |
| 5.7 | 意图分类 Agent | agents/email_analyzer.py | [x] (已存在) |
| 5.8 | 报价 Agent | agents/quote_agent.py | [x] |
| 5.9 | PDF Tool | tools/pdf.py | [x] |
| 5.10 | 邮件处理 Workflow | workflows/definitions/email_process.py | [x] |
| 5.11 | 邮件 Activity | workflows/activities/email.py | [x] |
| 5.12 | 事件记录表 | models/event.py | [x] |

### 依赖更新 (requirements.txt)

```
reportlab>=4.0.0          # PDF 生成
```

### 验收命令

```bash
# 1. 安装新依赖
cd backend && pip install -r requirements.txt

# 2. 执行数据库迁移
alembic upgrade head

# 3. 重启服务
./scripts/restart.sh --bg

# 4. 启动邮件监听器
python -m app.adapters.email_listener

# 5. 发送测试邮件到监听邮箱，观察日志
./scripts/logs.sh api

# 6. 查看事件记录
# 可通过数据库查询 events 表
```

### 下一步计划

**Phase 7: 完善优化**
- [ ] 7.1 单元测试
- [ ] 7.2 集成测试
- [ ] 7.3 API 文档完善

---

## 2026-01-30 - Phase 6: 前端界面完成

### 开发内容

完成 Phase 6 的前端界面开发，包括：
- **通用组件**：Modal 模态框、LoadingSpinner 加载动画
- **Chatbox 组件**：SSE 流式对话、会话管理、消息历史
- **审批管理页面**：审批列表、通过/拒绝操作
- **系统日志页面**：日志查看（模拟数据）
- **导航菜单更新**：添加审批管理和系统日志入口

### 产出文件清单

#### 通用组件 (src/components/)
```
frontend/src/components/
├── Modal.tsx                    # 通用模态框组件
└── ChatBox/
    ├── index.tsx                # 模块导出
    ├── ChatBox.tsx              # 聊天主容器
    ├── ChatMessage.tsx          # 消息气泡组件
    ├── ChatInput.tsx            # 输入框组件
    ├── ChatSidebar.tsx          # 会话列表侧边栏
    └── hooks/
        └── useSSE.ts            # SSE 流式处理 Hook
```

#### 页面 (src/app/)
```
frontend/src/app/
├── chat/
│   ├── page.tsx                 # 独立对话页面
│   └── layout.tsx               # 对话页面布局
└── admin/
    ├── approvals/
    │   └── page.tsx             # 审批管理页面
    └── logs/
        └── page.tsx             # 系统日志页面
```

#### API 扩展 (src/lib/)
```
frontend/src/lib/
└── api.ts                       # 新增 chatApi, workflowApi
```

### 关键代码说明

#### 1. SSE Hook (ChatBox/hooks/useSSE.ts)
```typescript
// 使用 fetch + ReadableStream 处理 SSE
// 支持 Authorization header（EventSource 不支持）
const response = await fetch(chatApi.getStreamUrl(), {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ session_id, message }),
});

const reader = response.body.getReader();
// 解析 SSE 格式: "data: {...}\n\n"
```

#### 2. ChatBox 组件 (ChatBox/ChatBox.tsx)
- 会话列表管理（创建、切换、删除）
- 消息历史展示
- 流式响应逐字显示
- 滚动自动定位到最新消息

#### 3. 审批管理 (admin/approvals/page.tsx)
- 调用 monitorApi.getWorkflows() 获取列表
- 支持按状态筛选（待审批/已完成/失败）
- 通过/拒绝操作调用 workflowApi

#### 4. Modal 组件 (Modal.tsx)
- ESC 键关闭
- 点击背景关闭
- 支持 sm/md/lg 三种尺寸

### 新增 API 定义

#### chatApi
```typescript
export const chatApi = {
  createSession: (data) => request('/api/chat/sessions', { method: 'POST', body: data }),
  getSessions: (params) => request('/api/chat/sessions', { params }),
  getSession: (sessionId) => request(`/api/chat/sessions/${sessionId}`),
  deleteSession: (sessionId) => request(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' }),
  getMessages: (sessionId, limit) => request(`/api/chat/sessions/${sessionId}/messages`),
  sendMessage: (data) => request('/api/chat/send', { method: 'POST', body: data }),
  getStreamUrl: () => `${API_BASE_URL}/api/chat/stream`,
  getBaseUrl: () => API_BASE_URL,
};
```

#### workflowApi
```typescript
export const workflowApi = {
  createApproval: (data) => request('/api/workflows/approval', { method: 'POST', body: data }),
  getStatus: (workflowId) => request(`/api/workflows/${workflowId}/status`),
  approve: (workflowId, comment) => request(`/api/workflows/${workflowId}/approve`, { method: 'POST', body: { comment } }),
  reject: (workflowId, reason) => request(`/api/workflows/${workflowId}/reject`, { method: 'POST', body: { reason } }),
  cancel: (workflowId) => request(`/api/workflows/${workflowId}/cancel`, { method: 'POST' }),
};
```

### 导航菜单更新

```typescript
// admin/layout.tsx
const navigation = [
  { name: '仪表盘', href: '/admin', icon: '📊' },
  { name: '用户管理', href: '/admin/users', icon: '👥' },
  { name: '审批管理', href: '/admin/approvals', icon: '✅' },  // 新增
  { name: 'LLM 配置', href: '/admin/llm', icon: '🤖' },
  { name: '运行监控', href: '/admin/monitor', icon: '📈' },
  { name: '系统日志', href: '/admin/logs', icon: '📋' },      // 新增
  { name: '飞书配置', href: '/admin/settings/feishu', icon: '💬' },
  { name: '系统设置', href: '/admin/settings', icon: '⚙️' },
];
```

### Phase 6 任务完成状态

| # | 任务 | 交付物 | 状态 |
|---|------|--------|------|
| 6.1 | Next.js 初始化 | frontend/ 项目结构 | [x] |
| 6.2 | 认证页面 | app/login/page.tsx | [x] |
| 6.3 | Dashboard | app/admin/page.tsx | [x] |
| 6.4 | Chatbox 组件 | components/ChatBox/ (SSE) | [x] |
| 6.5 | 审批管理 | app/admin/approvals/ | [x] |
| 6.6 | 任务列表 | - | [ ] (暂不需要) |
| 6.7 | 客户管理 | - | [ ] (暂不需要) |
| 6.8 | 管理员后台 | app/admin/* | [x] |
| 6.9 | 管理员-用户管理 | app/admin/users/page.tsx | [x] |
| 6.10 | 管理员-系统配置 | app/admin/settings | [x] |
| 6.11 | 管理员-日志查看 | app/admin/logs | [x] |
| 6.12 | 管理员-工作流监控 | app/admin/monitor | [x] |
| 6.13 | 认证上下文 | contexts/AuthContext.tsx | [x] |
| 6.14 | API 工具库 | lib/api.ts | [x] |
| 6.15 | 首页重定向 | app/page.tsx | [x] |

> **Phase 6 已完成** ✅ (2026-01-30)

### 验收命令

```bash
# 1. 启动前端开发服务器
cd frontend && npm run dev

# 2. 访问对话页面
open http://localhost:3000/chat

# 3. 测试 Chatbox
# - 创建新会话
# - 发送消息，观察流式输出
# - 切换会话
# - 删除会话

# 4. 访问审批管理
open http://localhost:3000/admin/approvals

# 5. 访问系统日志
open http://localhost:3000/admin/logs

# 6. 构建检查
cd frontend && npm run build
# 应成功生成 14 个路由
```

### Bug 修复记录

1. **AuthContext 属性名错误**
   - 问题：`app/page.tsx` 使用 `loading` 但 AuthContext 定义的是 `isLoading`
   - 修复：改为 `const { user, isLoading } = useAuth();`

2. **SQLAlchemy 保留字冲突**
   - 问题：`models/event.py` 使用 `metadata` 属性，与 SQLAlchemy Declarative API 冲突
   - 修复：改为 `event_metadata`

### 下一步计划

**Phase 7: 完善优化**
- [ ] 7.1 单元测试
- [ ] 7.2 集成测试
- [ ] 7.3 API 文档完善
- [ ] 7.4 部署文档
- [ ] 7.5 性能优化

---

## Phase 7: LLM 提供商扩展 + Agent 配置管理

> **开始时间**: 2026-02-01
> **状态**: 进行中 🚧
> **目标**: 支持 Gemini、Qwen 等多个 LLM 提供商，实现模型级别的 API Key 管理

### 核心需求

1. **新增 LLM 提供商支持**
   - Google Gemini (gemini-1.5-pro, gemini-1.5-flash, gemini-1.5-flash-8b)
   - 阿里千问 (qwen-max, qwen-plus, qwen-turbo)
   - 火山引擎 (doubao-pro-32k)

2. **模型级别 API Key 管理**
   - 从"按提供商存储"改为"按模型存储"
   - 精细化追踪每个模型的使用情况和成本

3. **前端 UI 优化**
   - 折叠/展开所有提供商（默认收缩）
   - 每个模型独立的 API Key 输入框

4. **Agent 配置管理**
   - 将 Prompt 页面改造为 Agent 管理页面
   - Agent 级别的模型选择、参数配置、工具配置

### 数据库设计

#### 新增表：`llm_model_configs`

```sql
CREATE TABLE llm_model_configs (
    id VARCHAR(36) PRIMARY KEY,
    model_id VARCHAR(100) UNIQUE,    -- 如：gemini/gemini-1.5-pro
    provider VARCHAR(50),             -- gemini, qwen, anthropic 等
    model_name VARCHAR(100),          -- Gemini 1.5 Pro
    api_key TEXT,                     -- 该模型的 API Key
    api_endpoint TEXT,                -- 自定义 API 端点
    total_requests INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    last_used_at TIMESTAMP,
    is_enabled BOOLEAN DEFAULT true,
    is_configured BOOLEAN DEFAULT false,
    description TEXT,
    parameters JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 产出文件

| 序号 | 类型 | 文件 | 状态 |
|-----|-----|------|-----|
| 7.1 | 数据库迁移 | backend/alembic/versions/h7i8j9k0l1m2_add_llm_model_configs.py | ✅ |
| 7.2 | 数据模型 | backend/app/models/llm_model_config.py | ✅ |
| 7.3 | 后端 API | backend/app/api/llm_models.py | ✅ |
| 7.4 | 配置更新 | backend/app/core/config.py | ✅ |
| 7.5 | 环境变量 | .env.example | ✅ |
| 7.6 | 路由注册 | backend/app/main.py | ✅ |
| 7.7 | 前端 API | frontend/src/lib/api.ts | ✅ |
| 7.8 | LLM 配置页 | frontend/src/app/admin/llm/page.tsx | ✅ |
| 7.9 | Agent 管理页 | frontend/src/app/admin/agents/page.tsx | ✅ |
| 7.10 | 导航更新 | frontend/src/app/admin/layout.tsx | ✅ |
| 7.11 | Agent 基类更新 | backend/app/agents/base.py | ⏳ |
| 7.12 | LLM 初始化更新 | backend/app/llm/__init__.py | ⏳ |

### 已完成的工作 ✅

#### 1. 数据库迁移（Phase 1）

创建了 `llm_model_configs` 表并插入了所有支持的模型：

```bash
# 已插入的模型
- Anthropic: claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus
- OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo
- Gemini: gemini-1.5-pro, gemini-1.5-flash, gemini-1.5-flash-8b
- Qwen: qwen-max, qwen-plus, qwen-turbo
- Volcengine: doubao-pro-32k
```

验证：

```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d concord \
  -c "SELECT provider, COUNT(*) FROM llm_model_configs GROUP BY provider;"

 provider  | count
-----------+-------
 anthropic |     3
 gemini    |     3
 openai    |     3
 qwen      |     3
 volcengine|     1
(5 行记录)
```

#### 2. 后端 API 实现（Phase 3）

创建了完整的 LLM 模型配置管理 API：

```python
# /admin/llm/models - 模型列表（支持筛选）
GET /admin/llm/models?provider=gemini&is_enabled=true

# /admin/llm/models/{model_id} - 模型详情
GET /admin/llm/models/gemini%2Fgemini-1.5-pro

# /admin/llm/models/{model_id} - 更新配置
PUT /admin/llm/models/gemini%2Fgemini-1.5-pro
{
  "api_key": "AIza...",
  "is_enabled": true,
  "parameters": {"temperature": 0.7}
}

# /admin/llm/models/{model_id}/test - 测试连接
POST /admin/llm/models/gemini%2Fgemini-1.5-pro/test
{
  "test_prompt": "你好"
}

# /admin/llm/models/stats/usage - 使用统计
GET /admin/llm/models/stats/usage
```

**功能特性**：
- ✅ 模型级别 API Key 存储
- ✅ API Key 遮蔽显示（只显示前4位和后4位）
- ✅ 模型连接测试
- ✅ 使用统计追踪（请求次数、Token 消耗）
- ✅ 按提供商/状态筛选
- ✅ 管理员权限认证

#### 3. 配置文件更新

**backend/app/core/config.py**:
```python
# 新增环境变量
GEMINI_API_KEY: str = ""
DASHSCOPE_API_KEY: str = ""
VOLCENGINE_API_KEY: str = ""
```

**.env.example**:
```bash
# LLM API Keys（也可在管理后台配置）
ANTHROPIC_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx
GEMINI_API_KEY=
DASHSCOPE_API_KEY=
VOLCENGINE_API_KEY=
```

#### 4. API 测试验证

```bash
# 测试脚本
./test_llm_api.sh

# 结果
[1] 健康检查... ✅
[2] 模型列表 API... ✅ （返回401，认证正常）
[3] Gemini 模型筛选... ✅ （返回401，认证正常）
```

### 已完成的前端工作 ✅ (2026-02-01 新增)

#### Phase 4: 前端 LLM 配置页面 ✅

**完成的任务**：
1. ✅ 更新 `frontend/src/lib/api.ts` 添加 `llmModelsApi`
   - 添加了完整的 TypeScript 接口定义
   - 实现了 list、get、update、test、getUsageStats 方法
2. ✅ 完全重写 `frontend/src/app/admin/llm/page.tsx`
   - ✅ 添加折叠/展开功能（默认全部收缩）
   - ✅ 改为模型级别的 API Key 配置
   - ✅ 添加 Gemini、Qwen、Volcengine 提供商卡片
   - ✅ 显示统计信息（总模型数、已配置、请求数、Token 数）
   - ✅ 每个模型独立的配置界面
   - ✅ 启用/禁用开关
   - ✅ 测试连接功能
   - ✅ 使用统计展示

**UI 特性**：
- 📊 顶部统计卡片（总模型数、已配置、总请求数、总 Token 数）
- 🔽 可折叠的提供商分组（默认收缩）
- 🔑 每个模型独立的 API Key 输入框
- 🔒 API Key 遮蔽显示（sk-ant-****...****）
- 🧪 一键测试模型连接
- 🔄 启用/禁用开关
- 📈 使用统计展示

#### Phase 5: Agent 管理页面 ✅

**完成的任务**：
1. ✅ 创建新的 `/admin/agents` 页面（保留原有 Prompts 页面）
2. ✅ 实现 Agent 列表展示
   - 显示所有注册的 Agent
   - 显示 Prompt 配置状态
   - 显示当前使用的模型
3. ✅ 实现配置编辑界面
   - 模型选择下拉框
   - Temperature 滑块（0-2）
   - Max Tokens 输入框
   - 关联 Prompt 显示
4. ✅ 更新导航菜单
   - 添加 "Agent 管理" 🧠 菜单项

**Agent 列表**：
- chat_agent (对话助手)
- email_analyzer (邮件分析器)
- email_summarizer (邮件摘要生成器)
- intent_classifier (意图分类器)
- quote_agent (报价助手)
- router_agent (路由代理)

**注**：Agent 配置保存功能标记为"开发中"，等待后端 API 实现

**2026-02-01 更新**：根据用户建议，将 Prompt 编辑功能整合到 Agent 管理页面中。现在 Agent 管理页面包含：
- ✅ 双标签页界面（基本配置 + Prompt 编辑）
- ✅ 在 Agent 页面中直接编辑 Prompt 内容
- ✅ Prompt 版本信息展示
- ✅ 变量提示和说明
- ✅ 完整的 Prompt 保存功能（已实现）

这样用户可以在一个页面中完成 Agent 的所有配置，无需在多个页面之间切换。原有的 `/admin/prompts` 页面仍然保留，可作为高级 Prompt 管理工具。

### 待完成的工作 ⏳

#### Phase 6: Agent 配置集成

**任务**：
1. [ ] 修改 `backend/app/agents/base.py`
   - 从 `system_settings` 读取 Agent 配置
2. [ ] 修改 `backend/app/llm/__init__.py`
   - 加载 Agent 配置到环境变量

#### Phase 7: 测试和验证

**任务**：
1. [ ] 端到端测试：配置模型 → 配置 Agent → 调用 Agent
2. [ ] 验证使用统计更新
3. [ ] 验证模型切换
4. [ ] 性能测试

### 技术亮点

1. **模型级别配置**：从提供商级别改为模型级别，实现精细化管理
2. **使用统计追踪**：自动记录每个模型的请求次数、Token 消耗、最后使用时间
3. **安全性**：API Key 遮蔽显示，敏感信息保护
4. **可扩展性**：新增提供商只需添加数据库记录，无需修改代码
5. **测试友好**：提供模型连接测试接口，快速验证配置

### 下一步计划

1. **立即执行**：
   - 完成前端 LLM 配置页面（折叠/展开 + 模型级别配置）
   - 完成 Agent 管理页面改造

2. **后续优化**：
   - 智谱 AI 直接支持调研（如果 LiteLLM 支持）
   - 成本追踪功能
   - 模型性能对比
   - 使用配额管理

### 验收命令

```bash
# 1. 验证数据库迁移
PGPASSWORD=postgres psql -h localhost -U postgres -d concord \
  -c "SELECT id, provider, model_name, is_configured FROM llm_model_configs LIMIT 5;"

# 2. 测试后端 API
./test_llm_api.sh

# 3. 查看 API 文档
open http://localhost:8000/docs#/LLM%20模型配置

# 4. 测试前端（完成后）
open http://localhost:3000/admin/llm
open http://localhost:3000/admin/agents
```

---

*最后更新: 2026-02-01*
