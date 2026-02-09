# Inventory 库存

## 概述

Inventory 是库存实体，记录某个仓库中某个产品的实际库存量和预留量。通过 (warehouse_id, product_id) 唯一约束，每个仓库的每个产品只有一条库存记录。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| warehouse_id | String(36) | 仓库 ID（外键） |
| product_id | String(36) | 产品 ID（外键） |
| quantity | Numeric(14,4) | 实际库存量 |
| reserved_quantity | Numeric(14,4) | 预留量（销售合同锁定） |
| unit | String(50) | 单位 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**唯一约束**: (warehouse_id, product_id)

## 库存变动

- **入库**：InboundOrder 确认收货时增加 quantity
- **出库**：OutboundOrder 确认发货时减少 quantity
- **预留**：SalesContract 审批通过时增加 reserved_quantity
- **可用量** = quantity - reserved_quantity

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/inventories | 库存列表（按仓库、产品筛选） |
| GET | /admin/inventories/{id} | 库存详情 |

## 相关文件

- Model: `backend/app/models/inventory.py`
- Schema: `backend/app/schemas/inventory.py`
- Service: `backend/app/services/inventory_service.py`
- API: `backend/app/api/inventories.py`
