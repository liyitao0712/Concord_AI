# Product 产品

## 概述

Product 是产品实体，归属于某个品类。ProductSupplier 是产品与供应商的多对多关联表，记录供应价格、起订量、交期等供应信息。

## 数据模型

### Product（产品）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| category_id | String(36) | 品类 ID（外键） |
| name | String(200) | 产品名称 |
| model_number | String(100) | 型号 |
| specifications | Text | 规格参数 |
| unit | String(50) | 单位 (PCS/SET/KG) |
| moq | Integer | 最小起订量 |
| reference_price | Numeric(12,2) | 参考价格 |
| currency | String(10) | 币种（默认 USD） |
| hs_code | String(20) | HS 海关编码 |
| origin | String(100) | 产地/原产国 |
| material | String(200) | 材质 |
| packaging | String(200) | 包装方式 |
| images | JSON | 产品图片列表 |
| description | Text | 产品描述 |
| tags | JSON | 标签列表 |
| status | String(20) | 状态 (active/inactive/discontinued) |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### ProductSupplier（产品-供应商关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| product_id | String(36) | 产品 ID（外键） |
| supplier_id | String(36) | 供应商 ID（外键） |
| supply_price | Numeric(12,2) | 供应价格 |
| currency | String(10) | 币种 |
| moq | Integer | 供应商起订量 |
| lead_time | Integer | 交货周期（天） |
| is_primary | Boolean | 是否主要供应商 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**唯一约束**: (product_id, supplier_id) — 同一产品同一供应商只能有一条记录。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/products | 产品列表（分页、搜索、按品类筛选） |
| POST | /admin/products | 创建产品 |
| GET | /admin/products/{id} | 产品详情 |
| PUT | /admin/products/{id} | 更新产品 |
| DELETE | /admin/products/{id} | 删除产品 |

## 相关文件

- Model: `backend/app/models/product.py`
- API: `backend/app/api/products.py`
- Frontend: `frontend/src/app/admin/products/page.tsx`
