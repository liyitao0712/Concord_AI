# Customer 客户

## 概述

Customer 是客户（公司）实体，Contact 是客户下的联系人。CustomerSuggestion 存储 AI 从邮件中提取的新客户建议，需人工审批后转为正式客户。

## 数据模型

### Customer（客户）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(200) | 公司全称 |
| short_name | String(100) | 公司简称 |
| country | String(100) | 国家 |
| region | String(100) | 地区/大洲 |
| industry | String(100) | 行业 |
| company_size | String(50) | 规模 (small/medium/large/enterprise) |
| annual_revenue | String(50) | 年营收区间 |
| customer_level | String(20) | 客户级别 (potential/normal/important/vip) |
| email | String(200) | 公司邮箱 |
| phone | String(50) | 电话 |
| website | String(300) | 官网 |
| address | Text | 地址 |
| payment_terms | String(100) | 付款条款 |
| shipping_terms | String(50) | 贸易术语 (FOB/CIF 等) |
| is_active | Boolean | 是否启用 |
| source | String(50) | 来源 (email/exhibition/referral/website/other) |
| notes | Text | 备注 |
| tags | JSON | 标签列表 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### Contact（联系人）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| customer_id | String(36) | 关联客户 ID（外键） |
| name | String(100) | 姓名 |
| title | String(100) | 职位 |
| department | String(100) | 部门 |
| email | String(200) | 邮箱 |
| phone | String(50) | 电话 |
| mobile | String(50) | 手机 |
| social_media | JSON | 社交媒体 {wechat, linkedin} |
| is_primary | Boolean | 是否主要联系人 |
| is_active | Boolean | 是否启用 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### CustomerSuggestion（AI 客户建议）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| suggestion_type | String(20) | 建议类型 (new_customer/new_contact) |
| suggested_company_name | String(200) | 建议的公司名称 |
| suggested_short_name | String(100) | 建议的简称 |
| suggested_country | String(100) | 建议的国家 |
| suggested_region | String(100) | 建议的地区 |
| suggested_industry | String(100) | 建议的行业 |
| suggested_website | String(300) | 建议的官网 |
| suggested_email_domain | String(200) | 邮箱域名 |
| suggested_customer_level | String(20) | 建议的客户级别 |
| suggested_tags | JSON | 建议的标签 |
| suggested_contact_name | String(100) | 建议的联系人姓名 |
| suggested_contact_email | String(200) | 建议的联系人邮箱 |
| suggested_contact_title | String(100) | 建议的联系人职位 |
| suggested_contact_phone | String(50) | 建议的联系人电话 |
| suggested_contact_department | String(100) | 建议的联系人部门 |
| confidence | Float | AI 置信度 (0-1) |
| reasoning | Text | AI 推理说明 |
| sender_type | String(20) | 发件方类型 |
| trigger_email_id | String(36) | 触发邮件 ID |
| trigger_content | Text | 触发内容摘要 |
| email_domain | String(200) | 邮箱域名（去重用） |
| matched_customer_id | String(36) | 匹配到的已有客户 ID |
| status | String(20) | pending/approved/rejected |
| workflow_id | String(100) | Temporal Workflow ID |
| reviewed_by | String(36) | 审批人 ID |
| reviewed_at | DateTime | 审批时间 |
| review_note | Text | 审批备注 |
| created_customer_id | String(36) | 批准后创建的客户 ID |
| created_contact_id | String(36) | 批准后创建的联系人 ID |
| created_at | DateTime | 创建时间 |

## API 接口

### 客户 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/customers | 客户列表（分页、搜索） |
| POST | /admin/customers | 创建客户 |
| GET | /admin/customers/{id} | 客户详情 |
| PUT | /admin/customers/{id} | 更新客户 |
| DELETE | /admin/customers/{id} | 删除客户 |
| POST | /admin/customers/ai-search | AI 搜索公司信息 |

### 客户建议审批

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/customer-suggestions | 建议列表 |
| POST | /admin/customer-suggestions/{id}/approve | 批准 |
| POST | /admin/customer-suggestions/{id}/reject | 拒绝 |

## 相关文件

- Model: `backend/app/models/customer.py`, `backend/app/models/customer_suggestion.py`
- API: `backend/app/api/customers.py`
- Agent: `backend/app/agents/customer_extractor.py`, `backend/app/agents/add_new_client_helper.py`
- Frontend: `frontend/src/app/admin/customers/page.tsx`
