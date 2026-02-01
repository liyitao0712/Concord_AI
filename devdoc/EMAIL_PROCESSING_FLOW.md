# 邮件处理流程

> 更新时间: 2026-02-01
> 架构: Celery + Redis + Temporal

---

## 架构概览

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

## 核心组件

### 1. Celery Beat（定时调度器）

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

### 2. Celery Worker（任务执行器）

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

### 3. EmailWorkerService（任务管理服务）

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

## 处理流程详解

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

## 数据库表

### email_accounts（邮箱账户配置）

存储 IMAP 账户信息和配置。

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | int | 账户 ID |
| name | varchar | 账户名称（如 "客服邮箱"） |
| imap_host | varchar | IMAP 服务器地址 |
| imap_port | int | IMAP 端口（通常 993） |
| imap_user | varchar | IMAP 用户名 |
| imap_password | varchar | IMAP 密码（加密存储） |
| imap_folder | varchar | 监听的文件夹（默认 INBOX） |
| imap_mark_as_read | bool | 处理后是否标记已读 |
| is_enabled | bool | 是否启用 |

### email_raw_messages（原始邮件记录）

存储邮件的元数据和文件路径。

| 字段 | 类型 | 说明 |
|-----|------|------|
| id | uuid | 记录 ID |
| account_id | int | 邮箱账户 ID |
| message_id | varchar | 邮件 Message-ID（唯一标识） |
| subject | text | 邮件主题 |
| sender | varchar | 发件人 |
| recipients | json | 收件人列表 |
| received_at | datetime | 接收时间 |
| eml_path | varchar | .eml 文件路径 |
| attachments | json | 附件列表 |
| processed | bool | 是否已处理 |
| event_id | varchar | 关联的 UnifiedEvent ID |

---

## 监控与调试

### 1. 查看 Celery 任务状态

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

### 2. 查看日志

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

### 3. 查看 Redis 数据

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

### 4. 查看数据库

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

## 性能优化

### 当前配置

- **邮箱数量**: 100 个
- **轮询间隔**: 60 秒
- **每次拉取**: 最多 50 封邮件
- **Worker 并发**: 10（可调整）
- **处理时间**: 约 8 分钟（全部 100 个邮箱）

### 性能对比

| 指标 | 旧架构（APScheduler） | 新架构（Celery） |
|-----|---------------------|-----------------|
| 100 个邮箱处理时间 | 50 分钟 | 8 分钟 |
| 并发能力 | 单进程 | 多进程/多实例 |
| 任务隔离 | 无 | 独立任务队列 |
| 自动重试 | 手动实现 | 内置支持 |
| 水平扩展 | 不支持 | 支持 |

### 优化建议

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

---

## 故障排查

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

## API 接口

### 1. 同步邮件任务

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

### 2. 手动触发邮件拉取

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

### 3. 查看邮件列表

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

## 配置参考

### Celery 配置（app/celery_app.py）

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

- [MANUAL.md](MANUAL.md) - 项目手册
- [CELERY_MIGRATION.md](CELERY_MIGRATION.md) - Celery 迁移说明（如果存在）
- [LLM_MANUAL.md](LLM_MANUAL.md) - LLM 服务手册

---

*文档创建时间: 2026-02-01*
*作者: Claude Code*
