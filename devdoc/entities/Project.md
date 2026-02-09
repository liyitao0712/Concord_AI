# Project 项目

## 概述

Project 是项目实体，支持多种项目类型（研发/订单/采购/销售等）。通过 ProjectAssociation 多态关联表实现与客户、供应商、合同、产品等业务实体的多对多关联。项目下包含 Task（任务/里程碑），通过 Progress 记录进度。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `projects` / `project_associations` |
| 模型路径 | `backend/app/models/project.py` |
| Schema 路径 | `backend/app/schemas/project.py` |

### 状态流转

```
draft → active → on_hold / completed / cancelled
```

### Project（项目）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(200) | 项目名称 |
| project_type | String(50) | 项目类型: general/research/order/purchase/sales 等 |
| description | Text | 项目描述 |
| status | String(20) | 状态: draft/active/on_hold/completed/cancelled |
| priority | String(10) | 优先级: low/medium/high/urgent |
| start_date | Date | 开始日期 |
| due_date | Date | 截止日期 |
| owner_id | String(36) | 项目负责人 ID（外键 → users） |
| tags | JSON | 标签列表 |
| notes | Text | 备注 |
| created_by | String(36) | 创建人 ID（外键 → users） |
| org_id | String(36) | 所属组织（外键 → organizations） |
| owner_dept_id | String(36) | 负责人部门（外键 → departments） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### ProjectAssociation（项目关联表）

通过 entity_type + entity_id 实现多态多对多关联。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| project_id | String(36) | 项目 ID（外键 → projects） |
| entity_type | String(30) | 实体类型（见下方枚举） |
| entity_id | String(36) | 实体 ID |
| notes | String(500) | 关联备注 |
| created_at | DateTime | 创建时间 |

**entity_type 支持的值**：
- `customer` - 客户
- `supplier` - 供应商
- `purchase_contract` - 采购合同
- `sales_contract` - 销售合同
- `product` - 产品
- `inbound_order` - 入库单
- `outbound_order` - 出库单
- `client_rfq` - 客户询价单
- `quotation` - 报价单
- `supplier_rfq` - 供应商询价单
- `supplier_quotation` - 供应商报价单

唯一约束：`(project_id, entity_type, entity_id)` 防止重复关联。

## 关系

- **ProjectAssociation**: 一对多，项目可关联多个业务实体（级联删除）
- **Task**: 一对多，项目下包含多个任务（级联删除，按 sort_order 排序）
- **User**: 多对一，项目负责人和创建人

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/projects | 项目列表（分页、搜索、筛选） |
| POST | /admin/projects | 创建项目 |
| GET | /admin/projects/{project_id} | 项目详情 |
| PUT | /admin/projects/{project_id} | 更新项目 |
| DELETE | /admin/projects/{project_id} | 删除项目 |
| PUT | /admin/projects/{project_id}/status | 更新状态 |
| POST | /admin/projects/{project_id}/associations | 添加关联实体 |
| DELETE | /admin/projects/{project_id}/associations/{assoc_id} | 移除关联实体 |
| POST | /admin/projects/from-email/{email_id} | 从邮件创建项目 |

## 相关文件

- Model: `backend/app/models/project.py`
- Schema: `backend/app/schemas/project.py`
- API: `backend/app/api/projects.py`
- Frontend: `frontend/src/app/admin/projects/page.tsx`, `frontend/src/app/admin/projects/ProjectsPanel.tsx`
