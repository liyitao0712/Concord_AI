# EmailRawMessage 原始邮件

## 概述

EmailRawMessage 存储系统接收到的原始邮件数据，EmailAttachment 存储邮件附件信息。邮件原文和附件文件存储在 OSS 中，数据库只保存元数据。

## 数据模型

### EmailRawMessage（原始邮件）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| email_account_id | Integer | 关联邮箱账户（外键） |
| message_id | String(500) | 邮件 Message-ID（唯一索引） |
| sender | String(255) | 发件人邮箱 |
| sender_name | String(255) | 发件人显示名称 |
| recipients | Text | 收件人列表（JSON） |
| subject | String(1000) | 邮件主题 |
| received_at | DateTime | 接收时间 |
| body_text | Text | 邮件正文（纯文本） |
| oss_key | String(500) | OSS 存储路径 |
| storage_type | String(20) | 存储类型（oss/local） |
| size_bytes | Integer | 邮件大小（字节） |
| is_processed | Boolean | 是否已处理 |
| event_id | String(36) | 关联事件 ID |
| processed_at | DateTime | 处理时间 |
| created_at | DateTime | 入库时间 |

### EmailAttachment（邮件附件）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| email_id | String(36) | 关联邮件 ID（外键） |
| filename | String(500) | 文件名 |
| content_type | String(100) | MIME 类型 |
| size_bytes | Integer | 文件大小（字节） |
| oss_key | String(500) | OSS 存储路径 |
| storage_type | String(20) | 存储类型（oss/local） |
| is_inline | Boolean | 是否内联附件 |
| content_id | String(255) | Content-ID（内联附件用） |
| is_signature | Boolean | 是否签名图片（自动过滤） |
| created_at | DateTime | 创建时间 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/emails | 邮件列表（分页、搜索、筛选） |
| GET | /admin/emails/{id} | 邮件详情 |
| GET | /admin/emails/{id}/raw | 下载原始邮件（.eml） |
| GET | /admin/emails/{id}/attachments/{att_id} | 下载附件 |

## 相关文件

- Model: `backend/app/models/email_raw.py`
- API: `backend/app/api/emails.py`
- 存储: `backend/app/storage/email_persistence.py`
- OSS: `backend/app/storage/oss.py`
