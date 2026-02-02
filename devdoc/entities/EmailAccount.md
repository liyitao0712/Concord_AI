# EmailAccount 邮箱账户

## 概述

EmailAccount 是邮箱账户实体，用于配置 IMAP/SMTP 邮箱连接。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(100) | 账户名称 |
| email | String(255) | 邮箱地址 |
| purpose | Enum | 用途 (send/receive/both) |
| imap_host | String(255) | IMAP 服务器 |
| imap_port | Integer | IMAP 端口 |
| imap_use_ssl | Boolean | IMAP SSL |
| smtp_host | String(255) | SMTP 服务器 |
| smtp_port | Integer | SMTP 端口 |
| smtp_use_tls | Boolean | SMTP TLS |
| username | String(255) | 用户名 |
| password | String(255) | 密码/授权码（加密存储） |
| is_active | Boolean | 是否启用 |
| last_sync_at | DateTime | 最后同步时间 |
| created_at | DateTime | 创建时间 |

## 用途 (purpose)

| 值 | 说明 |
|-----|------|
| send | 仅发送 |
| receive | 仅接收 |
| both | 收发都用 |

## 级联删除

删除邮箱账户时会级联删除：
- EmailRawMessage（原始邮件）
- EmailAttachment（附件）
- EmailAnalysis（分析结果）

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/email-accounts | 账户列表 |
| POST | /admin/email-accounts | 创建账户 |
| POST | /admin/email-accounts/{id}/test | 测试连接 |
| DELETE | /admin/email-accounts/{id} | 删除账户 |

## 相关文件

- Model: `backend/app/models/email_account.py`
- API: `backend/app/api/email_accounts.py`
- Service: `backend/app/services/email_service.py`

## 详细文档

参见 [EMAIL_ACCOUNT_CASCADE_DELETE.md](../EMAIL_ACCOUNT_CASCADE_DELETE.md)
