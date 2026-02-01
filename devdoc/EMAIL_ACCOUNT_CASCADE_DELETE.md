# 邮箱账户级联删除说明

> 更新时间: 2026-02-01

---

## 功能概述

删除邮箱账户时，自动级联删除所有关联数据，确保数据一致性。

### 删除范围

1. **PostgreSQL 数据库记录**
   - ✅ `email_accounts` - 邮箱账户
   - ✅ `email_raw_messages` - 该账户的所有邮件
   - ✅ `email_analyses` - 所有邮件的分析结果（显式删除）
   - ✅ `email_attachments` - 所有邮件的附件记录

2. **OSS/本地存储文件**
   - ✅ `.eml` 原始邮件文件
   - ✅ 附件文件

---

## 使用方法

### 基础用法（宽容模式 - 推荐）

```python
from app.services.email_account_service import email_account_service

# 删除邮箱账户（文件删除失败不影响数据库删除）
stats = await email_account_service.delete_account_cascade(account_id=123)

print(stats)
# {
#     "emails_deleted": 50,
#     "analyses_deleted": 50,
#     "attachments_deleted": 120,
#     "files_deleted": 170,
#     "files_failed": 0
# }
```

**特点**：
- 文件删除失败时记录日志，但继续删除数据库记录
- 适用于大多数场景，确保用户操作不会被阻塞
- 失败的文件会记录在 `files_failed` 字段

### 严格模式（推荐生产环境关键数据）

```python
# 文件删除失败时回滚整个事务
try:
    stats = await email_account_service.delete_account_cascade(
        account_id=123,
        strict_file_deletion=True  # 启用严格模式
    )
except RuntimeError as e:
    print(f"删除失败: {e}")
    # 处理失败：可能是 OSS 连接问题，需要解决后重试
```

**特点**：
- 文件删除失败时抛出异常，事务回滚
- 保证数据库与文件存储的一致性
- 适用于合规要求高的场景（如审计、存档）

### 自定义实例配置

```python
# 创建严格模式的服务实例
strict_service = EmailAccountService(strict_file_deletion=True)

# 后续所有调用都是严格模式
stats = await strict_service.delete_account_cascade(account_id=123)
```

---

## 工作流程

```
1. 开始事务
    ↓
2. 检查邮箱账户是否存在
    ↓
3. 查询该账户的所有邮件（email_raw_messages）
    ↓
4. 对每封邮件：
    ├─ a. 删除邮件分析结果（email_analyses）
    │      - 使用 DELETE 语句，不依赖数据库级联
    │      - 统计删除数量
    │
    ├─ b. 删除 .eml 原始文件（OSS/local）
    │      - 严格模式：失败则抛出异常 → 回滚事务
    │      - 宽容模式：失败则记录日志，继续
    │
    ├─ c. 删除附件文件（OSS/local）
    │      - 同上
    │
    ├─ d. 删除附件记录（email_attachments）
    │
    └─ e. 删除邮件记录（email_raw_messages）
    ↓
5. 删除邮箱账户（email_accounts）
    ↓
6. 提交事务
    ↓
7. 返回统计信息
```

---

## API 接口

### DELETE `/admin/email-accounts/{account_id}`

**请求**：
```bash
curl -X DELETE http://localhost:8000/admin/email-accounts/123 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**响应**（成功）：
```json
{
  "message": "邮箱账户已删除",
  "stats": {
    "emails_deleted": 50,
    "analyses_deleted": 50,
    "attachments_deleted": 120,
    "files_deleted": 170,
    "files_failed": 0
  }
}
```

**响应**（账户不存在）：
```json
{
  "detail": "邮箱账户不存在"
}
```

**响应**（严格模式下文件删除失败）：
```json
{
  "detail": "删除失败: 删除邮件文件失败: emails/raw/123/2026-01-15/abc.eml"
}
```

---

## 日志输出

### 宽容模式

```
[INFO] [EmailAccountService] 开始级联删除邮箱账户: 123 (严格模式: False)
[INFO] [EmailAccountService] 删除账户: Sales Account (sales@example.com)
[INFO] [EmailAccountService] 找到 50 封邮件
[DEBUG] [EmailAccountService] 删除邮件: msg-001
[DEBUG] [EmailAccountService] 删除邮件分析: 1 条
[DEBUG] [EmailAccountService] 已删除 OSS 文件: emails/raw/123/2026-01-15/msg-001.eml
[WARNING] [EmailAccountService] 删除文件失败: emails/attachments/123/2026-01-15/att-001.pdf (oss), 错误: Connection timeout
[INFO] [EmailAccountService] 级联删除完成: 邮件 50 封, 分析 50 条, 附件 120 个, 文件 169 个, 失败 1 个
```

### 严格模式

```
[INFO] [EmailAccountService] 开始级联删除邮箱账户: 123 (严格模式: True)
[INFO] [EmailAccountService] 删除账户: Sales Account (sales@example.com)
[INFO] [EmailAccountService] 找到 50 封邮件
[DEBUG] [EmailAccountService] 删除邮件: msg-001
[DEBUG] [EmailAccountService] 删除邮件分析: 1 条
[ERROR] [EmailAccountService] 删除文件失败: emails/raw/123/2026-01-15/msg-001.eml (oss), 错误: Connection timeout
[ERROR] [EmailAccountService] 删除邮件失败: msg-001, 删除邮件文件失败: emails/raw/123/2026-01-15/msg-001.eml
[ERROR] [EmailAccountService] 删除邮件 msg-001 失败: 删除邮件文件失败: emails/raw/123/2026-01-15/msg-001.eml
```

---

## 优化内容（2026-02-01）

### ✅ 问题 1：显式删除 EmailAnalysis

**之前**：
- 依赖数据库外键的 `ondelete="CASCADE"`
- 跨数据库兼容性风险

**现在**：
```python
# 显式删除（app/services/email_account_service.py:167-171）
stmt = delete(EmailAnalysis).where(EmailAnalysis.email_id == email.id)
result = await session.execute(stmt)
analyses_count = result.rowcount
stats["analyses_deleted"] += analyses_count
```

**优点**：
- ✅ 不依赖数据库级联
- ✅ 统计删除数量
- ✅ 更好的跨数据库兼容性

### ✅ 问题 2：文件删除失败处理

**之前**：
- 文件删除失败只记录 `files_failed`
- 数据库记录仍被删除 → 孤儿文件

**现在**：
```python
# 严格模式（app/services/email_account_service.py:177-180）
if not success:
    stats["files_failed"] += 1
    if strict_file_deletion:
        raise RuntimeError(f"删除邮件文件失败: {email.oss_key}")
```

**优点**：
- ✅ 宽容模式：不影响用户操作（默认）
- ✅ 严格模式：保证数据一致性（可选）
- ✅ 详细的错误日志

---

## 配置建议

### 开发环境

```python
# 使用宽容模式（默认）
email_account_service = EmailAccountService()

# 文件删除失败不影响测试流程
stats = await email_account_service.delete_account_cascade(account_id)
```

### 生产环境（一般业务）

```python
# 使用宽容模式
stats = await email_account_service.delete_account_cascade(
    account_id=account_id,
    strict_file_deletion=False
)

# 监控 files_failed 字段
if stats["files_failed"] > 0:
    logger.warning(f"有 {stats['files_failed']} 个文件删除失败，需要排查")
```

### 生产环境（合规要求高）

```python
# 使用严格模式
try:
    stats = await email_account_service.delete_account_cascade(
        account_id=account_id,
        strict_file_deletion=True
    )
except RuntimeError as e:
    # 删除失败，提示用户稍后重试
    raise HTTPException(
        status_code=500,
        detail=f"删除失败，请检查存储服务: {str(e)}"
    )
```

---

## 故障排查

### 问题：文件删除失败（宽容模式）

**现象**：
```json
{
  "files_deleted": 169,
  "files_failed": 1
}
```

**原因**：
1. OSS 网络超时
2. OSS 权限不足
3. 本地磁盘空间不足

**解决**：
1. 检查日志中的具体错误信息
2. 检查 OSS 连接配置
3. 手动删除孤儿文件（使用 OSS 控制台或脚本）

### 问题：严格模式下删除失败

**现象**：
```
RuntimeError: 删除邮件文件失败: emails/raw/123/2026-01-15/msg-001.eml
```

**解决**：
1. 检查 OSS/本地存储服务是否正常
2. 检查网络连接
3. 问题解决后重新调用删除接口

---

## 数据库表结构

### 关联关系

```sql
email_accounts (id)
    ↓ email_account_id
email_raw_messages (id)
    ↓ email_id
    ├─ email_analyses (ondelete="CASCADE")
    └─ email_attachments (cascade="all, delete-orphan")
```

### 外键定义

```python
# email_raw_messages.email_account_id
email_account_id = ForeignKey("email_accounts.id", ondelete="SET NULL")

# email_analyses.email_id
email_id = ForeignKey("email_raw_messages.id", ondelete="CASCADE")

# email_attachments.email_id
email_id = ForeignKey("email_raw_messages.id", ondelete="CASCADE")
```

---

## 性能考虑

### 大批量删除

如果邮箱账户有数千封邮件，建议：

```python
# 1. 分批删除（每次 100 封邮件）
# 2. 添加进度提示
# 3. 使用后台任务

from app.workers.tasks import delete_email_account_task

# 提交后台任务
task_id = await delete_email_account_task.delay(account_id=123)
```

### 索引优化

确保以下索引存在：
```sql
CREATE INDEX idx_email_raw_messages_account ON email_raw_messages(email_account_id);
CREATE INDEX idx_email_analyses_email ON email_analyses(email_id);
CREATE INDEX idx_email_attachments_email ON email_attachments(email_id);
```

---

## 相关文档

- [MANUAL.md](MANUAL.md#5-邮件管理) - 邮件管理模块
- [LLM_ARCHITECTURE_REVIEW.md](LLM_ARCHITECTURE_REVIEW.md) - LLM 调用架构
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构文档

---

*文档创建时间: 2026-02-01*
*最后更新: 2026-02-01*
