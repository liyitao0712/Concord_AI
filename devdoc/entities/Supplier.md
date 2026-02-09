# Supplier 供应商

## 概述

Supplier 是供应商（公司）实体，SupplierContact 是供应商下的联系人。结构与 Customer 类似，但包含供应商特有字段（如 main_products、supplier_level）。

## 数据模型

### Supplier（供应商）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(200) | 公司全称 |
| short_name | String(100) | 公司简称 |
| country | String(100) | 国家 |
| region | String(100) | 地区/大洲 |
| industry | String(100) | 行业 |
| company_size | String(50) | 规模 (small/medium/large/enterprise) |
| main_products | Text | 主营产品描述 |
| supplier_level | String(20) | 供应商级别 (potential/normal/important/strategic) |
| email | String(200) | 公司邮箱 |
| phone | String(50) | 电话 |
| website | String(300) | 官网 |
| address | Text | 地址 |
| payment_terms | String(100) | 付款条款 |
| shipping_terms | String(50) | 贸易术语 |
| is_active | Boolean | 是否启用 |
| source | String(50) | 来源 (email/exhibition/1688/other) |
| notes | Text | 备注 |
| tags | JSON | 标签列表 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### SupplierContact（供应商联系人）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| supplier_id | String(36) | 关联供应商 ID（外键） |
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

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/suppliers | 供应商列表（分页、搜索） |
| POST | /admin/suppliers | 创建供应商 |
| GET | /admin/suppliers/{id} | 供应商详情 |
| PUT | /admin/suppliers/{id} | 更新供应商 |
| DELETE | /admin/suppliers/{id} | 删除供应商 |
| POST | /admin/suppliers/ai-search | AI 搜索供应商信息 |

## 相关文件

- Model: `backend/app/models/supplier.py`
- API: `backend/app/api/suppliers.py`
- Agent: `backend/app/agents/add_new_supplier_helper.py`
- Frontend: `frontend/src/app/admin/suppliers/page.tsx`
