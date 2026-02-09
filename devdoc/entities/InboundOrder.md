# InboundOrder 入库单

## 概述

InboundOrder 是入库单实体，记录货物入库操作。通常关联采购合同，入库确认后更新库存。InboundLine 是入库明细行。

## 数据模型

### InboundOrder（入库单）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| order_no | String(50) | 入库单号（唯一） |
| warehouse_id | String(36) | 目标仓库 ID（外键） |
| purchase_contract_id | String(36) | 关联采购合同 ID（外键） |
| supplier_id | String(36) | 供应商 ID（外键） |
| status | String(20) | 状态 |
| expected_date | Date | 预计到货日期 |
| actual_date | Date | 实际到货日期 |
| notes | Text | 备注 |
| created_by | String(36) | 创建人 ID（外键） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### InboundLine（入库明细行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| inbound_order_id | String(36) | 入库单 ID（外键） |
| product_id | String(36) | 产品 ID（外键） |
| purchase_line_id | String(36) | 关联采购合同行 ID（外键） |
| expected_quantity | Numeric(14,4) | 预计数量 |
| received_quantity | Numeric(14,4) | 实收数量 |
| unit | String(50) | 单位 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 状态流转

```
draft → confirmed → partial_received → received
                                    ↘ cancelled
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/inbound-orders | 入库单列表 |
| POST | /admin/inbound-orders | 创建入库单 |
| GET | /admin/inbound-orders/{id} | 入库单详情 |
| PUT | /admin/inbound-orders/{id} | 更新入库单 |
| DELETE | /admin/inbound-orders/{id} | 删除入库单 |

## 相关文件

- Model: `backend/app/models/inbound_order.py`
- API: `backend/app/api/inbound_orders.py`
- Frontend: `frontend/src/app/admin/inbound-orders/`
