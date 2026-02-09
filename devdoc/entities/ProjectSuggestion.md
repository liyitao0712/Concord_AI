# ProjectSuggestion 项目建议

## 概述

ProjectSuggestion 存储 AI 从邮件中提取的项目建议，需人工审批后转为正式项目（Project）。审批流程与 CustomerSuggestion 类似：AI Agent 识别 → 保存建议（pending） → 管理员审批 → 批准后创建 Project。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `project_suggestions` |
| 模型路径 | `backend/app/models/project_suggestion.py` |
| Schema 路径 | `backend/app/schemas/project_suggestion.py` |

### 审批流程

```
AI 识别 → pending → approved（创建 Project）
                  → rejected
```

### ProjectSuggestion（项目建议）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| suggested_name | String(200) | 建议的项目名称 |
| suggested_type | String(50) | 建议的项目类型，默认 general |
| suggested_description | Text | 建议的项目描述 |
| suggested_priority | String(10) | 建议的优先级: low/medium/high/urgent |
| suggested_associations | JSON | 建议的关联实体 [{entity_type, entity_id, entity_name}] |
| confidence | Float | AI 置信度 0-1 |
| reasoning | Text | AI 推理说明 |
| trigger_email_id | String(36) | 触发的邮件 ID |
| trigger_content | Text | 触发建议的内容摘要 |
| trigger_source | String(20) | 来源: email / manual |
| status | String(20) | 状态: pending / approved / rejected |
| reviewed_by | String(36) | 审批人 ID |
| reviewed_at | DateTime | 审批时间 |
| review_note | Text | 审批备注 |
| created_project_id | String(36) | 审批通过后创建的项目 ID |
| created_at | DateTime | 创建时间 |

## 关系

- **Project**: 审批通过后通过 created_project_id 关联创建的项目
- **EmailRawMessage**: 通过 trigger_email_id 关联触发邮件

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/project-suggestions | 建议列表（分页） |
| GET | /admin/project-suggestions/{suggestion_id} | 建议详情 |
| POST | /admin/project-suggestions/{suggestion_id}/approve | 批准建议 |
| POST | /admin/project-suggestions/{suggestion_id}/reject | 拒绝建议 |

## 相关文件

- Model: `backend/app/models/project_suggestion.py`
- Schema: `backend/app/schemas/project_suggestion.py`
- API: `backend/app/api/project_suggestions.py`
