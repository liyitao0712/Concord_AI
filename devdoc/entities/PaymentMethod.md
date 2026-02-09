# PaymentMethod 付款方式

## 概述

PaymentMethod 是付款方式参考数据实体（只读系统预设），包含国际贸易中常见的付款方式（T/T、L/C、D/P 等）。用于合同表单的付款方式选择。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| code | String(20) | 付款方式代码（唯一，如 T/T、L/C） |
| name_en | String(200) | 英文全称 |
| name_zh | String(200) | 中文名称 |
| category | String(50) | 分类 (remittance/credit/collection/other) |
| description_zh | Text | 中文说明 |
| description_en | Text | 英文说明 |
| is_common | Boolean | 是否常用 |
| sort_order | Integer | 排序顺序 |
| created_at | DateTime | 创建时间 |

## 付款方式分类

| 分类 | 说明 | 示例 |
|------|------|------|
| remittance | 汇付 | T/T、M/T、D/D |
| credit | 信用证 | L/C、Standby L/C |
| collection | 托收 | D/P、D/A |
| other | 其他 | O/A、CAD、Escrow |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/payment-methods | 付款方式列表 |
| GET | /admin/payment-methods/{id} | 详情 |

## 相关文件

- Model: `backend/app/models/payment_method.py`
- API: `backend/app/api/payment_methods.py`
- Migration: `backend/alembic/versions/b2c3d4e5f6g7_add_payment_methods_table.py`
