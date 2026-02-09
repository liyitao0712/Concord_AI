# Warehouse 仓库

## 概述

Warehouse 是仓库实体，用于管理自有仓库、租赁仓库、保税仓等。仓库下挂载库存记录（Inventory）。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| code | String(30) | 仓库编码（唯一） |
| name | String(100) | 仓库名称 |
| address | String(300) | 地址 |
| contact_person | String(50) | 联系人 |
| contact_phone | String(50) | 联系电话 |
| warehouse_type | String(20) | 类型 (own/rented/bonded/virtual) |
| is_active | Boolean | 是否启用 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 仓库类型

| 值 | 说明 |
|-----|------|
| own | 自有仓库 |
| rented | 租赁仓库 |
| bonded | 保税仓 |
| virtual | 虚拟仓（在途库存等） |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/warehouses | 仓库列表 |
| POST | /admin/warehouses | 创建仓库 |
| GET | /admin/warehouses/{id} | 仓库详情 |
| PUT | /admin/warehouses/{id} | 更新仓库 |
| DELETE | /admin/warehouses/{id} | 删除仓库 |

## 相关文件

- Model: `backend/app/models/warehouse.py`
- Schema: `backend/app/schemas/warehouse.py`
- API: `backend/app/api/warehouses.py`
- Frontend: `frontend/src/app/admin/warehouses/`
