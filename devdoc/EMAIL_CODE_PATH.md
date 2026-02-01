# 邮件处理代码路径详解

> 更新时间: 2026-02-01
> 从实际代码调用层面跟踪完整流程

---

## 完整调用链路图

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

---

## 关键代码位置汇总

### 1. Celery 调度

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| Celery 配置 | `backend/app/celery_app.py` | 25-82 |
| 定时任务设置 | `backend/app/celery_app.py` | 91-105 |
| EmailWorkerService | `backend/app/services/email_worker_service.py` | 29-206 |
| 任务同步 | `backend/app/services/email_worker_service.py` | 41-110 |
| 添加任务 | `backend/app/services/email_worker_service.py` | 112-124 |

### 2. 邮件轮询

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| poll_email_account | `backend/app/tasks/email.py` | 58-168 |
| 分布式锁 | `backend/app/tasks/email.py` | 79-96 |
| 获取账户 | `backend/app/storage/email.py` | 230-260 |
| imap_fetch | `backend/app/storage/email.py` | 408-520 |
| IMAP 连接 | `backend/app/storage/email.py` | 442-453 |
| 邮件搜索 | `backend/app/storage/email.py` | 455-470 |
| 邮件解析 | `backend/app/storage/email.py` | 472-510 |

### 3. 邮件处理

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| process_email | `backend/app/tasks/email.py` | 180-283 |
| 邮件持久化 | `backend/app/storage/email_persistence.py` | 150-250 |
| 上传 OSS | `backend/app/storage/oss.py` | 50-120 |
| 附件处理 | `backend/app/storage/email_persistence.py` | 180-220 |
| 数据库记录 | `backend/app/storage/email_persistence.py` | 230-250 |

### 4. 事件转换

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| EmailAdapter | `backend/app/adapters/email.py` | 28-130 |
| to_unified_event | `backend/app/adapters/email.py` | 48-110 |
| 内容提取 | `backend/app/adapters/email.py` | 64-70 |
| 附件转换 | `backend/app/adapters/email.py` | 76-82 |

### 5. 事件分发

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| EventDispatcher | `backend/app/messaging/dispatcher.py` | 33-280 |
| dispatch | `backend/app/messaging/dispatcher.py` | 66-125 |
| 幂等性检查 | `backend/app/messaging/dispatcher.py` | 127-144 |
| 保存事件 | `backend/app/messaging/dispatcher.py` | 146-185 |
| 意图分类 | `backend/app/messaging/dispatcher.py` | 187-230 |
| 启动 Workflow | `backend/app/messaging/dispatcher.py` | 232-280 |

### 6. Redis Streams

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| RedisStreams | `backend/app/messaging/streams.py` | 39-300 |
| add_event | `backend/app/messaging/streams.py` | 130-170 |
| read_events | `backend/app/messaging/streams.py` | 172-220 |
| ack_event | `backend/app/messaging/streams.py` | 222-240 |

### 7. LLM 调用

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| LLMGateway | `backend/app/llm/gateway.py` | 20-200 |
| chat | `backend/app/llm/gateway.py` | 50-120 |
| IntentClassifierAgent | `backend/app/agents/intent_classifier.py` | 20-150 |

### 8. Temporal Workflow

| 组件 | 文件路径 | 行号 |
|-----|---------|------|
| start_workflow | `backend/app/workflows/client.py` | 30-80 |
| EmailProcessWorkflow | `backend/app/workflows/email_process.py` | 30-200 |

---

## 数据流向

### 1. IMAP → EmailMessage

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

### 2. EmailMessage → UnifiedEvent

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

### 3. UnifiedEvent → Event (数据库)

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

### 4. Event → Workflow Input

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

## Redis 数据结构

### 1. 分布式锁

```
键: email_worker:{account_id}:lock
值: celery-{task_id}
过期时间: 300 秒（5 分钟）
作用: 防止多个 Worker 实例重复处理同一个邮箱
```

### 2. 检查点

```
键: email_worker:{account_id}:last_check
值: 2026-02-01T12:00:00
过期时间: 604800 秒（7 天）
作用: 记录上次检查邮箱的时间，避免重复拉取
```

### 3. Redis Streams

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

## 数据库表

### 1. email_accounts（邮箱账户）

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

### 2. email_raw_messages（原始邮件记录）

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

### 3. events（统一事件）

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

## 错误处理

### 1. Celery 任务重试

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

### 2. 幂等性保证

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

### 3. 持久化失败不阻断流程

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

## 性能监控点

### 1. 邮件拉取性能

```python
# 监控指标
- 平均拉取时间: poll_email_account 任务执行时间
- 拉取失败率: 任务失败次数 / 总任务数
- 锁冲突率: 获取锁失败次数 / 总任务数
```

### 2. 邮件处理性能

```python
# 监控指标
- 平均处理时间: process_email 任务执行时间
- 处理失败率: 任务失败次数 / 总任务数
- 意图分类准确率: 需人工标注验证
```

### 3. Workflow 性能

```python
# 监控指标
- Workflow 启动成功率
- Workflow 平均执行时间
- Workflow 失败率
```

---

*文档创建时间: 2026-02-01*
*作者: Claude Code*
