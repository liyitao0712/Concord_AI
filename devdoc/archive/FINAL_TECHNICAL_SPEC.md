# Concord AI 中台系统 - 最终技术规格文档

> **文档版本**: v1.2 Final
> **更新日期**: 2026-01-29
> **项目定位**: 团队内部 AI 自动化平台，未来可商业化
> **设计原则**: 可插拔、可扩展、简洁清晰

---

## 目录

1. [项目概述](#一项目概述)
2. [系统架构](#二系统架构)
3. [技术栈选型](#三技术栈选型)
4. [核心模块设计](#四核心模块设计)
5. [数据模型](#五数据模型)
6. [AI 能力规划](#六ai-能力规划)
7. [开发计划](#七开发计划)
8. [部署与运维](#八部署与运维)

---

## 一、项目概述

### 1.1 项目目标

构建一个 **AI 中台系统**，实现：
- 统一的 AI 能力调用入口
- 可插拔的 Agent 和工具体系
- 灵活的工作流编排与审批机制
- 支持多种输入渠道（Web、Chatbox、飞书、Webhook）

### 1.2 核心设计原则

| 原则 | 说明 |
|------|------|
| **可插拔** | Agent 和工具都是插件，随时增删，通过注册中心管理 |
| **中台定位** | 统一数据模型，沉淀业务数据，未来可替代 ERP |
| **审批灵活** | 每个工作流独立配置审批节点，支持人机协作 |
| **渐进式** | 可以一个模块一个模块地做，快速迭代 |
| **少即是多** | 能少一个组件就少一个，降低运维复杂度 |

### 1.3 一句话总结

```
FastAPI + Redis + Temporal + LangGraph + LiteLLM + PostgreSQL (含 pgvector)

• 不用 LangChain，只用 LangGraph
• LLM 统一用 LiteLLM
• Tools 自己封装
• Temporal 就是 Orchestrator（不需要 Celery）
• Chatbox 用 SSE 流式输出
• 向量搜索用 pgvector（不额外加组件）
• 文件存储用阿里云 OSS
• 数据迁移用 Alembic
```

---

## 二、系统架构

### 2.1 整体架构图（8层）

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    用户端                                           │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│    │  Web 界面   │    │   Chatbox   │    │  飞书机器人  │    │   Webhook   │        │
│    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
└───────────┼──────────────────┼──────────────────┼──────────────────┼───────────────┘
            │                  │                  │                  │
            │         ┌────────┴────────┐         │                  │
            │         │  SSE 流式输出    │         │                  │
            │         └────────┬────────┘         │                  │
            ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ① API Layer (FastAPI)                                  │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│    │   认证   │  │   幂等   │  │   限流   │  │   路由   │  │   日志   │           │
│    │  (JWT)  │  │  校验    │  │          │  │          │  │          │           │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────┬───────────────────────────────────────────┘
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ② Message Layer (Redis)                                │
│    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐            │
│    │   Redis Streams  │    │   Redis Pub/Sub  │    │   Redis Cache    │            │
│    │   (消息队列)      │    │   (实时通知)      │    │   (缓存/Session) │            │
│    └──────────────────┘    └──────────────────┘    └──────────────────┘            │
└─────────────────────────────────────────┬───────────────────────────────────────────┘
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ③ Workflow Engine (Temporal)                                │
│                            = Orchestrator 编排层                                    │
│    ┌────────────────────────────────────────────────────────────────────────────┐  │
│    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│    │   │ 邮件处理流程 │  │ 报价处理流程 │  │ 订单处理流程 │  │ 审批处理流程 │      │  │
│    │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│    │   功能：流程编排 | 状态持久化 | 失败重试 | 超时处理 | 人工审批 | 定时任务   │  │
│    └────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────┬───────────────────────────────────────────┘
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            ④ Agent Layer (LangGraph)                                │
│    ┌────────────────────────────────────────────────────────────────────────────┐  │
│    │                          Agent = LLM + Prompt + Tools                      │  │
│    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│    │   │ 邮件分析Agent│  │ 报价生成Agent│  │ 订单处理Agent│  │ 对话Agent   │      │  │
│    │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘      │  │
│    │   内部循环：Think → Act → Observe → Think (直到完成)                       │  │
│    └────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────┬───────────────────────────────┘
                                ▼                     ▼
┌───────────────────────────────────────┐ ┌───────────────────────────────────────────┐
│       ⑤ LLM Gateway (LiteLLM)         │ │              ⑥ Tools Layer                │
│   ┌───────────┐  ┌───────────┐       │ │   ┌────────┐ ┌────────┐ ┌────────┐       │
│   │  Claude   │  │   GPT     │       │ │   │ 邮件   │ │ 数据库 │ │ 文件   │       │
│   └───────────┘  └───────────┘       │ │   └────────┘ └────────┘ └────────┘       │
│   ┌───────────┐  ┌───────────┐       │ │   ┌────────┐ ┌────────┐ ┌────────┐       │
│   │ 本地模型  │  │  其他     │       │ │   │ HTTP   │ │ 飞书   │ │ PDF    │       │
│   └───────────┘  └───────────┘       │ │   └────────┘ └────────┘ └────────┘       │
│   统一接口，一行代码切换模型           │ │   工具注册中心，可插拔设计               │
└───────────────────────────────────────┘ └───────────────────────────────────────────┘
                                │                     │
                                └──────────┬──────────┘
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ⑦ Storage Layer                                        │
│   ┌───────────────────────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│   │         PostgreSQL 16             │ │     Redis       │ │   阿里云 OSS    │    │
│   │   (主数据库 + pgvector 向量)       │ │   (缓存/消息)   │ │   (文件存储)    │    │
│   │ • 用户/客户/订单/报价              │ │ • Session       │ │ • 附件          │    │
│   │ • 会话/消息                        │ │ • 缓存/幂等Key  │ │ • 报价单PDF    │    │
│   │ • 文档 Embedding (pgvector)       │ │ • 短期记忆      │ │ • 生成的文件    │    │
│   └───────────────────────────────────┘ └─────────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              ⑧ Infrastructure                                       │
│    Docker + Docker Compose (开发) → Kubernetes (生产)                               │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 入口统一与事件模型

不同渠道的输入格式各异，需要在 API Layer 统一转换为**标准事件格式**，再进入后续处理。

#### 2.2.1 多渠道输入适配

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              多渠道输入适配层                                        │
│                                                                                     │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐        │
│  │ Web API   │  │ Chatbox   │  │ 飞书回调  │  │ Webhook   │  │ 邮件监听  │        │
│  │ /api/*    │  │ /chat/*   │  │ /feishu/* │  │ /hook/*   │  │ IMAP      │        │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘        │
│        │              │              │              │              │               │
│        ▼              ▼              ▼              ▼              ▼               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐        │
│  │  Web      │  │  Chat     │  │  Feishu   │  │  Webhook  │  │  Email    │        │
│  │ Adapter   │  │ Adapter   │  │ Adapter   │  │ Adapter   │  │ Adapter   │        │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘        │
│        │              │              │              │              │               │
│        └──────────────┴──────────────┴──────────────┴──────────────┘               │
│                                      │                                             │
│                                      ▼                                             │
│                       ┌──────────────────────────────┐                             │
│                       │     统一事件格式 (Event)      │                             │
│                       │     UnifiedEvent Schema      │                             │
│                       └──────────────────────────────┘                             │
│                                      │                                             │
│                                      ▼                                             │
│                              Redis Streams                                         │
│                                      │                                             │
│                                      ▼                                             │
│                          Temporal Workflow Engine                                  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

#### 2.2.2 统一事件模型（UnifiedEvent）

```python
# schemas/event.py

from pydantic import BaseModel
from typing import Literal, Optional, Any
from datetime import datetime
from uuid import uuid4

class UnifiedEvent(BaseModel):
    """统一事件模型 - 所有入口的标准格式"""

    # === 事件标识 ===
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: Literal[
        "chat",           # 对话消息
        "email",          # 邮件
        "webhook",        # Webhook 触发
        "command",        # 指令/命令
        "approval",       # 审批操作
        "schedule",       # 定时触发
    ]

    # === 来源信息 ===
    source: Literal["web", "chatbox", "feishu", "webhook", "email", "schedule"]
    source_id: Optional[str] = None       # 来源唯一标识（如飞书消息ID）

    # === 用户信息 ===
    user_id: Optional[str] = None         # 系统用户ID
    user_name: Optional[str] = None       # 用户名称
    user_external_id: Optional[str] = None  # 外部ID（如飞书open_id）

    # === 会话信息 ===
    session_id: Optional[str] = None      # 会话ID（对话场景）
    thread_id: Optional[str] = None       # 线程ID（邮件回复链）

    # === 内容 ===
    content: str                          # 主要内容（文本）
    content_type: Literal["text", "html", "markdown"] = "text"
    attachments: list[dict] = []          # 附件列表

    # === 上下文 ===
    context: dict[str, Any] = {}          # 额外上下文信息
    metadata: dict[str, Any] = {}         # 元数据

    # === 时间戳 ===
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # === 处理控制 ===
    priority: Literal["low", "normal", "high"] = "normal"
    idempotency_key: Optional[str] = None  # 幂等键


class EventResponse(BaseModel):
    """统一响应模型"""

    event_id: str
    status: Literal["accepted", "processing", "completed", "failed"]
    message: Optional[str] = None
    data: Optional[dict] = None
    workflow_id: Optional[str] = None     # 如果触发了 Workflow
```

#### 2.2.3 各渠道适配器实现

```python
# adapters/base.py

from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """适配器基类"""

    @abstractmethod
    async def to_unified_event(self, raw_data: dict) -> UnifiedEvent:
        """将原始数据转换为统一事件"""
        pass

    @abstractmethod
    async def send_response(self, event: UnifiedEvent, response: dict) -> None:
        """发送响应回原渠道"""
        pass


# adapters/feishu_adapter.py

class FeishuAdapter(BaseAdapter):
    """飞书适配器"""

    async def to_unified_event(self, raw_data: dict) -> UnifiedEvent:
        """飞书消息 → 统一事件"""

        # 飞书消息结构
        # {
        #     "event": {
        #         "message": {
        #             "message_id": "xxx",
        #             "content": "{\"text\":\"你好\"}",
        #             "chat_id": "oc_xxx"
        #         },
        #         "sender": {
        #             "sender_id": {"open_id": "ou_xxx"},
        #             "sender_type": "user"
        #         }
        #     }
        # }

        event_data = raw_data.get("event", {})
        message = event_data.get("message", {})
        sender = event_data.get("sender", {})

        # 解析消息内容
        content_json = json.loads(message.get("content", "{}"))
        content = content_json.get("text", "")

        return UnifiedEvent(
            event_type="chat",
            source="feishu",
            source_id=message.get("message_id"),
            user_external_id=sender.get("sender_id", {}).get("open_id"),
            session_id=message.get("chat_id"),
            content=content,
            context={
                "chat_type": message.get("chat_type"),
                "message_type": message.get("message_type"),
            },
            metadata={"raw": raw_data}
        )

    async def send_response(self, event: UnifiedEvent, response: dict) -> None:
        """发送飞书消息"""
        # 调用飞书 API 发送消息
        pass


# adapters/email_adapter.py

class EmailAdapter(BaseAdapter):
    """邮件适配器"""

    async def to_unified_event(self, raw_data: dict) -> UnifiedEvent:
        """邮件 → 统一事件"""

        # raw_data 结构（由邮件监听服务解析后）
        # {
        #     "message_id": "<xxx@mail.com>",
        #     "from": "sender@example.com",
        #     "to": ["receiver@example.com"],
        #     "subject": "询价 - 产品A",
        #     "body": "请报价...",
        #     "attachments": [{"filename": "spec.pdf", "path": "oss://..."}]
        # }

        return UnifiedEvent(
            event_type="email",
            source="email",
            source_id=raw_data.get("message_id"),
            user_name=raw_data.get("from"),
            thread_id=raw_data.get("in_reply_to"),  # 回复链
            content=raw_data.get("body", ""),
            content_type="html" if "<html" in raw_data.get("body", "") else "text",
            attachments=raw_data.get("attachments", []),
            context={
                "subject": raw_data.get("subject"),
                "to": raw_data.get("to"),
                "cc": raw_data.get("cc"),
            },
            metadata={"raw_headers": raw_data.get("headers", {})}
        )


# adapters/webhook_adapter.py

class WebhookAdapter(BaseAdapter):
    """通用 Webhook 适配器"""

    async def to_unified_event(self, raw_data: dict, webhook_type: str) -> UnifiedEvent:
        """Webhook → 统一事件"""

        # 根据 webhook_type 解析不同格式
        # 支持: github, stripe, custom 等

        return UnifiedEvent(
            event_type="webhook",
            source="webhook",
            source_id=raw_data.get("id") or str(uuid4()),
            content=json.dumps(raw_data),
            content_type="text",
            context={
                "webhook_type": webhook_type,
                "headers": raw_data.get("_headers", {}),
            },
            metadata={"raw": raw_data}
        )


# adapters/chat_adapter.py

class ChatAdapter(BaseAdapter):
    """Chatbox 适配器"""

    async def to_unified_event(self, raw_data: dict, user_id: str) -> UnifiedEvent:
        """Chatbox 消息 → 统一事件"""

        return UnifiedEvent(
            event_type="chat",
            source="chatbox",
            user_id=user_id,
            session_id=raw_data.get("session_id"),
            content=raw_data.get("message", ""),
            context={
                "agent_id": raw_data.get("agent_id"),
            }
        )
```

#### 2.2.4 事件分发服务

```python
# services/event_dispatcher.py

class EventDispatcher:
    """事件分发器 - 将统一事件路由到对应处理流程"""

    def __init__(
        self,
        redis_client,
        temporal_client,
        intent_classifier
    ):
        self.redis = redis_client
        self.temporal = temporal_client
        self.classifier = intent_classifier

    async def dispatch(self, event: UnifiedEvent) -> EventResponse:
        """分发事件到对应处理流程"""

        # 1. 幂等检查
        if event.idempotency_key:
            if await self._is_duplicate(event.idempotency_key):
                return EventResponse(
                    event_id=event.event_id,
                    status="accepted",
                    message="Duplicate event, already processed"
                )

        # 2. 写入事件流（用于审计和回放）
        await self._log_event(event)

        # 3. 根据事件类型路由
        if event.event_type == "chat":
            return await self._handle_chat(event)
        elif event.event_type == "email":
            return await self._handle_email(event)
        elif event.event_type == "webhook":
            return await self._handle_webhook(event)
        elif event.event_type == "approval":
            return await self._handle_approval(event)
        else:
            return await self._handle_generic(event)

    async def _handle_chat(self, event: UnifiedEvent) -> EventResponse:
        """处理对话事件 - 直接调用 Agent"""
        # 对话场景通常是同步/流式响应
        # 不需要启动 Workflow
        return EventResponse(
            event_id=event.event_id,
            status="processing"
        )

    async def _handle_email(self, event: UnifiedEvent) -> EventResponse:
        """处理邮件事件 - 启动 Workflow"""

        # 1. 意图分类
        intent = await self.classifier.classify(event.content)

        # 2. 根据意图启动对应 Workflow
        workflow_map = {
            "inquiry": "QuoteWorkflow",
            "order": "OrderWorkflow",
            "support": "SupportWorkflow",
            "unknown": "ManualReviewWorkflow",
        }

        workflow_name = workflow_map.get(intent, "ManualReviewWorkflow")

        # 3. 启动 Temporal Workflow
        workflow_id = f"{workflow_name}-{event.event_id}"
        handle = await self.temporal.start_workflow(
            workflow_name,
            event.model_dump(),
            id=workflow_id,
            task_queue="main-queue"
        )

        return EventResponse(
            event_id=event.event_id,
            status="processing",
            workflow_id=workflow_id,
            data={"intent": intent}
        )

    async def _log_event(self, event: UnifiedEvent):
        """记录事件到 Redis Streams"""
        await self.redis.xadd(
            "events:all",
            {"data": event.model_dump_json()},
            maxlen=100000  # 保留最近10万条
        )
```

#### 2.2.5 API 路由整合

```python
# api/events.py

from fastapi import APIRouter, Request, Depends

router = APIRouter(prefix="/events", tags=["Events"])

# === 飞书入口 ===
@router.post("/feishu")
async def feishu_callback(
    request: Request,
    adapter: FeishuAdapter = Depends(),
    dispatcher: EventDispatcher = Depends()
):
    """飞书机器人回调"""
    raw_data = await request.json()

    # 飞书验证请求
    if raw_data.get("type") == "url_verification":
        return {"challenge": raw_data.get("challenge")}

    event = await adapter.to_unified_event(raw_data)
    return await dispatcher.dispatch(event)


# === Webhook 入口 ===
@router.post("/webhook/{webhook_type}")
async def webhook_callback(
    webhook_type: str,
    request: Request,
    adapter: WebhookAdapter = Depends(),
    dispatcher: EventDispatcher = Depends()
):
    """通用 Webhook 回调"""
    raw_data = await request.json()
    raw_data["_headers"] = dict(request.headers)

    event = await adapter.to_unified_event(raw_data, webhook_type)
    return await dispatcher.dispatch(event)


# === 邮件入口（内部调用）===
@router.post("/email")
async def email_received(
    email_data: dict,
    adapter: EmailAdapter = Depends(),
    dispatcher: EventDispatcher = Depends()
):
    """邮件监听服务推送"""
    event = await adapter.to_unified_event(email_data)
    return await dispatcher.dispatch(event)
```

#### 2.2.6 事件表设计

```python
# models/event.py

class Event(Base):
    """事件记录表 - 所有入口事件的统一存储"""
    __tablename__ = "events"

    id = Column(String, primary_key=True)           # event_id
    event_type = Column(String, index=True)         # chat/email/webhook/...
    source = Column(String, index=True)             # web/feishu/email/...
    source_id = Column(String)                      # 来源唯一标识

    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    session_id = Column(String, nullable=True)

    content = Column(Text)
    content_type = Column(String, default="text")

    context = Column(JSON, default={})
    metadata = Column(JSON, default={})

    status = Column(String, default="received")     # received/processing/completed/failed
    workflow_id = Column(String, nullable=True)     # 关联的 Workflow

    created_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_event_source_time", source, created_at),
        Index("idx_event_user", user_id, created_at),
    )
```

### 2.3 数据流示例：邮件处理

```
新邮件到达
    ↓
① 邮件监听服务捕获 → EmailAdapter → UnifiedEvent
    ↓
② EventDispatcher 分发 → 写入 Redis Streams
    ↓
③ 意图分类 → 路由到对应 Workflow
    ↓
④ Temporal 启动邮件处理 Workflow → Workflow Engine
    ↓
⑤ 调用邮件分析 Agent (LangGraph)
    ↓
⑥ Agent 调用 Claude API 分析意图 → LLM Gateway
    ↓
⑦ 根据意图路由到对应处理
    ├─ 询价 → 报价 Agent → 生成报价单 → 审批
    ├─ 订单 → 订单 Agent → 创建订单
    └─ 其他 → 通知人工处理
    ↓
⑧ 结果存储到 PostgreSQL / 阿里云 OSS → Storage Layer
    ↓
⑨ 通过原渠道适配器发送响应
```

---

## 三、技术栈选型

### 3.1 核心技术栈

| 层级 | 组件 | 技术选型 | 版本 | 选择理由 | 未来扩展 |
|------|------|----------|------|----------|----------|
| **API** | Web框架 | FastAPI | 0.109+ | 高性能、自动文档、异步支持 | - |
| **API** | 数据校验 | Pydantic | 2.x | 类型安全、自动序列化 | - |
| **API** | 服务器 | uvicorn | 0.27+ | ASGI、高性能 | gunicorn 多进程 |
| **消息** | 消息队列 | Redis Streams | 7.x | 简单、持久化、够用 | Kafka（超大规模） |
| **消息** | 实时通知 | Redis Pub/Sub | 7.x | 推送状态更新 | - |
| **消息** | 缓存 | Redis | 7.x | 和消息层共用 | - |
| **Workflow** | 流程引擎 | Temporal | latest | 持久化、重试、审批、复杂定时 | - |
| **调度** | 轻量定时 | APScheduler | 3.10+ | 简单轮询、无额外组件 | Celery Beat（分布式） |
| **Agent** | Agent框架 | LangGraph | 0.0.26+ | 状态机清晰、不依赖LangChain | - |
| **LLM** | 模型网关 | LiteLLM | 1.23+ | 统一接口、一行换模型 | - |
| **LLM** | 主力模型 | Claude | Opus 4.5 | 效果最好、推理能力强 | - |
| **LLM** | 备选模型 | GPT-4 | latest | 生态广、备选方案 | 本地模型 |
| **Tools** | 工具封装 | 自己实现 | - | 更可控、好调试 | - |
| **存储** | 主数据库 | PostgreSQL | 16.x | 功能强、JSON支持好 | - |
| **存储** | 向量搜索 | pgvector | 0.6+ | 不加组件、和主库一起 | Qdrant（亿级向量） |
| **存储** | 文件存储 | 阿里云 OSS | - | 国内快、有CDN、便宜 | AWS S3（海外） |
| **存储** | 数据迁移 | Alembic | 1.13+ | SQLAlchemy 官方工具 | - |
| **前端** | Web框架 | Next.js | 14.x | React生态、全栈能力 | - |
| **前端** | UI组件 | shadcn/ui | latest | 美观、可定制 | - |
| **前端** | 状态管理 | Zustand | 4.x | 简单轻量 | - |
| **部署** | 容器化 | Docker Compose | latest | 开发方便、一键启动 | Kubernetes |

### 3.2 关键设计决策

| 决策点 | 选择 | 不选 | 原因 | 未来可能切换 |
|--------|------|------|------|--------------|
| LLM调用 | LiteLLM | LangChain | 更简单、统一接口 | - |
| Agent框架 | LangGraph | LangChain Agent | 可单独用、更可控 | - |
| Tool封装 | 自己写 | LangChain @tool | 更透明、好调试 | - |
| 向量检索 | pgvector | Qdrant | 少一个服务、够用 | Qdrant（向量>500万） |
| 消息队列 | Redis | Kafka/RabbitMQ | 简单够用、减少组件 | Kafka（超高吞吐） |
| 实时通信 | SSE | WebSocket | 流式输出更适合 | WebSocket（双向通信） |
| 工作流引擎 | Temporal | Celery | 持久化、审批等待原生支持 | - |
| 复杂定时 | Temporal Schedules | - | 报表、归档等复杂任务 | - |
| 轻量轮询 | APScheduler | Celery Beat | 邮件拉取、心跳等简单任务 | Celery Beat（分布式/持久化） |
| 文件存储 | 阿里云 OSS | MinIO | 国内用户、免运维 | MinIO（纯私有化） |
| 权限管理 | 简单角色检查 | Casbin | 团队小、够用 | Casbin（多租户/商业化） |

### 3.3 向量存储：pgvector vs Qdrant

| 对比项 | pgvector (当前选择) | Qdrant (未来扩展) |
|--------|---------------------|-------------------|
| 部署 | PostgreSQL 扩展，零额外组件 | 独立服务，需要单独部署 |
| 性能 | 百万级向量够用 | 亿级向量，高并发场景 |
| 功能 | 基础相似度搜索 | 过滤、分组、多向量、Payload |
| 运维 | 和 PG 一起备份 | 单独备份、监控 |
| 学习成本 | SQL 语法 | 新 API |
| **适用场景** | 文档数 < 100万，QPS < 100 | 文档数 > 500万，QPS > 1000 |

**pgvector 使用示例：**

```sql
-- 启用扩展
CREATE EXTENSION vector;

-- 创建带向量的表
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(1536)  -- OpenAI/Claude embedding 维度
);

-- 创建索引（IVFFlat，适合百万级）
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 相似度搜索
SELECT content, 1 - (embedding <=> $1) AS similarity
FROM documents
ORDER BY embedding <=> $1
LIMIT 10;
```

**迁移到 Qdrant 的时机：**
- 向量数据 > 500万条
- 搜索 QPS > 100
- 需要复杂过滤（按时间、标签等）
- 需要多租户数据隔离

### 3.4 文件存储：阿里云 OSS

```python
import oss2

# 初始化 OSS 客户端
auth = oss2.Auth(os.getenv("OSS_ACCESS_KEY"), os.getenv("OSS_SECRET_KEY"))
bucket = oss2.Bucket(auth, os.getenv("OSS_ENDPOINT"), os.getenv("OSS_BUCKET"))

# 上传文件
bucket.put_object("quotes/123.pdf", pdf_content)

# 生成临时访问链接（1小时有效）
url = bucket.sign_url("GET", "quotes/123.pdf", 3600)

# 下载文件
result = bucket.get_object("quotes/123.pdf")
content = result.read()
```

**环境变量配置：**
```bash
OSS_ACCESS_KEY=your_access_key
OSS_SECRET_KEY=your_secret_key
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=concord-ai-files
```

### 3.5 Chatbox 专用技术

| 功能 | 技术 | 说明 |
|------|------|------|
| 实时通信 | SSE (Server-Sent Events) | 流式输出、比WebSocket简单 |
| 流式输出 | LiteLLM stream=True | LLM原生支持 |
| 会话管理 | PostgreSQL | chat_sessions 表 |
| 消息存储 | PostgreSQL | chat_messages 表 |
| 上下文管理 | Redis + PostgreSQL | 短期Redis、长期PG |
| 前端组件 | React + SSE Client | 逐字显示效果 |

### 3.6 认证与安全

| 功能 | 技术 | 说明 | 未来扩展 |
|------|------|------|----------|
| 认证方式 | JWT | Access Token (15min) + Refresh Token (7d) | OAuth2.0 |
| 密码加密 | bcrypt | passlib 库 | - |
| Token黑名单 | Redis | 登出时加入黑名单 | - |
| 幂等性 | 三层防护 | RequestID → Redis锁 → DB唯一约束 | - |
| 权限管理 | 简单角色 | admin/user 两级 | Casbin（多租户） |

#### 3.6.1 系统管理员后台

系统管理员后台是一个**独立的管理界面**，仅供系统管理员使用。

**设计原则：**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           系统架构                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐          ┌─────────────────────┐                   │
│  │    用户端 (Web)      │          │   管理员后台 (Admin)  │                   │
│  │                     │          │                     │                   │
│  │  • 普通用户使用      │          │  • 仅管理员可访问     │                   │
│  │  • Chatbox 对话     │          │  • 系统配置管理       │                   │
│  │  • 任务查看         │          │  • 用户管理          │                   │
│  │  • 审批操作         │          │  • Agent 配置        │                   │
│  │                     │          │  • 日志查看          │                   │
│  └──────────┬──────────┘          └──────────┬──────────┘                   │
│             │                                │                              │
│             │      ┌─────────────────────────┤                              │
│             │      │                         │                              │
│             ▼      ▼                         ▼                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        API Layer (FastAPI)                           │   │
│  │  ┌───────────────────┐          ┌───────────────────┐               │   │
│  │  │  /api/*           │          │  /admin/*          │               │   │
│  │  │  (user/admin)     │          │  (admin only)      │               │   │
│  │  │                   │          │                    │               │   │
│  │  │  get_current_user │          │  get_current_admin │               │   │
│  │  └───────────────────┘          └───────────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**角色定义：**

| 角色 | 标识 | 权限 | 说明 |
|------|------|------|------|
| 系统管理员 | `admin` | 全部 | 可访问所有功能，包括管理员后台 |
| 普通用户 | `user` | 基础 | 只能访问用户端功能 |

**管理员后台功能：**

| 模块 | 功能 | API 前缀 |
|------|------|----------|
| 用户管理 | 创建/禁用/删除用户，重置密码 | `/admin/users` |
| Agent 配置 | 启用/禁用 Agent，配置参数 | `/admin/agents` |
| 系统配置 | LLM 模型、邮件配置等 | `/admin/settings` |
| 日志查看 | 系统日志、操作审计 | `/admin/logs` |
| Workflow 管理 | 查看/取消 Workflow | `/admin/workflows` |

**认证实现：**

```python
# core/security.py

async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前管理员用户

    非管理员访问 /admin/* 接口时返回 403 Forbidden
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user


# api/admin.py

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users")
async def list_users(
    admin: User = Depends(get_current_admin_user),  # 仅管理员
    db: AsyncSession = Depends(get_db)
):
    """获取所有用户列表"""
    ...

@router.post("/users/{user_id}/disable")
async def disable_user(
    user_id: str,
    admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """禁用用户"""
    ...
```

**初始管理员：**

系统首次部署时，通过环境变量或命令行创建初始管理员：

```bash
# 方式一：环境变量
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure_password

# 方式二：命令行（推荐）
python -m app.scripts.create_admin --email admin@example.com --password xxx
```

**安全措施：**

- 管理员后台独立路由前缀 `/admin/*`
- 所有管理员接口强制要求 `role=admin`
- 敏感操作记录审计日志
- 管理员密码强度要求更高
- 管理员 Token 过期时间更短（可选）

### 3.7 定时任务分层设计

定时任务根据复杂度分为两层处理：

#### 3.7.1 任务分工

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           定时任务分层                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  APScheduler（轻量级轮询，进程内）                                           │
│  ├── 邮件拉取（每 1-5 分钟）                                                 │
│  ├── 健康检查（每 30 秒）                                                    │
│  ├── 缓存预热/清理（每小时）                                                 │
│  ├── 外部 API 状态检测                                                      │
│  └── 简单的数据同步                                                         │
│                                                                             │
│  Temporal Schedule（复杂工作流定时触发）                                     │
│  ├── 每日报表生成（需要多步骤处理）                                          │
│  ├── 每周数据归档（需要持久化状态）                                          │
│  ├── 定期审批提醒（需要等待人工响应）                                        │
│  ├── 批量数据处理（需要失败重试）                                            │
│  └── 跨服务编排任务                                                         │
│                                                                             │
│  未来扩展：Celery Beat（分布式、持久化）                                     │
│  └── 当 APScheduler 无法满足时（多实例部署、任务持久化需求）                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.7.2 APScheduler 实现

```python
# services/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

# === 邮件拉取任务 ===
async def poll_emails():
    """每分钟拉取新邮件"""
    email_service = get_email_service()
    new_emails = await email_service.fetch_new_emails()

    for email in new_emails:
        event = await email_adapter.to_unified_event(email)
        await event_dispatcher.dispatch(event)

scheduler.add_job(
    poll_emails,
    trigger=IntervalTrigger(minutes=1),
    id="email_polling",
    replace_existing=True,
    max_instances=1  # 防止任务堆积
)

# === 健康检查任务 ===
async def health_check():
    """每30秒检查外部服务状态"""
    services = ["llm", "oss", "temporal"]
    for service in services:
        status = await check_service_health(service)
        if not status:
            logger.warning(f"Service {service} is unhealthy")

scheduler.add_job(
    health_check,
    trigger=IntervalTrigger(seconds=30),
    id="health_check",
    replace_existing=True
)

# === 缓存清理任务 ===
async def cleanup_expired_cache():
    """每小时清理过期缓存"""
    await redis_client.cleanup_expired_keys("cache:*")

scheduler.add_job(
    cleanup_expired_cache,
    trigger=CronTrigger(minute=0),  # 每小时整点
    id="cache_cleanup",
    replace_existing=True
)

# === FastAPI 集成 ===
@app.on_event("startup")
async def startup():
    scheduler.start()
    logger.info("APScheduler started")

@app.on_event("shutdown")
async def shutdown():
    scheduler.shutdown(wait=True)
    logger.info("APScheduler stopped")
```

#### 3.7.3 Temporal Schedule 实现

```python
# workflows/schedules.py

from temporalio.client import Client, Schedule, ScheduleSpec, ScheduleActionStartWorkflow
from temporalio.client import ScheduleIntervalSpec
from datetime import timedelta

async def setup_temporal_schedules(client: Client):
    """设置 Temporal 定时任务"""

    # === 每日报表生成 ===
    await client.create_schedule(
        "daily-report",
        Schedule(
            action=ScheduleActionStartWorkflow(
                DailyReportWorkflow.run,
                id="daily-report",
                task_queue="main-queue",
            ),
            spec=ScheduleSpec(
                cron_expressions=["0 9 * * *"]  # 每天早上9点
            ),
        ),
    )

    # === 每周数据归档 ===
    await client.create_schedule(
        "weekly-archive",
        Schedule(
            action=ScheduleActionStartWorkflow(
                DataArchiveWorkflow.run,
                id="weekly-archive",
                task_queue="main-queue",
            ),
            spec=ScheduleSpec(
                cron_expressions=["0 2 * * 0"]  # 每周日凌晨2点
            ),
        ),
    )

    # === 审批超时提醒（每4小时检查）===
    await client.create_schedule(
        "approval-reminder",
        Schedule(
            action=ScheduleActionStartWorkflow(
                ApprovalReminderWorkflow.run,
                id="approval-reminder",
                task_queue="main-queue",
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(hours=4))]
            ),
        ),
    )
```

#### 3.7.4 选择决策树

```
需要定时执行的任务
        │
        ▼
    任务复杂吗？
    ├─ 否（简单轮询、几秒完成）
    │       │
    │       ▼
    │   APScheduler ✓
    │   • 邮件拉取
    │   • 健康检查
    │   • 缓存清理
    │
    └─ 是（多步骤、需要状态）
            │
            ▼
        Temporal Schedule ✓
        • 报表生成
        • 数据归档
        • 审批提醒

如果遇到以下情况，考虑迁移到 Celery Beat：
• 需要多实例部署，任务不能重复执行
• 需要任务执行记录持久化
• 需要动态增删定时任务（运行时）
• 需要分布式锁保证
```

### 3.8 Ingest Pipeline（文档摄入）

知识库的核心是将文档转换为可检索的向量。Ingest Pipeline 负责这个过程。

#### 3.7.1 Ingest 流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Ingest Pipeline                                   │
│                                                                             │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │  上传   │ -> │  解析   │ -> │  分块   │ -> │ Embed  │ -> │  存储   │  │
│  │ Upload │    │  Parse  │    │  Chunk  │    │         │    │  Store  │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       │              │              │              │              │        │
│       ▼              ▼              ▼              ▼              ▼        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ 阿里云  │    │ PDF     │    │ 递归    │    │ Claude  │    │ PG +    │  │
│  │ OSS    │    │ Word    │    │ 分块    │    │ /OpenAI │    │pgvector │  │
│  │        │    │ HTML    │    │ 512字符 │    │Embedding│    │         │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.7.2 Ingest 技术栈

| 阶段 | 技术 | 说明 | 未来扩展 |
|------|------|------|----------|
| **文件上传** | 阿里云 OSS | 原始文件存储 | - |
| **PDF 解析** | PyMuPDF (fitz) | 快速、准确 | Unstructured |
| **Word 解析** | python-docx | .docx 文件 | - |
| **HTML 解析** | BeautifulSoup | 网页内容 | - |
| **Excel 解析** | openpyxl | 表格数据 | - |
| **文本分块** | 递归字符分割 | 自己实现，简单可控 | LangChain Splitter |
| **Embedding** | LiteLLM | 统一接口，支持多模型 | - |
| **向量存储** | pgvector | 和业务数据在一起 | Qdrant |

#### 3.7.3 分块策略

```python
# services/chunker.py

class RecursiveChunker:
    """递归字符分割器"""

    def __init__(
        self,
        chunk_size: int = 512,      # 每块大小
        chunk_overlap: int = 50,     # 重叠字符数
        separators: list = None      # 分割符优先级
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",  # 段落
            "\n",    # 换行
            "。",    # 句号（中文）
            ".",     # 句号（英文）
            " ",     # 空格
            ""       # 字符
        ]

    def split(self, text: str) -> list[str]:
        """递归分割文本"""
        chunks = []
        self._split_recursive(text, self.separators, chunks)
        return chunks

    def _split_recursive(self, text: str, separators: list, chunks: list):
        if len(text) <= self.chunk_size:
            if text.strip():
                chunks.append(text.strip())
            return

        # 找到合适的分割符
        separator = separators[0] if separators else ""

        if separator:
            parts = text.split(separator)
        else:
            # 最后手段：按字符切割
            for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
                chunk = text[i:i + self.chunk_size]
                if chunk.strip():
                    chunks.append(chunk.strip())
            return

        # 合并小块
        current_chunk = ""
        for part in parts:
            if len(current_chunk) + len(part) + len(separator) <= self.chunk_size:
                current_chunk += (separator if current_chunk else "") + part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = part

        if current_chunk.strip():
            chunks.append(current_chunk.strip())
```

#### 3.7.4 Embedding 服务

```python
# services/embedding_service.py

from litellm import embedding
import asyncio

class EmbeddingService:
    """Embedding 服务，支持批量处理"""

    def __init__(
        self,
        model: str = "text-embedding-3-small",  # OpenAI
        # model: str = "voyage-2",              # Voyage AI
        batch_size: int = 100
    ):
        self.model = model
        self.batch_size = batch_size

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量生成 embedding"""
        embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            response = await asyncio.to_thread(
                embedding,
                model=self.model,
                input=batch
            )
            embeddings.extend([item["embedding"] for item in response.data])

        return embeddings

    async def embed_single(self, text: str) -> list[float]:
        """单条文本 embedding"""
        response = await asyncio.to_thread(
            embedding,
            model=self.model,
            input=[text]
        )
        return response.data[0]["embedding"]
```

#### 3.7.5 完整 Ingest 服务

```python
# services/ingest_service.py

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from bs4 import BeautifulSoup

class IngestService:
    """文档摄入服务"""

    def __init__(
        self,
        chunker: RecursiveChunker,
        embedding_service: EmbeddingService,
        db: AsyncSession,
        oss_client
    ):
        self.chunker = chunker
        self.embedding_service = embedding_service
        self.db = db
        self.oss = oss_client

    async def ingest_file(
        self,
        file_path: str,
        file_type: str,
        metadata: dict = None
    ) -> dict:
        """
        完整的文档摄入流程

        Returns:
            {"document_id": str, "chunks_count": int}
        """
        # 1. 解析文档
        text = await self._parse_file(file_path, file_type)

        # 2. 分块
        chunks = self.chunker.split(text)

        # 3. 生成 embedding
        embeddings = await self.embedding_service.embed_texts(chunks)

        # 4. 存储到数据库
        document_id = await self._store_chunks(
            chunks=chunks,
            embeddings=embeddings,
            source_file=file_path,
            metadata=metadata or {}
        )

        return {
            "document_id": document_id,
            "chunks_count": len(chunks)
        }

    async def _parse_file(self, file_path: str, file_type: str) -> str:
        """解析不同格式的文件"""

        # 从 OSS 下载文件
        content = self.oss.get_object(file_path).read()

        if file_type == "pdf":
            return self._parse_pdf(content)
        elif file_type == "docx":
            return self._parse_docx(content)
        elif file_type == "html":
            return self._parse_html(content)
        elif file_type == "txt":
            return content.decode("utf-8")
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def _parse_pdf(self, content: bytes) -> str:
        """解析 PDF"""
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def _parse_docx(self, content: bytes) -> str:
        """解析 Word 文档"""
        import io
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join([para.text for para in doc.paragraphs])

    def _parse_html(self, content: bytes) -> str:
        """解析 HTML"""
        soup = BeautifulSoup(content, "html.parser")
        # 移除 script 和 style
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n")

    async def _store_chunks(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        source_file: str,
        metadata: dict
    ) -> str:
        """存储分块到 pgvector"""
        from uuid import uuid4

        document_id = str(uuid4())

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=i,
                content=chunk,
                embedding=embedding,
                source_file=source_file,
                metadata={**metadata, "chunk_index": i}
            )
            self.db.add(doc)

        await self.db.commit()
        return document_id
```

#### 3.7.6 Ingest API

```python
# api/ingest.py

from fastapi import APIRouter, UploadFile, File, BackgroundTasks

router = APIRouter(prefix="/ingest", tags=["Ingest"])

@router.post("/upload")
async def upload_and_ingest(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    ingest_service: IngestService = Depends(get_ingest_service)
):
    """
    上传文件并摄入知识库

    支持格式: PDF, DOCX, HTML, TXT
    """
    # 1. 上传到 OSS
    file_path = f"documents/{uuid4()}/{file.filename}"
    content = await file.read()
    oss_client.put_object(file_path, content)

    # 2. 获取文件类型
    file_type = file.filename.split(".")[-1].lower()

    # 3. 后台处理 ingest（大文件异步）
    if len(content) > 1_000_000:  # > 1MB
        background_tasks.add_task(
            ingest_service.ingest_file,
            file_path=file_path,
            file_type=file_type,
            metadata={"filename": file.filename}
        )
        return {"status": "processing", "file_path": file_path}

    # 4. 小文件同步处理
    result = await ingest_service.ingest_file(
        file_path=file_path,
        file_type=file_type,
        metadata={"filename": file.filename}
    )

    return {"status": "completed", **result}


@router.post("/url")
async def ingest_from_url(
    url: str,
    ingest_service: IngestService = Depends(get_ingest_service)
):
    """从 URL 抓取内容并摄入"""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        content = response.text

    # 存储 HTML 到 OSS
    file_path = f"documents/urls/{uuid4()}.html"
    oss_client.put_object(file_path, content.encode())

    # Ingest
    result = await ingest_service.ingest_file(
        file_path=file_path,
        file_type="html",
        metadata={"source_url": url}
    )

    return {"status": "completed", **result}
```

#### 3.7.7 检索服务（配合 Ingest 使用）

```python
# services/retrieval_service.py

class RetrievalService:
    """向量检索服务"""

    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_service = embedding_service

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> list[dict]:
        """
        相似度搜索

        Returns:
            [{"content": str, "similarity": float, "metadata": dict}, ...]
        """
        # 1. Query embedding
        query_embedding = await self.embedding_service.embed_single(query)

        # 2. pgvector 搜索
        result = await self.db.execute(
            text("""
                SELECT
                    content,
                    1 - (embedding <=> :query_embedding) AS similarity,
                    metadata,
                    source_file
                FROM document_chunks
                WHERE 1 - (embedding <=> :query_embedding) > :min_similarity
                ORDER BY embedding <=> :query_embedding
                LIMIT :top_k
            """),
            {
                "query_embedding": str(query_embedding),
                "min_similarity": min_similarity,
                "top_k": top_k
            }
        )

        return [
            {
                "content": row.content,
                "similarity": row.similarity,
                "metadata": row.metadata,
                "source_file": row.source_file
            }
            for row in result.fetchall()
        ]
```

#### 3.7.8 数据模型

```python
# models/document.py

from pgvector.sqlalchemy import Vector

class DocumentChunk(Base):
    """文档分块表"""
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True)
    document_id = Column(String, index=True)          # 原始文档 ID
    chunk_index = Column(Integer)                      # 分块序号
    content = Column(Text)                             # 文本内容
    embedding = Column(Vector(1536))                   # 向量（维度取决于模型）
    source_file = Column(String)                       # OSS 文件路径
    metadata = Column(JSON, default={})                # 元数据
    created_at = Column(DateTime, default=func.now())

    # 索引
    __table_args__ = (
        Index("idx_embedding", embedding, postgresql_using="ivfflat"),
    )
```

---

## 四、核心模块设计

### 4.1 可插拔 Agent 设计

Agent 通过注册中心管理，每个 Agent 定义标准接口：

```yaml
# agents/quote_agent.yaml
agent:
  id: quote_agent
  name: 报价准备
  description: 处理询价邮件，自动生成报价单
  version: 1.0.0
  enabled: true

triggers:
  - type: email_intent
    conditions:
      intent: ["询价", "报价请求", "price inquiry"]
  - type: manual
    description: 手动触发报价流程

workflow:
  steps:
    - id: extract_requirements
      action: llm_extract
      prompt_template: extract_quote_requirements
      output: requirements

    - id: search_products
      action: tool_call
      tool: product_search
      input: "{{requirements.products}}"
      output: products

    - id: calculate_price
      action: tool_call
      tool: price_calculator
      input:
        products: "{{products}}"
        quantity: "{{requirements.quantity}}"
      output: pricing

    - id: generate_quote
      action: tool_call
      tool: pdf_generator
      template: quote_template
      input: "{{pricing}}"
      output: quote_pdf

    - id: approval_check
      action: approval
      condition: "{{pricing.total > 100000}}"
      approvers: ["sales_manager"]
      timeout: 24h
      on_timeout: remind

    - id: send_quote
      action: tool_call
      tool: email_send
      input:
        to: "{{original_email.from}}"
        subject: "报价单 - {{requirements.title}}"
        attachment: "{{quote_pdf}}"

tools_required:
  - product_search
  - price_calculator
  - pdf_generator
  - email_send

permissions:
  - read:products
  - read:customers
  - write:quotes
  - send:email
```

### 4.2 审批流设计（Temporal Signal）

```python
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class QuoteWorkflow:
    def __init__(self):
        self.approval_result = None

    @workflow.run
    async def run(self, quote_data: dict):
        # 生成报价单
        quote = await workflow.execute_activity(
            generate_quote, quote_data,
            start_to_close_timeout=timedelta(minutes=5)
        )

        # 金额超过10万需要审批
        if quote["total"] > 100000:
            # 发送审批通知（飞书/邮件）
            await workflow.execute_activity(
                send_approval_notification,
                {"quote_id": quote["id"], "approvers": ["manager"]},
                start_to_close_timeout=timedelta(minutes=1)
            )

            # 等待审批 Signal，最多7天
            await workflow.wait_condition(
                lambda: self.approval_result is not None,
                timeout=timedelta(days=7)
            )

            if self.approval_result != "approved":
                return {"status": "rejected"}

        # 发送报价单
        await workflow.execute_activity(send_quote_email, quote)
        return {"status": "completed", "quote_id": quote["id"]}

    @workflow.signal
    async def approve(self, decision: str):
        self.approval_result = decision
```

**审批触发方式（不需要前端）：**
- API 接口
- 飞书机器人卡片回调
- 邮件回复解析
- CLI 命令

### 4.3 幂等性三层防护

```python
# 第一层：Request ID 快速去重
@app.middleware("http")
async def idempotency_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")
    if request_id:
        if await redis.exists(f"idempotent:{request_id}"):
            return cached_response
    return await call_next(request)

# 第二层：Redis 分布式锁
async def process_with_lock(key: str, ttl: int = 300):
    lock = await redis.set(f"lock:{key}", "1", nx=True, ex=ttl)
    if not lock:
        raise DuplicateRequestError()

# 第三层：数据库唯一约束
class Order(Base):
    idempotency_key = Column(String, unique=True, nullable=True)
```

---

## 五、数据模型

### 5.1 核心表结构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          数据关系图                                  │
│                                                                     │
│  CUSTOMER ─┬──< ORDER ──< ORDER_ITEM >── PRODUCT                   │
│            │                                │                       │
│            └──< QUOTE ──< QUOTE_ITEM >──────┘                       │
│                   │                                                 │
│                   └──< APPROVAL >── USER                            │
│                                                                     │
│  TASK ──< TASK_LOG                                                 │
│    │                                                               │
│    └── AGENT                                                       │
│                                                                     │
│  CHAT_SESSION ──< CHAT_MESSAGE                                     │
│                                                                     │
│  DOCUMENT (含 embedding 向量列，pgvector)                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 主要表定义

| 表名 | 用途 | 主要字段 |
|------|------|----------|
| **users** | 系统用户 | id, email, password_hash, name, role, is_active |
| **customers** | 客户信息 | id, name, company, email, metadata |
| **products** | 产品目录 | id, sku, name, price, specs, active |
| **orders** | 订单记录 | id, customer_id, status, total_amount, items, workflow_id, idempotency_key |
| **quotes** | 报价记录 | id, customer_id, status, total_amount, items, valid_until, workflow_id |
| **approvals** | 审批记录 | id, entity_type, entity_id, status, approvers, approved_by, decided_at |
| **chat_sessions** | 聊天会话 | id, user_id, title, agent_id, metadata |
| **chat_messages** | 聊天消息 | id, session_id, role, content, status, tool_calls |
| **tasks** | 任务记录 | id, agent_id, status, input, output, created_at |
| **documents** | 知识库文档 | id, content, embedding (vector), metadata |

### 5.3 数据存储分工

| 数据类型 | 存储位置 | 生命周期 | 未来扩展 |
|----------|----------|----------|----------|
| 用户、客户、订单、报价 | PostgreSQL | 永久 | - |
| 会话、消息历史 | PostgreSQL | 永久 | - |
| 审批记录 | PostgreSQL | 永久 | - |
| 文档 Embedding | PostgreSQL (pgvector) | 永久 | Qdrant |
| Workflow 状态 | Temporal (自动) | Workflow生命周期 | - |
| Session/Token | Redis | 短期（小时/天） | - |
| 幂等Key | Redis | 5分钟 | - |
| 对话短期上下文 | Redis | 对话期间 | - |
| 文件/附件 | 阿里云 OSS | 永久 | - |

---

## 六、AI 能力规划

### 6.1 Phase 1 核心能力（必须）

| # | 能力 | 说明 | 优先级 |
|---|------|------|--------|
| 1 | 文本生成 | 写邮件、报告、文案 | P0 |
| 2 | 文本摘要 | 长文档/邮件总结 | P0 |
| 5 | 分类/打标签 | 意图分类、邮件分类 | P0 |
| 7 | 实体提取 | 从邮件提取客户、产品、数量 | P0 |
| 10 | 对话/聊天 | Chatbox 多轮对话 | P0 |
| 26 | 工具调用 | LLM 调用外部 API/函数 | P0 |
| 27 | 多步骤任务执行 | Agent 工作流 | P0 |
| 30 | 邮件自动化 | 读取、发送、分类邮件 | P0 |
| 34 | 审批工作流 | 人机协作 | P0 |

### 6.2 Phase 2 增强能力（重要）

| # | 能力 | 说明 | 优先级 |
|---|------|------|--------|
| 11 | 文档问答 | 基于上传文档回答问题 | P1 |
| 12 | 知识库构建 | 内部知识库 | P1 |
| 13 | 向量检索 | Embedding + 相似度搜索 (pgvector) | P1 |
| 29 | 文件操作 | 读写、转换文件 | P1 |
| 32 | 消息/通知推送 | 飞书、钉钉通知 | P1 |
| 33 | 定时任务 | Temporal Schedules | P1 |
| 37 | PDF 处理 | 解析、生成 PDF | P1 |

### 6.3 Phase 3 扩展能力（未来）

| # | 能力 | 说明 | 优先级 |
|---|------|------|--------|
| 17 | 图像理解 | 看图回答问题 | P2 |
| 20 | OCR/文字识别 | 从图片提取文字 | P2 |
| 35 | 多 Agent 协作 | 复杂任务协同 | P2 |
| 36 | 表格/Excel 处理 | 分析、生成表格 | P2 |
| 42 | CRM 集成 | Salesforce 等 | P2 |
| 44 | 项目管理集成 | Jira、Notion 等 | P2 |

---

## 七、开发计划

### 7.1 总体时间线

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              开发路线图（10周）                                   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ Phase 1 │ Phase 2 │ Phase 3   │ Phase 4 │ Phase 5   │ Phase 6     │ Phase 7    │
│ Week1-2 │ Week 3  │ Week 4-5  │ Week 6  │ Week 7    │ Week 8-9    │ Week 10    │
│ 基础骨架 │ Workflow│ Agent层   │ Chatbox │ 完整流程  │ 前端界面    │ 完善优化   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 详细开发计划

#### Phase 1: 基础骨架（Week 1-2）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 项目初始化 | 创建项目结构、配置 Docker Compose | docker-compose.yml |
| FastAPI 框架 | API 入口、路由结构、中间件 | app/main.py |
| 数据库集成 | PostgreSQL + pgvector + Alembic | models/, alembic/ |
| Redis 集成 | 缓存、消息队列基础 | core/redis.py |
| OSS 集成 | 阿里云 OSS 文件上传下载 | services/storage.py |
| 认证模块 | JWT 认证、用户注册登录 | api/auth.py |
| 幂等性中间件 | 三层防护实现 | core/idempotency.py |

#### Phase 2: Workflow 集成（Week 3）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| Temporal 部署 | Docker 部署 Temporal Server | docker-compose.yml 更新 |
| Worker 实现 | Temporal Worker 基础代码 | workflows/worker.py |
| 第一个 Workflow | 简单的审批工作流 | workflows/definitions/approval.py |
| 定时任务 | Temporal Schedules 示例 | workflows/schedules.py |

#### Phase 3: Agent 层（Week 4-5）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| LiteLLM 集成 | 统一 LLM 调用接口 | services/llm_service.py |
| LangGraph 基础 | Agent 状态机框架 | agents/base.py |
| Agent 注册中心 | 动态加载 Agent | agents/registry.py |
| Tool 注册中心 | 工具管理 | tools/registry.py |
| 基础 Tools | 邮件、HTTP、数据库工具 | tools/ |
| 第一个 Agent | 邮件分析 Agent | agents/email_analyzer.py |

#### Phase 4: Chatbox（Week 6）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| SSE 端点 | 流式输出接口 | api/chat.py |
| 会话管理 | 会话创建、消息存储 | services/chat_service.py |
| 上下文管理 | 短期记忆（Redis）+ 长期（PG） | services/context_service.py |
| 对话 Agent | 通用对话处理 | agents/chat_agent.py |

#### Phase 5: 完整业务流程（Week 7）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 邮件监听 | IMAP 监听新邮件 | services/email_listener.py |
| 意图分类 | 邮件意图识别 | agents/intent_classifier.py |
| 报价 Agent | 完整报价流程 | agents/quote_agent.py |
| PDF 生成 | 报价单 PDF | tools/pdf_generator.py |
| 端到端测试 | 邮件→分析→报价→审批→发送 | tests/e2e/ |

#### Phase 6: 前端界面（Week 8-9）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| Next.js 初始化 | 项目结构、路由 | frontend/ |
| 认证页面 | 登录、注册 | app/auth/ |
| Dashboard | 任务概览、统计 | app/dashboard/ |
| Chatbox 组件 | SSE 对话界面 | components/ChatBox/ |
| 审批管理 | 待审批列表、操作 | app/approvals/ |

#### Phase 7: 完善优化（Week 10）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 日志系统 | 结构化日志 | core/logging.py |
| 单元测试 | 核心模块测试 | tests/unit/ |
| 集成测试 | API 测试 | tests/integration/ |
| 文档完善 | API 文档、部署文档 | docs/ |

---

## 八、部署与运维

### 8.1 项目目录结构

```
concord-ai/
├── docker-compose.yml          # 容器编排
├── .env.example                 # 环境变量模板
├── alembic/                     # 数据库迁移
│   ├── alembic.ini
│   └── versions/
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── api/                 # API 路由
│   │   ├── core/                # 核心模块
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic 模式
│   │   └── services/            # 业务服务
│   │
│   ├── workflows/               # Temporal Workflows
│   ├── agents/                  # LangGraph Agents
│   └── tools/                   # Tools
│
├── frontend/                    # Next.js 前端
└── docs/                        # 文档
```

### 8.2 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 3000 | Next.js 前端 |
| Backend API | 8000 | FastAPI (/docs 查看文档) |
| Temporal UI | 8080 | 查看 Workflow 状态 |
| PostgreSQL | 5432 | 主数据库 (含 pgvector) |
| Redis | 6379 | 缓存/消息 |

### 8.3 环境变量

```bash
# .env.example

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/concord

# Redis
REDIS_URL=redis://localhost:6379/0

# Temporal
TEMPORAL_HOST=localhost:7233

# 阿里云 OSS
OSS_ACCESS_KEY=your_access_key
OSS_SECRET_KEY=your_secret_key
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=concord-ai-files

# LLM
ANTHROPIC_API_KEY=your_api_key
OPENAI_API_KEY=your_api_key

# JWT
JWT_SECRET=your_jwt_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 8.4 核心依赖清单

**后端 (Python)**
```
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.0
sqlalchemy>=2.0
asyncpg>=0.29.0
alembic>=1.13.0
pgvector>=0.2.0
redis>=5.0
temporalio>=1.4.0
langgraph>=0.0.26
litellm>=1.23.0
apscheduler>=3.10.0
oss2>=2.18.0
python-jose>=3.3.0
passlib>=1.7.4
httpx>=0.26.0
```

**前端 (Node.js)**
```
next>=14.0.0
react>=18.2.0
typescript>=5.0.0
tailwindcss>=3.4.0
zustand>=4.5.0
@tanstack/react-query>=5.0.0
```

---

## 附录：未来扩展路径

| 当前方案 | 触发条件 | 扩展方案 |
|----------|----------|----------|
| pgvector | 向量 > 500万 或 QPS > 100 | Qdrant |
| APScheduler | 多实例部署 / 任务持久化 / 分布式锁 | Celery Beat |
| 简单角色 | 多租户 / 商业化 | Casbin |
| Redis Streams | 超高吞吐 | Kafka |
| 阿里云 OSS | 纯私有化部署 | MinIO |
| Docker Compose | 生产环境 | Kubernetes |
| 单实例 | 高可用 | 多实例 + 负载均衡 |

---

> **文档版本**: v1.2 Final
> **更新说明**: 新增入口统一设计、Ingest Pipeline、定时任务分层（APScheduler + Temporal Schedule）
