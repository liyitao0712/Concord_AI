# OutboundOrder 出库单

## 概述

OutboundOrder 是出库单实体，记录货物出库操作。通常关联销售合同，出库确认后扣减库存。OutboundLine 是出库明细行。

## 数据模型

### OutboundOrder（出库单）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| order_no | String(50) | 出库单号（唯一） |
| warehouse_id | String(36) | 仓库 ID（外键） |
| sales_contract_id | String(36) | 关联销售合同 ID（外键） |
| customer_id | String(36) | 客户 ID（外键） |
| status | String(20) | 状态 |
| expected_date | Date | 预计发货日期 |
| actual_date | Date | 实际发货日期 |
| notes | Text | 备注 |
| created_by | String(36) | 创建人 ID（外键） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### OutboundLine（出库明细行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| outbound_order_id | String(36) | 出库单 ID（外键） |
| product_id | String(36) | 产品 ID（外键） |
| sales_line_id | String(36) | 关联销售合同行 ID（外键） |
| quantity | Numeric(14,4) | 计划数量 |
| shipped_quantity | Numeric(14,4) | 实发数量 |
| unit | String(50) | 单位 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 状态流转

```
draft → confirmed → partial_shipped → shipped
                                   ↘ cancelled
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/outbound-orders | 出库单列表 |
| POST | /admin/outbound-orders | 创建出库单 |
| GET | /admin/outbound-orders/{id} | 出库单详情 |
| PUT | /admin/outbound-orders/{id} | 更新出库单 |
| DELETE | /admin/outbound-orders/{id} | 删除出库单 |

## 相关文件

- Model: `backend/app/models/outbound_order.py`
- API: `backend/app/api/outbound_orders.py`
- Frontend: `frontend/src/app/admin/outbound-orders/`
