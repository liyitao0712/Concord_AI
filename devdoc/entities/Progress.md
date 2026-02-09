# Progress 进度记录

## 概述

Progress 是进度记录/时间线实体，记录任务（Task）的状态更新、完成度变化和沟通记录。采用 Append-only 设计，记录不可编辑，支持关联邮件实现邮件驱动的进度追踪。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `progress_entries` |
| 模型路径 | `backend/app/models/progress.py` |
| Schema 路径 | `backend/app/schemas/progress.py` |

### 记录类型

| progress_type | 说明 | 关键字段 |
|------|------|------|
| status_update | 状态变更记录 | old_status, new_status |
| completion | 完成度更新 | percentage |
| communication | 沟通/备注记录 | content, email_id |

### Progress（进度记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| task_id | String(36) | 所属任务 ID（外键 → tasks，级联删除） |
| progress_type | String(20) | 记录类型: status_update/completion/communication |
| content | Text | 记录内容/备注 |
| old_status | String(20) | 变更前状态（status_update 类型使用） |
| new_status | String(20) | 变更后状态（status_update 类型使用） |
| percentage | Integer | 完成百分比（completion 类型使用） |
| email_id | String(36) | 关联邮件 ID（外键 → email_raw_messages） |
| attachments | JSON | 附件列表 [{name, key, storage_type}] |
| created_by | String(36) | 创建人 ID（外键 → users） |
| created_at | DateTime | 创建时间 |

## 关系

- **Task**: 多对一，每个进度记录属于一个任务
- **EmailRawMessage**: 多对一，可选关联邮件（沟通记录来源）

## 设计说明

- **Append-only**: 进度记录只能创建和删除，不支持编辑，确保时间线的真实性
- **邮件驱动**: 通过 email_id 关联邮件，实现将邮件沟通自动记录为项目进度
- **多用途**: 同一个表通过 progress_type 区分不同类型的记录，简化数据模型

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/progress | 进度记录列表（按 task_id 筛选） |
| POST | /admin/progress | 创建进度记录 |
| DELETE | /admin/progress/{progress_id} | 删除进度记录 |

## 相关文件

- Model: `backend/app/models/progress.py`
- Schema: `backend/app/schemas/progress.py`
- API: `backend/app/api/progress.py`
