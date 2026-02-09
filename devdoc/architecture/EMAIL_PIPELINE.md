# 邮件处理管线

> 完整描述邮件从收取到分析的技术链路
> 合并自: EMAIL_PROCESSING_FLOW.md + EMAIL_CODE_PATH.md + EMAIL_SUMMARIZER_WORKFLOW.md

---

## 目录
1. [架构概览](#1-架构概览)
2. [核心组件](#2-核心组件)
3. [处理流程详解](#3-处理流程详解)
4. [代码调用链路](#4-代码调用链路)
5. [EmailSummarizer 工作流](#5-emailsummarizer-工作流)
6. [数据流向与数据结构](#6-数据流向与数据结构)
7. [监控与调试](#7-监控与调试)
8. [性能与优化](#8-性能与优化)
9. [故障排查](#9-故障排查)
10. [API 接口](#10-api-接口)

---

## 1. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        邮件处理完整流程                           │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ IMAP 邮箱     │      │ Redis Queue  │      │ PostgreSQL   │
│ (外部邮箱)    │─────>│ (消息队列)    │─────>│ (持久化)      │
└──────────────┘      └──────────────┘      └──────────────┘
       │                     │                      │
       │                     │                      │
       v                     v                      v
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Celery Beat  │      │ Celery Worker│      │ Redis Streams│
│ (定时调度)    │      │ (任务执行)    │      │ (事件流)      │
└──────────────┘      └──────────────┘      └──────────────┘
       │                     │                      │
       │                     │                      │
       v                     v                      v
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ poll_email   │      │process_email │      │ Dispatcher   │
│ (轮询任务)    │      │ (处理任务)    │      │ (意图分类)    │
└──────────────┘      └──────────────┘      └──────────────┘
                             │                      │
                             │                      │
                             v                      v
                      ┌──────────────┐      ┌──────────────┐
                      │ OSS/Local    │      │ Temporal     │
                      │ (附件存储)    │      │ (工作流)      │
                      └──────────────┘      └──────────────┘
```

---

## 2. 核心组件

### 2.1 Celery Beat（定时调度器）

**位置**: `backend/app/celery_app.py`

**功能**:
- 定时触发邮件轮询任务
- 由 `EmailWorkerService` 动态管理任务

**运行方式**:
```bash
cd backend
source venv/bin/activate
celery -A app.celery_app beat --loglevel=info
```

**配置**:
- 轮询间隔: 默认 60 秒（可在 `EmailWorkerService.sync_email_tasks()` 中配置）
- 每个邮箱账户都有独立的定时任务

---

### 2.2 Celery Worker（任务执行器）

**位置**: `backend/app/celery_app.py`

**功能**:
- 执行邮件拉取任务 (`poll_email_account`)
- 执行邮件处理任务 (`process_email`)
- 支持水平扩展（可启动多个 Worker 实例）

**运行方式**:
```bash
cd backend
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info --concurrency=10
```

**并发配置**:
- `--concurrency=10`: 每个 Worker 最多同时处理 10 个任务
- 可启动多个 Worker 实例实现负载均衡

---

### 2.3 EmailWorkerService（任务管理服务）

**位置**: `backend/app/services/email_worker_service.py`

**功能**:
- 动态管理 Celery Beat 的定时任务
- 为每个邮箱账户创建/删除轮询任务
- 监控任务状态

**API**:
```python
from app.services.email_worker_service import email_worker_service

# 同步所有邮箱账户的定时任务
await email_worker_service.sync_email_tasks(interval=60)

# 为单个账户添加任务
await email_worker_service.add_account_task(account_id=1, interval=60)

# 删除账户任务
await email_worker_service.remove_account_task(account_id=1)

# 获取任务状态
status = await email_worker_service.get_task_status()
```

---

## 3. 处理流程详解

### 阶段 1: 邮件轮询（Celery Beat → poll_email_account）

**触发方式**: Celery Beat 定时触发（默认 60 秒间隔）

**任务**: `poll_email_account(account_id: int)`

**位置**: `backend/app/tasks/email.py:50-168`

**流程**:

```python
1. 获取分布式锁（Redis）
   └─> 键名: email_worker:{account_id}:lock
   └─> 过期时间: 5 分钟
   └─> 防止多个实例重复处理

2. 查询邮箱账户配置
   └─> 从 email_accounts 表读取
   └─> 检查账户是否启用

3. 获取上次检查点（Redis）
   └─> 键名: email_worker:{account_id}:last_check
   └─> 默认: 1 天前

4. 拉取新邮件（IMAP）
   └─> 调用 imap_fetch(folder, limit=50, since, unseen_only=True)
   └─> 只拉取未读邮件

5. 将每封邮件作为独立任务加入队列
   └─> 调用 process_email.delay(email_data, account_id)
   └─> 异步执行，不阻塞轮询

6. 更新检查点（Redis）
   └─> 保存当前时间

7. 释放锁
```

**返回值**:
```python
{
    "account_id": 1,
    "emails_found": 10,      # 发现的新邮件数
    "emails_queued": 10,     # 已加入处理队列的邮件数
    "skipped": False         # 是否被跳过（锁定状态）
}
```

---

### 阶段 2: 邮件处理（Celery Worker → process_email）

**触发方式**: `poll_email_account` 任务为每封邮件调用 `process_email.delay()`

**任务**: `process_email(email_data: dict, account_id: int)`

**位置**: `backend/app/tasks/email.py:172-283`

**流程**:

```python
1. 持久化原始邮件
   └─> 调用 persistence_service.persist(email, account_id)
   └─> 保存邮件 .eml 文件和附件到 OSS/本地
   └─> 记录到 email_raw_messages 表
   └─> 失败不阻断流程（可能是重复邮件）

2. 转换为 UnifiedEvent
   └─> 调用 email_adapter.to_unified_event(email)
   └─> 提取邮件字段：发件人、收件人、主题、正文
   └─> 生成唯一 event_id

3. 添加元数据
   └─> email_account_id: 邮箱账户 ID
   └─> email_account_name: 邮箱账户名称
   └─> email_raw_id: 持久化记录 ID

4. 添加到 Redis Streams
   └─> 调用 redis_streams.add_event(event)
   └─> 流名称: events:{event_type}
   └─> 用于事件溯源和审计

5. 分发到 Dispatcher（意图分类 + 启动 Workflow）
   └─> 调用 event_dispatcher.dispatch(event)
   └─> 意图分类：判断邮件类型（询价、订单、投诉等）
   └─> 启动对应的 Temporal Workflow

6. 更新持久化记录状态
   └─> 调用 persistence_service.mark_processed(raw_id, event_id)
   └─> 标记邮件已处理

7. 标记邮件为已读（可选）
   └─> 根据账户配置 account.imap_mark_as_read 决定
   └─> 调用 imap_mark_as_read(message_id, folder, account_id)
```

**返回值**:
```python
{
    "message_id": "msg-123@example.com",
    "raw_record_id": 456,           # 持久化记录 ID
    "event_id": "evt-789",          # UnifiedEvent ID
    "workflow_id": "wf-abc",        # Temporal Workflow ID
    "status": "success"
}
```

---

### 阶段 3: 意图分类与工作流启动（Dispatcher）

**位置**: `backend/app/messaging/dispatcher.py`

**流程**:

```python
1. 意图分类（LLM）
   └─> 调用 intent_classifier_agent
   └─> 分析邮件内容，判断意图
   └─> 返回意图类型：inquiry（询价）、order（订单）、complaint（投诉）等

2. 路由到对应的 Workflow
   └─> 询价邮件 → QuoteWorkflow
   └─> 订单邮件 → OrderWorkflow
   └─> 投诉邮件 → ComplaintWorkflow
   └─> 未知意图 → 人工处理队列

3. 启动 Temporal Workflow
   └─> 调用 temporal_client.start_workflow()
   └─> 传递 event_id 和意图分类结果
   └─> Workflow 异步执行业务逻辑

4. 返回 Workflow ID
   └─> 用于后续查询和跟踪
```

---

## 4. 代码调用链路

### 完整调用链路图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              邮件处理完整调用链                                │
└─────────────────────────────────────────────────────────────────────────────┘

阶段 1: 定时调度 (每 60 秒)
┌──────────────────────────────────────────────────────────────────────────┐
│ Celery Beat                                                              │
│ backend/app/celery_app.py:91-105                                         │
│   ↓                                                                      │
│ setup_periodic_tasks()                                                   │
│   - 由 EmailWorkerService 动态添加任务                                     │
│   - 每个邮箱账户一个独立任务                                               │
│                                                                          │
│ EmailWorkerService.sync_email_tasks()                                    │
│ backend/app/services/email_worker_service.py:41-110                      │
│   ↓                                                                      │
│ celery_app.conf.beat_schedule["poll-email-{account_id}"] = {            │
│     "task": "app.tasks.email.poll_email_account",                       │
│     "schedule": timedelta(seconds=60),                                   │
│     "args": (account_id,)                                                │
│ }                                                                        │
└──────────────────────────────────────────────────────────────────────────┘
                            ↓  (定时触发)

阶段 2: 邮件轮询
┌──────────────────────────────────────────────────────────────────────────┐
│ poll_email_account(account_id: int)                                      │
│ backend/app/tasks/email.py:58-168                                        │
│                                                                          │
│ 步骤 1: 获取分布式锁                                                       │
│   └─> redis_client.set(                                                 │
│          key="email_worker:{account_id}:lock",                           │
│          value=f"celery-{task_id}",                                      │
│          ex=300,  # 5 分钟                                               │
│          nx=True  # 只在不存在时设置                                       │
│       )                                                                  │
│   └─> 如果获取失败 → 返回 {"skipped": True}                               │
│                                                                          │
│ 步骤 2: 获取账户配置                                                       │
│   └─> get_active_imap_accounts()                                        │
│        backend/app/storage/email.py:230-260                              │
│        ├─> 查询数据库 email_accounts 表                                   │
│        ├─> WHERE is_enabled = True                                       │
│        └─> 返回 List[EmailAccountConfig]                                 │
│                                                                          │
│ 步骤 3: 获取检查点                                                         │
│   └─> _get_checkpoint(account_id)                                       │
│        backend/app/tasks/email.py:288-300                                │
│        └─> redis_client.get("email_worker:{account_id}:last_check")     │
│        └─> 默认: datetime.now() - timedelta(days=1)                      │
│                                                                          │
│ 步骤 4: 拉取新邮件                                                         │
│   └─> imap_fetch(                                                       │
│          folder=account.imap_folder,   # "INBOX"                         │
│          limit=50,                     # 每次最多 50 封                   │
│          since=last_check,             # 上次检查时间                     │
│          unseen_only=True,             # 只拉取未读邮件                   │
│          account_id=account_id                                           │
│       )                                                                  │
│        backend/app/storage/email.py:408-520                              │
│        │                                                                 │
│        ├─> 步骤 4.1: 连接 IMAP                                            │
│        │   └─> imap = aioimaplib.IMAP4_SSL(                             │
│        │            host=account.imap_host,                              │
│        │            port=account.imap_port                               │
│        │       )                                                         │
│        │   └─> await imap.login(user, password)                         │
│        │                                                                 │
│        ├─> 步骤 4.2: 选择邮件夹                                            │
│        │   └─> await imap.select(folder)  # "INBOX"                     │
│        │                                                                 │
│        ├─> 步骤 4.3: 构建搜索条件                                          │
│        │   └─> search_criteria = ["UNSEEN"]                             │
│        │   └─> if since: search_criteria.append(f'SINCE {date}')        │
│        │                                                                 │
│        ├─> 步骤 4.4: 搜索邮件                                             │
│        │   └─> response = await imap.search(*search_criteria)           │
│        │   └─> message_ids = response.split()[-limit:]                  │
│        │                                                                 │
│        ├─> 步骤 4.5: 拉取邮件内容                                          │
│        │   └─> for msg_id in message_ids:                               │
│        │          response = await imap.fetch(msg_id, "(RFC822)")       │
│        │          email_message = _parse_email(raw_bytes)               │
│        │                                                                 │
│        └─> 返回 List[EmailMessage]                                       │
│                                                                          │
│ 步骤 5: 将每封邮件加入处理队列                                              │
│   └─> for email in emails:                                              │
│          process_email.delay(                                            │
│              email_data=email.to_dict(),                                 │
│              account_id=account_id                                       │
│          )                                                               │
│       └─> 异步任务，不等待结果                                            │
│                                                                          │
│ 步骤 6: 更新检查点                                                         │
│   └─> _save_checkpoint(account_id)                                      │
│        backend/app/tasks/email.py:303-307                                │
│        └─> redis_client.set(                                            │
│               key="email_worker:{account_id}:last_check",                │
│               value=datetime.now().isoformat(),                          │
│               ex=86400 * 7  # 保存 7 天                                  │
│           )                                                              │
│                                                                          │
│ 步骤 7: 释放锁                                                            │
│   └─> redis_client.delete("email_worker:{account_id}:lock")             │
│                                                                          │
│ 返回值:                                                                  │
│   {                                                                      │
│       "account_id": 1,                                                   │
│       "emails_found": 10,                                                │
│       "emails_queued": 10                                                │
│   }                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
                            ↓ (为每封邮件创建任务)

阶段 3: 邮件处理
┌──────────────────────────────────────────────────────────────────────────┐
│ process_email(email_data: dict, account_id: int)                         │
│ backend/app/tasks/email.py:180-283                                       │
│                                                                          │
│ 步骤 1: 反序列化邮件数据                                                   │
│   └─> email = EmailMessage.from_dict(email_data)                        │
│        backend/app/storage/email.py:116-135                              │
│                                                                          │
│ 步骤 2: 持久化原始邮件和附件                                               │
│   └─> persistence_service.persist(email, account_id)                    │
│        backend/app/storage/email_persistence.py:150-250                  │
│        │                                                                 │
│        ├─> 步骤 2.1: 检查重复                                             │
│        │   └─> 查询数据库: SELECT * FROM email_raw_messages              │
│        │                    WHERE message_id = ?                         │
│        │   └─> 如果已存在 → 抛出异常                                      │
│        │                                                                 │
│        ├─> 步骤 2.2: 上传 .eml 文件                                       │
│        │   └─> eml_path = f"emails/{uuid}/{message_id}.eml"             │
│        │   └─> oss_client.upload(email.raw_bytes, eml_path)             │
│        │        backend/app/storage/oss.py                               │
│        │                                                                 │
│        ├─> 步骤 2.3: 解析并上传附件                                        │
│        │   └─> msg = email.message_from_bytes(email.raw_bytes)          │
│        │   └─> for part in msg.walk():                                  │
│        │          if is_attachment(part):                                │
│        │              att_path = f"emails/{uuid}/attachments/{name}"     │
│        │              oss_client.upload(part.get_payload(), att_path)    │
│        │          if is_signature_image(part):                           │
│        │              # 跳过签名图片                                      │
│        │                                                                 │
│        ├─> 步骤 2.4: 创建数据库记录                                        │
│        │   └─> raw_record = EmailRawMessage(                            │
│        │          id=uuid,                                               │
│        │          account_id=account_id,                                 │
│        │          message_id=email.message_id,                           │
│        │          subject=email.subject,                                 │
│        │          sender=email.sender,                                   │
│        │          recipients=email.recipients,                           │
│        │          eml_path=eml_path,                                     │
│        │          attachments=[...],                                     │
│        │          processed=False                                        │
│        │       )                                                         │
│        │   └─> session.add(raw_record)                                  │
│        │   └─> session.commit()                                         │
│        │                                                                 │
│        └─> 返回 EmailRawMessage 对象                                     │
│                                                                          │
│ 步骤 3: 转换为 UnifiedEvent                                               │
│   └─> email_adapter.to_unified_event(email)                             │
│        backend/app/adapters/email.py:48-110                              │
│        │                                                                 │
│        ├─> 提取邮件内容                                                  │
│        │   └─> content = email.body_text or email.body_html            │
│        │                                                                 │
│        ├─> 提取回复链 ID                                                 │
│        │   └─> thread_id = email.headers.get("in-reply-to")            │
│        │                                                                 │
│        ├─> 构建附件列表                                                  │
│        │   └─> attachments = [                                          │
│        │           Attachment(name, content_type, size)                 │
│        │           for att in email.attachments                          │
│        │       ]                                                         │
│        │                                                                 │
│        └─> 返回 UnifiedEvent(                                            │
│               event_id=uuid4(),                                          │
│               event_type="email",                                        │
│               source="email",                                            │
│               source_id=email.message_id,                                │
│               content=content,                                           │
│               user_external_id=email.sender,                             │
│               thread_id=thread_id,                                       │
│               attachments=attachments,                                   │
│               metadata={                                                 │
│                   "subject": email.subject,                              │
│                   "recipients": email.recipients,                        │
│                   "date": email.date                                     │
│               }                                                          │
│           )                                                              │
│                                                                          │
│ 步骤 4: 添加元数据                                                         │
│   └─> event.metadata["email_account_id"] = account_id                   │
│   └─> event.metadata["email_account_name"] = account.name               │
│   └─> event.metadata["email_raw_id"] = raw_record.id                    │
│                                                                          │
│ 步骤 5: 添加到 Redis Streams                                              │
│   └─> redis_streams.add_event(event)                                    │
│        backend/app/messaging/streams.py:130-170                          │
│        │                                                                 │
│        ├─> 序列化事件                                                    │
│        │   └─> event_data = {                                           │
│        │          "event_id": event.event_id,                           │
│        │          "event_type": event.event_type,                       │
│        │          "content": event.content,                             │
│        │          "metadata": json.dumps(event.metadata)                │
│        │       }                                                         │
│        │                                                                 │
│        ├─> 添加到 Stream                                                 │
│        │   └─> stream_id = await redis_client.xadd(                     │
│        │          name="events:incoming",                                │
│        │          fields=event_data                                      │
│        │       )                                                         │
│        │   └─> stream_id 格式: "1234567890123-0"                        │
│        │                                                                 │
│        └─> 返回 stream_id                                                │
│                                                                          │
│ 步骤 6: 分发到 Dispatcher（意图分类 + 启动 Workflow）                      │
│   └─> event_dispatcher.dispatch(event)                                  │
│        backend/app/messaging/dispatcher.py:66-125                        │
│        │                                                                 │
│        ├─> 步骤 6.1: 幂等性检查                                           │
│        │   └─> _check_idempotency(session, event.idempotency_key)      │
│        │        └─> SELECT * FROM events                                │
│        │             WHERE idempotency_key = 'email:{message_id}'       │
│        │        └─> 如果已存在 → 返回 existing.workflow_id               │
│        │                                                                 │
│        ├─> 步骤 6.2: 保存事件到数据库                                     │
│        │   └─> _save_event(session, event)                              │
│        │        backend/app/messaging/dispatcher.py:146-185              │
│        │        └─> db_event = Event(                                   │
│        │               id=event.event_id,                                │
│        │               idempotency_key=f"email:{message_id}",            │
│        │               event_type="email",                               │
│        │               source="email",                                   │
│        │               content=event.content,                            │
│        │               status=EventStatus.PENDING,                       │
│        │               metadata=event.metadata                           │
│        │           )                                                     │
│        │        └─> session.add(db_event)                               │
│        │                                                                 │
│        ├─> 步骤 6.3: 意图分类                                             │
│        │   └─> _classify_intent(event, session)                         │
│        │        backend/app/messaging/dispatcher.py:187-230              │
│        │        │                                                        │
│        │        ├─> 准备分类上下文                                        │
│        │        │   └─> context = {                                     │
│        │        │          "subject": event.metadata["subject"],         │
│        │        │          "content": event.content,                    │
│        │        │          "sender": event.user_external_id             │
│        │        │       }                                                │
│        │        │                                                        │
│        │        ├─> 调用意图分类 Agent                                    │
│        │        │   └─> agent = agent_registry.get_agent(              │
│        │        │              "intent_classifier"                       │
│        │        │          )                                             │
│        │        │   └─> result = await agent.run(context)               │
│        │        │        backend/app/agents/intent_classifier.py        │
│        │        │        │                                               │
│        │        │        ├─> 加载 Prompt                                 │
│        │        │        │   └─> prompt = await render_prompt(          │
│        │        │        │            "intent_classifier",               │
│        │        │        │            subject=subject,                   │
│        │        │        │            content=content                    │
│        │        │        │        )                                      │
│        │        │        │                                               │
│        │        │        ├─> 调用 LLM                                    │
│        │        │        │   └─> response = await llm_gateway.chat(     │
│        │        │        │            model=DEFAULT_LLM_MODEL,           │
│        │        │        │            messages=[                         │
│        │        │        │                {"role": "user", "content": prompt} │
│        │        │        │            ]                                  │
│        │        │        │        )                                      │
│        │        │        │        backend/app/llm/gateway.py:50-120     │
│        │        │        │        └─> litellm.completion(...)           │
│        │        │        │                                               │
│        │        │        └─> 解析 JSON 结果                              │
│        │        │            └─> {"intent": "inquiry", "confidence": 0.9} │
│        │        │                                                        │
│        │        └─> 返回 intent: "inquiry"                               │
│        │                                                                 │
│        ├─> 步骤 6.4: 启动 Workflow                                        │
│        │   └─> _start_workflow(event, intent)                           │
│        │        backend/app/messaging/dispatcher.py:232-280              │
│        │        │                                                        │
│        │        ├─> 确定 Workflow 类型                                   │
│        │        │   └─> workflow_name = INTENT_WORKFLOW_MAP.get(        │
│        │        │            intent,                                     │
│        │        │            DEFAULT_WORKFLOW                            │
│        │        │       )                                                │
│        │        │   └─> "inquiry" → "EmailProcessWorkflow"              │
│        │        │                                                        │
│        │        ├─> 准备 Workflow 参数                                   │
│        │        │   └─> workflow_input = {                              │
│        │        │          "event_id": event.event_id,                  │
│        │        │          "intent": intent,                            │
│        │        │          "subject": event.metadata["subject"],         │
│        │        │          "content": event.content                     │
│        │        │       }                                                │
│        │        │                                                        │
│        │        ├─> 启动 Temporal Workflow                               │
│        │        │   └─> workflow_id = await start_workflow(             │
│        │        │            workflow_name="EmailProcessWorkflow",       │
│        │        │            workflow_id=f"email-{event.event_id}",     │
│        │        │            workflow_input=workflow_input               │
│        │        │       )                                                │
│        │        │        backend/app/workflows/client.py:30-80          │
│        │        │        │                                               │
│        │        │        ├─> 连接 Temporal                               │
│        │        │        │   └─> client = await Client.connect(         │
│        │        │        │            settings.TEMPORAL_ADDRESS          │
│        │        │        │        )                                      │
│        │        │        │                                               │
│        │        │        ├─> 启动 Workflow                               │
│        │        │        │   └─> handle = await client.start_workflow(  │
│        │        │        │            workflow_class=EmailProcessWorkflow, │
│        │        │        │            id=workflow_id,                    │
│        │        │        │            task_queue="email-processing",     │
│        │        │        │            args=[workflow_input]              │
│        │        │        │        )                                      │
│        │        │        │                                               │
│        │        │        └─> 返回 workflow_id                            │
│        │        │                                                        │
│        │        └─> 返回 workflow_id                                     │
│        │                                                                 │
│        ├─> 步骤 6.5: 更新事件状态                                         │
│        │   └─> db_event.workflow_id = workflow_id                       │
│        │   └─> db_event.mark_processing()                               │
│        │        └─> db_event.status = EventStatus.PROCESSING            │
│        │   └─> session.commit()                                         │
│        │                                                                 │
│        └─> 返回 workflow_id                                              │
│                                                                          │
│ 步骤 7: 更新持久化记录状态                                                 │
│   └─> persistence_service.mark_processed(raw_record.id, event.event_id) │
│        backend/app/storage/email_persistence.py:280-310                  │
│        └─> UPDATE email_raw_messages                                    │
│             SET processed = true, event_id = ?                           │
│             WHERE id = ?                                                 │
│                                                                          │
│ 步骤 8: 标记邮件为已读（可选）                                             │
│   └─> if account.imap_mark_as_read:                                     │
│          imap_mark_as_read(                                              │
│              message_id=email.message_id,                                │
│              folder=account.imap_folder,                                 │
│              account_id=account_id                                       │
│          )                                                               │
│        backend/app/storage/email.py:523-570                              │
│        └─> 连接 IMAP → SELECT folder → STORE message_id +FLAGS \Seen    │
│                                                                          │
│ 返回值:                                                                  │
│   {                                                                      │
│       "message_id": "msg-123@example.com",                               │
│       "raw_record_id": "uuid-456",                                       │
│       "event_id": "uuid-789",                                            │
│       "workflow_id": "email-uuid-789",                                   │
│       "status": "success"                                                │
│   }                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
                            ↓ (Workflow 异步执行)

阶段 4: Workflow 执行（Temporal）
┌──────────────────────────────────────────────────────────────────────────┐
│ EmailProcessWorkflow                                                     │
│ backend/app/workflows/email_process.py                                   │
│                                                                          │
│ 步骤 1: 分析邮件内容                                                       │
│   └─> activity: analyze_email_content(event_id)                         │
│        └─> 调用 email_analyzer Agent                                     │
│        └─> 提取关键信息（客户名、产品、需求等）                            │
│                                                                          │
│ 步骤 2: 生成回复                                                           │
│   └─> activity: generate_email_response(analysis)                       │
│        └─> 根据意图类型选择对应 Agent                                     │
│        └─> inquiry → quote_agent（生成报价）                             │
│        └─> order → order_agent（确认订单）                               │
│        └─> complaint → support_agent（客户支持）                         │
│                                                                          │
│ 步骤 3: 发送回复（可选，需人工审核）                                        │
│   └─> activity: send_email_reply(response)                              │
│        └─> smtp_send(...)                                                │
│                                                                          │
│ 步骤 4: 更新事件状态                                                       │
│   └─> activity: update_event_status(event_id, "completed")              │
│        └─> UPDATE events SET status = 'completed' WHERE id = ?          │
│                                                                          │
│ Workflow 完成                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

### 附录: 关键代码位置汇总

#### 1. Celery 调度

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| Celery 配置 | `backend/app/celery_app.py` | 25-82 |
| 定时任务设置 | `backend/app/celery_app.py` | 91-105 |
| EmailWorkerService | `backend/app/services/email_worker_service.py` | 29-206 |
| 任务同步 | `backend/app/services/email_worker_service.py` | 41-110 |
| 添加任务 | `backend/app/services/email_worker_service.py` | 112-124 |

#### 2. 邮件轮询

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| poll_email_account | `backend/app/tasks/email.py` | 58-168 |
| 分布式锁 | `backend/app/tasks/email.py` | 79-96 |
| 获取账户 | `backend/app/storage/email.py` | 230-260 |
| imap_fetch | `backend/app/storage/email.py` | 408-520 |
| IMAP 连接 | `backend/app/storage/email.py` | 442-453 |
| 邮件搜索 | `backend/app/storage/email.py` | 455-470 |
| 邮件解析 | `backend/app/storage/email.py` | 472-510 |

#### 3. 邮件处理

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| process_email | `backend/app/tasks/email.py` | 180-283 |
| 邮件持久化 | `backend/app/storage/email_persistence.py` | 150-250 |
| 上传 OSS | `backend/app/storage/oss.py` | 50-120 |
| 附件处理 | `backend/app/storage/email_persistence.py` | 180-220 |
| 数据库记录 | `backend/app/storage/email_persistence.py` | 230-250 |

#### 4. 事件转换

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| EmailAdapter | `backend/app/adapters/email.py` | 28-130 |
| to_unified_event | `backend/app/adapters/email.py` | 48-110 |
| 内容提取 | `backend/app/adapters/email.py` | 64-70 |
| 附件转换 | `backend/app/adapters/email.py` | 76-82 |

#### 5. 事件分发

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| EventDispatcher | `backend/app/messaging/dispatcher.py` | 33-280 |
| dispatch | `backend/app/messaging/dispatcher.py` | 66-125 |
| 幂等性检查 | `backend/app/messaging/dispatcher.py` | 127-144 |
| 保存事件 | `backend/app/messaging/dispatcher.py` | 146-185 |
| 意图分类 | `backend/app/messaging/dispatcher.py` | 187-230 |
| 启动 Workflow | `backend/app/messaging/dispatcher.py` | 232-280 |

#### 6. Redis Streams

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| RedisStreams | `backend/app/messaging/streams.py` | 39-300 |
| add_event | `backend/app/messaging/streams.py` | 130-170 |
| read_events | `backend/app/messaging/streams.py` | 172-220 |
| ack_event | `backend/app/messaging/streams.py` | 222-240 |

#### 7. LLM 调用

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| LLMGateway | `backend/app/llm/gateway.py` | 20-200 |
| chat | `backend/app/llm/gateway.py` | 50-120 |
| IntentClassifierAgent | `backend/app/agents/intent_classifier.py` | 20-150 |

#### 8. Temporal Workflow

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| start_workflow | `backend/app/workflows/client.py` | 30-80 |
| EmailProcessWorkflow | `backend/app/workflows/email_process.py` | 30-200 |

---

## 5. EmailSummarizer 工作流

### 5.1 触发方式

EmailSummarizerAgent 有 **3 种触发方式**：

```
┌──────────────────────────────────────────────────────────────────┐
│                      触发入口                                     │
│                                                                  │
│  ① Celery 定时任务              ② API 手动触发                    │
│     poll_email_account             POST /emails/{id}/ai-analyze  │
│     ↓                              ↓                             │
│     process_email                  ai_analyze_email()            │
│     ↓                              ↓                             │
│  EventDispatcher.dispatch()     email_summarizer.analyze()       │
│     ↓                                                            │
│  _classify_intent()            ③ 并行分类（暂未启用）               │
│     ↓                              _classify_parallel()          │
│  agent_registry.run(               ↓                             │
│    "email_summarizer")          asyncio.gather(                  │
│                                    email_summarizer,             │
│                                    work_type_analyzer            │
│                                 )                                │
└──────────────────────────────────────────────────────────────────┘
```

**关键文件**：
- `app/api/emails.py:648` -- API 手动触发入口
- `app/messaging/dispatcher.py:237` -- EventDispatcher 自动触发
- `app/messaging/dispatcher.py:159` -- 并行分类（EmailSummarizer + WorkTypeAnalyzer）

---

### 5.2 完整工作流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EmailSummarizerAgent.analyze()                        │
│                    入口: email_summarizer.py:44                          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  输入参数                                                                │
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  email_id     : str          — 邮件 ID                         │     │
│  │  sender       : str          — 发件人邮箱                       │     │
│  │  sender_name  : Optional[str]— 发件人名称                       │     │
│  │  subject      : str          — 邮件主题                         │     │
│  │  body_text    : str          — 纯文本正文                       │     │
│  │  body_html    : Optional[str]— HTML 正文                        │     │
│  │  received_at  : Optional[dt] — 收件时间                         │     │
│  └────────────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 1: 邮件正文清洗                                                    │
│  clean_email_content()  — email_cleaner.py:332                          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │   body_text / body_html                                           │  │
│  │        │                                                          │  │
│  │        ▼                                                          │  │
│  │   ┌─────────────────┐     参数配置:                                │  │
│  │   │ 优先使用纯文本    │     • max_length = 10000 字符              │  │
│  │   │ HTML 作为备选     │     • remove_signature = False (保留签名)  │  │
│  │   └────────┬────────┘     • remove_quotes = False (保留引用历史)   │  │
│  │            │                                                      │  │
│  │            ▼                                                      │  │
│  │   ┌──────────────────────────────────────────────┐                │  │
│  │   │  处理管道:                                     │                │  │
│  │   │                                               │                │  │
│  │   │  1. HTML → 纯文本 (如果使用 HTML)              │                │  │
│  │   │     ├─ 移除 <style>, <script>, <head>         │                │  │
│  │   │     ├─ 清除所有 HTML 标签                      │                │  │
│  │   │     └─ 解码 HTML 实体 (&nbsp; &lt; 等)         │                │  │
│  │   │                                               │                │  │
│  │   │  2. 签名移除 (当前关闭)                        │                │  │
│  │   │     ├─ 检测 "Best regards" / "此致" 等         │                │  │
│  │   │     └─ 检测 "Sent from my iPhone" 等          │                │  │
│  │   │                                               │                │  │
│  │   │  3. 引用移除 (当前关闭)                        │                │  │
│  │   │     ├─ 检测 "On ... wrote:" 等                │                │  │
│  │   │     └─ 检测 ">" 引用行                        │                │  │
│  │   │                                               │                │  │
│  │   │  4. 规范化空白                                 │                │  │
│  │   │     ├─ 多个空行 → 单个空行                     │                │  │
│  │   │     └─ 移除行尾空白                            │                │  │
│  │   │                                               │                │  │
│  │   │  5. 截断 (>10000 字符时)                       │                │  │
│  │   │     ├─ 优先在句号处截断                         │                │  │
│  │   │     └─ 其次在换行处截断                         │                │  │
│  │   └───────────────────────────────────────────────┘                │  │
│  │            │                                                      │  │
│  │            ▼                                                      │  │
│  │     cleaned_content (清洗后的文本)                                 │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  如果 cleaned_content 为空 → 返回 _empty_result("邮件正文为空")          │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ 正文不为空
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 2: 加载 System Prompt                                             │
│  get_prompt("email_summarizer_system")  — prompts/manager.py            │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │   加载优先级:                                                      │  │
│  │                                                                   │  │
│  │   ① 数据库 (system_prompts 表)                                    │  │
│  │      ↓ 未找到                                                     │  │
│  │   ② defaults.py 内置模板                                          │  │
│  │      ↓ 未找到                                                     │  │
│  │   ③ 硬编码回退:                                                    │  │
│  │      "You are a professional foreign trade                        │  │
│  │       email analysis assistant..."                                │  │
│  │                                                                   │  │
│  │   System Prompt 内容 (defaults.py):                               │  │
│  │   ┌─────────────────────────────────────────────────────────┐     │  │
│  │   │  角色: 外贸邮件分析助手                                    │     │  │
│  │   │  输出: 严格 JSON 格式                                     │     │  │
│  │   │  要求: 填充所有字段，无法识别用 null 或 []                  │     │  │
│  │   └─────────────────────────────────────────────────────────┘     │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 3: 构建 User Prompt (变量渲染)                                    │
│  render_prompt("email_summarizer", **vars)  — prompts/manager.py        │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │   模板变量:                                                        │  │
│  │   ┌─────────────────────────────────────────────────────────┐     │  │
│  │   │  {{sender}}       ← sender (发件人邮箱)                  │     │  │
│  │   │  {{sender_name}}  ← sender_name (发件人名称)             │     │  │
│  │   │  {{subject}}      ← subject (邮件主题)                   │     │  │
│  │   │  {{received_at}}  ← received_at (收件时间, 格式化)       │     │  │
│  │   │  {{content}}      ← cleaned_content (清洗后正文)         │     │  │
│  │   └─────────────────────────────────────────────────────────┘     │  │
│  │                                                                   │  │
│  │   渲染后输出: 包含邮件元信息 + 正文的完整分析请求                    │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  如果 prompt 为空 → 返回 _empty_result("Prompt loading failed")         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ prompt 加载成功
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 4: 调用 LLM                                                       │
│  self.llm.chat()  — llm/gateway.py                                      │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │   ┌──────────────────────┐                                        │  │
│  │   │    LLMGateway.chat() │                                        │  │
│  │   └──────────┬───────────┘                                        │  │
│  │              │                                                    │  │
│  │              ▼                                                    │  │
│  │   ┌──────────────────────┐                                        │  │
│  │   │  模型选择优先级:       │                                        │  │
│  │   │  ① Agent.model 属性   │                                        │  │
│  │   │  ② 环境变量            │                                        │  │
│  │   │    DEFAULT_LLM_MODEL  │                                        │  │
│  │   │  ③ config.py 默认值   │                                        │  │
│  │   └──────────┬───────────┘                                        │  │
│  │              │                                                    │  │
│  │              ▼                                                    │  │
│  │   ┌──────────────────────┐        ┌───────────────────────┐       │  │
│  │   │      LiteLLM         │───────▶│  LLM Provider API     │       │  │
│  │   │  (统一多模型网关)      │◀───────│  Claude/GPT/Gemini... │       │  │
│  │   └──────────┬───────────┘        └───────────────────────┘       │  │
│  │              │                                                    │  │
│  │              ▼                                                    │  │
│  │   ┌──────────────────────┐                                        │  │
│  │   │    LLMResponse       │                                        │  │
│  │   │  • content (文本)     │                                        │  │
│  │   │  • model (模型名)     │                                        │  │
│  │   │  • usage (token 统计) │                                        │  │
│  │   │  • finish_reason     │                                        │  │
│  │   └──────────────────────┘                                        │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  如果调用异常 → 返回 _empty_result(error_message)                        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │ LLM 返回成功
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 5: 解析 LLM 返回                                                  │
│  _parse_response(content)  — email_summarizer.py:134                    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │   LLM 原始返回文本                                                 │  │
│  │        │                                                          │  │
│  │        ▼                                                          │  │
│  │   尝试 1: json.loads(content)                                     │  │
│  │        │                                                          │  │
│  │        ├── 成功 → 返回 dict                                       │  │
│  │        │                                                          │  │
│  │        ▼ JSONDecodeError                                          │  │
│  │   尝试 2: 从 ```json ... ``` 代码块提取                            │  │
│  │        │   正则: ```(?:json)?\s*(\{.*?\})\s*```                   │  │
│  │        │                                                          │  │
│  │        ├── 成功 → 返回 dict                                       │  │
│  │        │                                                          │  │
│  │        ▼ 未匹配或解析失败                                          │  │
│  │   尝试 3: 查找第一个 { 到最后一个 }                                 │  │
│  │        │   content[start:end]                                     │  │
│  │        │                                                          │  │
│  │        ├── 成功 → 返回 dict                                       │  │
│  │        │                                                          │  │
│  │        ▼ 仍然失败                                                  │  │
│  │   返回 {"parse_error": True, "raw_response": content[:500]}       │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step 6: 组装返回结果                                                    │
│  email_summarizer.py:122-128                                            │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                                                                   │  │
│  │   解析后的 result dict                                             │  │
│  │        │                                                          │  │
│  │        ▼  追加元数据:                                              │  │
│  │   ┌───────────────────────────────────────────────────────┐       │  │
│  │   │  result["email_id"]        = email_id                 │       │  │
│  │   │  result["cleaned_content"] = cleaned_content          │       │  │
│  │   │  result["llm_model"]       = model                    │       │  │
│  │   │  result["token_used"]      = response.usage.total     │       │  │
│  │   └───────────────────────────────────────────────────────┘       │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  输出结果 (写入 email_analyses 表)                                       │
│                                                                         │
│  ┌─── 摘要与翻译 ───┐  ┌─── 发件方信息 ───┐  ┌─── 意图分类 ─────────┐  │
│  │ summary          │  │ sender_type      │  │ intent              │  │
│  │ key_points[]     │  │ sender_company   │  │ intent_confidence   │  │
│  │ original_language│  │ sender_country   │  │ urgency             │  │
│  └──────────────────┘  │ is_new_contact   │  │ sentiment           │  │
│                        └──────────────────┘  └─────────────────────┘  │
│                                                                         │
│  ┌─── 业务信息 ──────────────────┐  ┌─── 跟进建议 ──────────────────┐  │
│  │ products[{name,specs,qty,    │  │ questions[]                    │  │
│  │   unit,target_price}]        │  │ action_required[]              │  │
│  │ amounts[{value,currency,     │  │ suggested_reply                │  │
│  │   context}]                  │  │ priority (p0/p1/p2/p3)         │  │
│  │ trade_terms{incoterm,        │  └────────────────────────────────┘  │
│  │   payment_terms,destination} │                                      │
│  │ deadline                     │  ┌─── 分析元数据 ──────────────────┐  │
│  └──────────────────────────────┘  │ cleaned_content                │  │
│                                     │ llm_model                      │  │
│                                     │ token_used                     │  │
│                                     └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 5.3 简化流程图

```
  邮件原始数据
       │
       ▼
  ┌─────────────┐
  │ 1. 正文清洗   │  clean_email_content()
  │  HTML→文本    │  保留签名和引用历史
  │  规范化空白    │  截断到 10000 字符
  └──────┬──────┘
         │
         ▼ 正文为空? ──── Yes ──▶ 返回空结果
         │ No
         ▼
  ┌─────────────┐
  │ 2. 加载Prompt│  DB → defaults.py → 硬编码回退
  │  System      │  email_summarizer_system
  │  User        │  email_summarizer + 变量渲染
  └──────┬──────┘
         │
         ▼ Prompt 为空? ── Yes ──▶ 返回空结果
         │ No
         ▼
  ┌─────────────┐
  │ 3. 调用 LLM  │  LiteLLM → Claude/GPT/Gemini...
  │  chat()      │  非工具调用模式
  └──────┬──────┘
         │
         ▼ 异常? ────── Yes ──▶ 返回空结果
         │ No
         ▼
  ┌─────────────┐
  │ 4. 解析 JSON │  3 级回退策略:
  │              │  直接解析 → 代码块提取 → 花括号匹配
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 5. 追加元数据 │  email_id, cleaned_content,
  │              │  llm_model, token_used
  └──────┬──────┘
         │
         ▼
  ┌─────────────┐
  │ 6. 持久化     │  写入 email_analyses 表
  │  返回结果     │  (由调用方负责)
  └─────────────┘
```

---

### 5.4 错误处理流程

```
  任意步骤失败
       │
       ▼
  _empty_result(email_id, error)
       │
       ▼
  ┌──────────────────────────────────┐
  │  {                               │
  │    "email_id": email_id,         │
  │    "summary": "分析失败: {error}",│
  │    "key_points": [],             │
  │    "intent": "other",            │
  │    "intent_confidence": 0,       │
  │    "urgency": "low",             │
  │    "sentiment": "neutral",       │
  │    "priority": "p3",             │
  │    "error": error                │
  │  }                               │
  └──────────────────────────────────┘
```

---

### 5.5 与其他组件的交互关系

```
                          ┌──────────────────┐
                          │   Celery Worker   │
                          │ (email 队列)       │
                          └────────┬─────────┘
                                   │ poll → dispatch
                                   ▼
┌──────────┐           ┌──────────────────────┐           ┌──────────┐
│ API 端点  │──────────▶│  EmailSummarizer     │──────────▶│ 数据库    │
│ /emails/ │           │  Agent               │           │ email_   │
│ {id}/    │           │                      │           │ analyses │
│ ai-      │           │  ┌────────────────┐  │           └──────────┘
│ analyze  │           │  │ EmailCleaner   │  │
└──────────┘           │  │ Tool           │  │
                       │  └────────────────┘  │
                       │                      │
                       │  ┌────────────────┐  │           ┌──────────┐
                       │  │ PromptManager  │◀─┼───────────│ system_  │
                       │  │ (缓存 5 分钟)   │  │           │ prompts  │
                       │  └────────────────┘  │           │ 表       │
                       │                      │           └──────────┘
                       │  ┌────────────────┐  │
                       │  │ LLMGateway     │  │           ┌──────────┐
                       │  │ (LiteLLM)      │──┼──────────▶│ LLM API  │
                       │  └────────────────┘  │           │ Provider │
                       └──────────────────────┘           └──────────┘
```

---

### 5.6 关键代码位置

| 步骤 | 方法 | 文件:行号 |
|------|------|----------|
| 入口 | `analyze()` | `app/agents/email_summarizer.py:44` |
| 正文清洗 | `clean_email_content()` | `app/tools/email_cleaner.py:332` |
| HTML 清洗 | `clean_html()` | `app/tools/email_cleaner.py:73` |
| 签名移除 | `remove_signature()` | `app/tools/email_cleaner.py:98` |
| 引用移除 | `remove_quoted_content()` | `app/tools/email_cleaner.py:129` |
| 内容截断 | `truncate_content()` | `app/tools/email_cleaner.py:195` |
| 加载 Prompt | `get_prompt()` | `app/llm/prompts/manager.py` |
| 渲染 Prompt | `render_prompt()` | `app/llm/prompts/manager.py` |
| 默认 Prompt | `DEFAULT_PROMPTS["email_summarizer"]` | `app/llm/prompts/defaults.py:74` |
| LLM 调用 | `llm.chat()` | `app/llm/gateway.py` |
| 模型选择 | `_get_model()` | `app/agents/base.py:100` |
| JSON 解析 | `_parse_response()` | `app/agents/email_summarizer.py:134` |
| 空结果 | `_empty_result()` | `app/agents/email_summarizer.py:172` |
| 兼容接口 | `run()` | `app/agents/email_summarizer.py:190` |
| API 触发 | `ai_analyze_email()` | `app/api/emails.py:648` |
| 自动触发 | `_classify_intent()` | `app/messaging/dispatcher.py:237` |
| 结果存储 | `EmailAnalysis` 模型 | `app/models/email_analysis.py:20` |

---

## 6. 数据流向与数据结构

### 6.1 数据流向

#### IMAP → EmailMessage

```python
# backend/app/storage/email.py:408-520
raw_bytes (RFC822) → email.message_from_bytes() → EmailMessage(
    message_id="<msg-123@example.com>",
    subject="询价: 产品 A",
    sender="customer@example.com",
    body_text="请问产品A的价格是多少？",
    attachments=[{"filename": "spec.pdf", ...}],
    raw_bytes=b"From: ..."
)
```

#### EmailMessage → UnifiedEvent

```python
# backend/app/adapters/email.py:48-110
EmailMessage → UnifiedEvent(
    event_id="uuid-789",
    event_type="email",
    source="email",
    source_id="<msg-123@example.com>",
    content="请问产品A的价格是多少？",
    user_external_id="customer@example.com",
    metadata={
        "subject": "询价: 产品 A",
        "recipients": ["sales@company.com"],
        "date": "2026-02-01T12:00:00Z"
    }
)
```

#### UnifiedEvent → Event (数据库)

```python
# backend/app/messaging/dispatcher.py:146-185
UnifiedEvent → Event(
    id="uuid-789",
    idempotency_key="email:<msg-123@example.com>",
    event_type="email",
    source="email",
    content="请问产品A的价格是多少？",
    status=EventStatus.PENDING,
    metadata={...}
)
```

#### Event → Workflow Input

```python
# backend/app/messaging/dispatcher.py:232-280
Event → workflow_input = {
    "event_id": "uuid-789",
    "intent": "inquiry",
    "subject": "询价: 产品 A",
    "content": "请问产品A的价格是多少？"
}
```

---

### 6.2 Redis 数据结构

#### 分布式锁

```
键: email_worker:{account_id}:lock
值: celery-{task_id}
过期时间: 300 秒（5 分钟）
作用: 防止多个 Worker 实例重复处理同一个邮箱
```

#### 检查点

```
键: email_worker:{account_id}:last_check
值: 2026-02-01T12:00:00
过期时间: 604800 秒（7 天）
作用: 记录上次检查邮箱的时间，避免重复拉取
```

#### Redis Streams

```
Stream: events:incoming
格式: {
    "event_id": "uuid-789",
    "event_type": "email",
    "content": "...",
    "metadata": "{...}"  # JSON 字符串
}
ID: 1234567890123-0
作用: 事件流，用于事件溯源和审计
```

---

### 6.3 数据库表

#### email_accounts（邮箱账户）

```sql
CREATE TABLE email_accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    imap_host VARCHAR(255),
    imap_port INTEGER DEFAULT 993,
    imap_user VARCHAR(255),
    imap_password VARCHAR(255),
    imap_folder VARCHAR(100) DEFAULT 'INBOX',
    imap_mark_as_read BOOLEAN DEFAULT FALSE,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### email_raw_messages（原始邮件记录）

```sql
CREATE TABLE email_raw_messages (
    id UUID PRIMARY KEY,
    account_id INTEGER REFERENCES email_accounts(id),
    message_id VARCHAR(255) UNIQUE NOT NULL,
    subject TEXT,
    sender VARCHAR(255),
    recipients JSONB,
    received_at TIMESTAMP,
    eml_path VARCHAR(500),
    attachments JSONB,
    processed BOOLEAN DEFAULT FALSE,
    event_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### events（统一事件）

```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE,
    event_type VARCHAR(50),
    source VARCHAR(50),
    source_id VARCHAR(255),
    content TEXT,
    content_type VARCHAR(50),
    user_id INTEGER,
    user_external_id VARCHAR(255),
    session_id UUID,
    thread_id VARCHAR(255),
    intent VARCHAR(50),
    workflow_id VARCHAR(255),
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 6.4 错误处理

#### Celery 任务重试

```python
# backend/app/tasks/email.py:50-57
@celery_app.task(
    max_retries=3,                # 最多重试 3 次
    default_retry_delay=60,       # 失败后 60 秒重试
)
async def poll_email_account(self, account_id: int):
    try:
        # ... 业务逻辑
    except Exception as exc:
        # 自动重试
        raise self.retry(exc=exc)
```

#### 幂等性保证

```python
# backend/app/messaging/dispatcher.py:84-92
# 1. 检查幂等键
if event.idempotency_key:
    existing = await self._check_idempotency(
        session, event.idempotency_key
    )
    if existing:
        logger.info(f"事件已处理，跳过: {event.idempotency_key}")
        return existing.workflow_id  # 返回已有的 workflow_id
```

#### 持久化失败不阻断流程

```python
# backend/app/tasks/email.py:223-230
try:
    raw_record = await persistence_service.persist(email, account_id)
    logger.info(f"已持久化: {raw_record.id}")
except Exception as e:
    logger.error(f"持久化失败: {e}")
    # 持久化失败不阻断流程（可能是重复邮件）
    # 继续后续处理
```

---

## 7. 监控与调试

### 7.1 查看 Celery 任务状态

使用 Flower（Celery 监控面板）：

```bash
cd backend
source venv/bin/activate
celery -A app.celery_app flower --port=5555
```

访问: http://localhost:5555

**功能**:
- 查看任务执行历史
- 查看任务失败原因
- 查看 Worker 负载
- 手动重试失败任务

---

### 7.2 查看日志

**Celery Beat 日志**:
```bash
# 如果使用 nohup 启动
tail -f logs/celery-beat.log

# 如果前台运行
# 直接查看控制台输出
```

**Celery Worker 日志**:
```bash
# 如果使用 nohup 启动
tail -f logs/celery-worker.log

# 如果前台运行
# 直接查看控制台输出
```

**关键日志标签**:
- `[Celery:PollEmail]`: 邮件轮询任务
- `[Celery:ProcessEmail]`: 邮件处理任务

---

### 7.3 查看 Redis 数据

**检查点（上次检查时间）**:
```bash
redis-cli GET "email_worker:1:last_check"
# 返回: 2026-02-01T12:00:00
```

**分布式锁**:
```bash
redis-cli GET "email_worker:1:lock"
# 返回: celery-task-id 或 (nil)
```

**任务队列长度**:
```bash
redis-cli LLEN "celery"
# 返回: 待处理任务数
```

---

### 7.4 查看数据库

**查询待处理邮件**:
```sql
SELECT id, subject, sender, received_at
FROM email_raw_messages
WHERE processed = false
ORDER BY received_at DESC
LIMIT 10;
```

**查询账户统计**:
```sql
SELECT
    a.name,
    COUNT(e.id) as total_emails,
    SUM(CASE WHEN e.processed THEN 1 ELSE 0 END) as processed,
    SUM(CASE WHEN NOT e.processed THEN 1 ELSE 0 END) as pending
FROM email_accounts a
LEFT JOIN email_raw_messages e ON e.account_id = a.id
WHERE a.is_enabled = true
GROUP BY a.id, a.name;
```

---

## 8. 性能与优化

### 8.1 当前配置

- **邮箱数量**: 100 个
- **轮询间隔**: 60 秒
- **每次拉取**: 最多 50 封邮件
- **Worker 并发**: 10（可调整）
- **处理时间**: 约 8 分钟（全部 100 个邮箱）

### 8.2 性能对比

| 指标 | 旧架构（APScheduler） | 新架构（Celery） |
|-----|---------------------|-----------------|
| 100 个邮箱处理时间 | 50 分钟 | 8 分钟 |
| 并发能力 | 单进程 | 多进程/多实例 |
| 任务隔离 | 无 | 独立任务队列 |
| 自动重试 | 手动实现 | 内置支持 |
| 水平扩展 | 不支持 | 支持 |

### 8.3 优化建议

1. **增加 Worker 数量**（水平扩展）
   ```bash
   # 启动第 2 个 Worker
   celery -A app.celery_app worker --loglevel=info --concurrency=10

   # 启动第 3 个 Worker
   celery -A app.celery_app worker --loglevel=info --concurrency=10
   ```

2. **调整并发数**（垂直扩展）
   ```bash
   # 每个 Worker 并发 20 个任务
   celery -A app.celery_app worker --concurrency=20
   ```

3. **调整轮询间隔**
   ```python
   # 紧急邮箱：30 秒
   await email_worker_service.add_account_task(account_id=1, interval=30)

   # 普通邮箱：60 秒
   await email_worker_service.add_account_task(account_id=2, interval=60)

   # 低优先级：300 秒
   await email_worker_service.add_account_task(account_id=3, interval=300)
   ```

4. **调整拉取数量**
   ```python
   # 修改 backend/app/tasks/email.py:119
   limit=50  # 改为 100（高流量邮箱）
   ```

### 8.4 性能监控点

#### 邮件拉取性能

```python
# 监控指标
- 平均拉取时间: poll_email_account 任务执行时间
- 拉取失败率: 任务失败次数 / 总任务数
- 锁冲突率: 获取锁失败次数 / 总任务数
```

#### 邮件处理性能

```python
# 监控指标
- 平均处理时间: process_email 任务执行时间
- 处理失败率: 任务失败次数 / 总任务数
- 意图分类准确率: 需人工标注验证
```

#### Workflow 性能

```python
# 监控指标
- Workflow 启动成功率
- Workflow 平均执行时间
- Workflow 失败率
```

---

## 9. 故障排查

### 问题 1: 邮件没有被拉取

**可能原因**:
1. Celery Beat 未运行
2. 邮箱账户未启用
3. IMAP 连接失败
4. 分布式锁未释放

**排查步骤**:
```bash
# 1. 检查 Celery Beat 进程
ps aux | grep "celery.*beat"

# 2. 检查邮箱账户配置
curl -X GET http://localhost:8000/admin/email-accounts \
  -H "Authorization: Bearer $TOKEN"

# 3. 测试 IMAP 连接
curl -X POST http://localhost:8000/admin/email-accounts/1/test \
  -H "Authorization: Bearer $TOKEN"

# 4. 清除分布式锁
redis-cli DEL "email_worker:1:lock"
```

---

### 问题 2: 邮件处理失败

**可能原因**:
1. Celery Worker 未运行
2. 任务队列积压
3. 数据库连接失败
4. LLM API 调用失败

**排查步骤**:
```bash
# 1. 检查 Celery Worker 进程
ps aux | grep "celery.*worker"

# 2. 查看任务队列
redis-cli LLEN "celery"

# 3. 查看失败任务
# 访问 Flower: http://localhost:5555
# 查看 "Failures" 标签页

# 4. 手动重试失败任务
# 在 Flower 中点击 "Retry"
```

---

### 问题 3: 重复处理邮件

**可能原因**:
1. 检查点未保存
2. 分布式锁失效
3. 多个 Worker 实例冲突

**排查步骤**:
```bash
# 1. 检查检查点
redis-cli GET "email_worker:1:last_check"

# 2. 检查锁状态
redis-cli GET "email_worker:1:lock"

# 3. 检查是否有多个 Worker 实例
ps aux | grep "email_worker"

# 4. 清理旧进程
pkill -f "email_worker"
```

---

## 10. API 接口

### 10.1 同步邮件任务

**端点**: `POST /admin/workers/sync-email-tasks`

**请求**:
```json
{
  "interval": 60  // 轮询间隔（秒），可选
}
```

**响应**:
```json
{
  "added": 5,      // 新增任务数
  "removed": 2,    // 删除任务数
  "updated": 10,   // 更新任务数
  "total": 15      // 总任务数
}
```

---

### 10.2 手动触发邮件拉取

**端点**: `POST /admin/email-accounts/{account_id}/poll`

**响应**:
```json
{
  "account_id": 1,
  "emails_found": 10,
  "emails_queued": 10,
  "skipped": false
}
```

---

### 10.3 查看邮件列表

**端点**: `GET /admin/emails`

**参数**:
- `account_id`: 邮箱账户 ID（可选）
- `processed`: 是否已处理（true/false，可选）
- `limit`: 返回数量（默认 20）
- `offset`: 偏移量（默认 0）

**响应**:
```json
{
  "total": 100,
  "items": [
    {
      "id": "uuid-123",
      "account_id": 1,
      "subject": "询价: 产品 A",
      "sender": "customer@example.com",
      "received_at": "2026-02-01T12:00:00Z",
      "processed": true,
      "event_id": "evt-456"
    }
  ]
}
```

---

### 10.4 配置参考

#### Celery 配置（app/celery_app.py）

```python
# 任务队列配置
task_queues=(
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("email", Exchange("email"), routing_key="email"),  # 邮件专用队列
    Queue("workflow", Exchange("workflow"), routing_key="workflow"),
)

# 任务路由
task_routes={
    "app.tasks.email.*": {"queue": "email"},
}

# 任务执行配置
task_acks_late=True                    # 任务执行完才确认
task_reject_on_worker_lost=True        # Worker 丢失时重新排队
worker_prefetch_multiplier=1           # 每次只取 1 个任务（公平分发）
worker_max_tasks_per_child=1000        # Worker 进程处理 1000 个任务后重启

# 任务限流
task_annotations={
    "*": {"rate_limit": "100/s"},      # 每秒最多 100 个任务
}
```

---

## 相关文档

- [开发手册](../guides/BACKEND_HANDBOOK.md) - 后端开发手册
- [LLM 手册](../guides/LLM_GUIDE.md) - LLM 服务手册
- [Celery 指南](../guides/CELERY_GUIDE.md) - Celery 使用指南

---

*文档合并时间: 2026-02-10*
*原始文档: EMAIL_PROCESSING_FLOW.md (2026-02-01) + EMAIL_CODE_PATH.md (2026-02-01) + EMAIL_SUMMARIZER_WORKFLOW.md (2026-02-07)*
