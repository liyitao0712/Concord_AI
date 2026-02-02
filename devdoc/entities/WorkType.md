# WorkType 工作类型

## 概述

WorkType 是用于分类和管理业务工作类型的实体。支持 Parent-Child 层级结构，可被 AI 自动识别和建议。

## 数据模型

### WorkType（工作类型定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| parent_id | String(36) | 父级 ID（自引用外键，可为空） |
| code | String(100) | 唯一标识码（全大写英文+下划线） |
| name | String(100) | 中文名称 |
| description | Text | 详细描述（供 LLM 参考） |
| level | Integer | 层级：1=顶级，2=子级 |
| path | String(500) | 完整路径（如 /ORDER/ORDER_NEW） |
| examples | JSON | 示例文本列表 |
| keywords | JSON | 关键词列表 |
| is_active | Boolean | 是否启用 |
| is_system | Boolean | 是否系统内置 |
| usage_count | Integer | 使用次数统计 |
| created_by | String(100) | 创建者标识 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### WorkTypeSuggestion（AI 建议，待审批）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| suggested_code | String(100) | 建议的类型代码 |
| suggested_name | String(100) | 建议的中文名称 |
| suggested_description | Text | 建议的描述 |
| suggested_parent_id | String(36) | 建议的父级 ID |
| suggested_parent_code | String(100) | 建议的父级代码 |
| suggested_level | Integer | 建议的层级 |
| suggested_examples | JSON | 建议的示例 |
| suggested_keywords | JSON | 建议的关键词 |
| confidence | Float | AI 置信度（0-1） |
| reasoning | Text | AI 推理说明 |
| trigger_email_id | String(36) | 触发邮件 ID |
| trigger_content | Text | 触发内容摘要 |
| status | String(20) | pending/approved/rejected |
| workflow_id | String(100) | Temporal Workflow ID |
| reviewed_by | String(36) | 审批人 ID |
| reviewed_at | DateTime | 审批时间 |
| review_note | Text | 审批备注 |
| created_work_type_id | String(36) | 批准后创建的 WorkType ID |
| created_at | DateTime | 创建时间 |

## 层级结构

```
Level 1 (顶级)          Level 2 (子级)
─────────────────────────────────────────
ORDER (订单)     ──→    ORDER_NEW (新订单)
                 ──→    ORDER_CHANGE (订单修改)

INQUIRY (询价)

SHIPMENT (物流)

PAYMENT (付款)

COMPLAINT (投诉)

OTHER (其他)
```

### 命名规范

- 顶级类型：全大写英文，如 `ORDER`、`INQUIRY`
- 子级类型：以父级代码为前缀 + 下划线 + 子类型名，如 `ORDER_NEW`、`ORDER_CHANGE`

## API 接口

### WorkType CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/work-types | 获取列表（扁平） |
| GET | /admin/work-types/tree | 获取树形结构 |
| POST | /admin/work-types | 创建工作类型 |
| GET | /admin/work-types/{id} | 获取详情 |
| PUT | /admin/work-types/{id} | 更新工作类型 |
| DELETE | /admin/work-types/{id} | 删除工作类型 |

### WorkTypeSuggestion 审批

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/work-type-suggestions | 获取建议列表 |
| GET | /admin/work-type-suggestions/{id} | 获取建议详情 |
| POST | /admin/work-type-suggestions/{id}/approve | 批准建议 |
| POST | /admin/work-type-suggestions/{id}/reject | 拒绝建议 |

## 与其他模块的关系

```
┌─────────────────┐
│   邮件进入系统   │
└────────┬────────┘
         ↓
┌─────────────────┐    ┌─────────────────┐
│ EmailSummarizer │    │WorkTypeAnalyzer │
│   (并行执行)    │    │   (并行执行)    │
└────────┬────────┘    └────────┬────────┘
         │                      │
         │                      ↓
         │             ┌─────────────────┐
         │             │ 匹配现有类型？  │
         │             └────────┬────────┘
         │                      │
         │         ┌────────────┴────────────┐
         │         ↓                         ↓
         │  ┌─────────────┐         ┌─────────────────┐
         │  │ 使用现有类型 │         │ 创建 Suggestion │
         │  └─────────────┘         └────────┬────────┘
         │                                   ↓
         │                          ┌─────────────────┐
         │                          │ Temporal 审批流 │
         │                          └────────┬────────┘
         ↓                                   ↓
┌─────────────────┐                 ┌─────────────────┐
│  Event.intent   │                 │ 人工审批/超时   │
└─────────────────┘                 └─────────────────┘
```

## 相关文件

- Model: `backend/app/models/work_type.py`
- Schema: `backend/app/schemas/work_type.py`
- API: `backend/app/api/work_types.py`
- Migration: `backend/alembic/versions/j9k0l1m2n3o4_add_work_types_table.py`
- Frontend: `frontend/src/app/admin/work-types/page.tsx`

## 种子数据

系统初始化时自动创建以下工作类型：

| Code | Name | Level |
|------|------|-------|
| ORDER | 订单 | 1 |
| ORDER_NEW | 新订单 | 2 |
| ORDER_CHANGE | 订单修改 | 2 |
| INQUIRY | 询价 | 1 |
| SHIPMENT | 物流 | 1 |
| PAYMENT | 付款 | 1 |
| COMPLAINT | 投诉 | 1 |
| OTHER | 其他 | 1 |
