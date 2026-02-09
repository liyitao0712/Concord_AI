# Task 任务

## 概述

Task 是任务/里程碑实体，属于某个项目（Project）。支持双重用途：具体可执行任务（action）和阶段里程碑（milestone）。通过自引用 parent_task_id 实现子任务树结构。任务的进度通过 Progress 记录追踪。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `tasks` |
| 模型路径 | `backend/app/models/task.py` |
| Schema 路径 | `backend/app/schemas/task.py` |

### 状态流转

```
pending → in_progress → completed / cancelled
```

### Task（任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| project_id | String(36) | 所属项目 ID（外键 → projects，级联删除） |
| parent_task_id | String(36) | 父任务 ID（自引用外键 → tasks，级联删除） |
| title | String(300) | 任务标题 |
| description | Text | 任务描述 |
| task_type | String(20) | 任务类型: action（具体任务）/ milestone（里程碑） |
| phase_name | String(100) | 阶段名称（milestone 类型使用） |
| status | String(20) | 状态: pending/in_progress/completed/cancelled |
| priority | String(10) | 优先级: low/medium/high/urgent |
| assignee_id | String(36) | 负责人 ID（外键 → users） |
| sort_order | Integer | 排序序号（越小越靠前） |
| completion_percentage | Integer | 完成百分比 0-100 |
| due_date | Date | 截止日期 |
| created_by | String(36) | 创建人 ID（外键 → users） |
| org_id | String(36) | 所属组织（外键 → organizations） |
| owner_id | String(36) | 负责人（外键 → users） |
| owner_dept_id | String(36) | 负责人部门（外键 → departments） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 关系

- **Project**: 多对一，每个任务属于一个项目
- **Task (parent)**: 自引用多对一，支持子任务树结构
- **Task (children)**: 自引用一对多，包含子任务（级联删除）
- **Progress**: 一对多，包含多个进度记录（级联删除，按 created_at 倒序）
- **User**: 多对一，关联负责人和创建人

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/tasks | 任务列表（分页、按项目筛选） |
| POST | /admin/tasks | 创建任务 |
| GET | /admin/tasks/{task_id} | 任务详情 |
| PUT | /admin/tasks/{task_id} | 更新任务 |
| DELETE | /admin/tasks/{task_id} | 删除任务 |

## 相关文件

- Model: `backend/app/models/task.py`
- Schema: `backend/app/schemas/task.py`
- API: `backend/app/api/tasks.py`
