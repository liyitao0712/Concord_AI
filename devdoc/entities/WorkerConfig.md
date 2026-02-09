# WorkerConfig Worker 配置

## 概述

WorkerConfig 是后台 Worker 配置实体，管理飞书 Bot、邮件轮询等后台任务的运行参数。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| worker_type | String(20) | Worker 类型 (feishu/email_polling/scheduler) |
| name | String(100) | 名称 |
| config | JSON | 配置参数 |
| agent_id | String(50) | 绑定的 Agent (默认 chat_agent) |
| is_enabled | Boolean | 是否启用 |
| description | Text | 描述 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## Worker 类型

| 类型 | 说明 |
|------|------|
| feishu | 飞书 Bot Worker |
| email_polling | 邮件轮询 Worker |
| scheduler | 定时任务 Worker |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/workers | Worker 列表 |
| POST | /admin/workers | 创建 Worker |
| PUT | /admin/workers/{id} | 更新 Worker |
| DELETE | /admin/workers/{id} | 删除 Worker |

## 相关文件

- Model: `backend/app/models/worker.py`
- API: `backend/app/api/workers.py`
- Frontend: `frontend/src/app/admin/workers/page.tsx`
