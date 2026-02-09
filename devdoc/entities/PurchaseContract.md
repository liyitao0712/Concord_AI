# PurchaseContract 采购合同

## 概述

PurchaseContract 是采购合同实体，记录与供应商签订的采购合同。PurchaseLine 是合同明细行。可与销售合同关联实现背对背采购。

## 数据模型

### PurchaseContract（采购合同）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| contract_no | String(50) | 合同编号（唯一） |
| supplier_id | String(36) | 供应商 ID（外键） |
| contact_id | String(36) | 供应商联系人 ID（外键） |
| trade_term | String(20) | 贸易术语 (FOB/CIF 等) |
| payment_method | String(50) | 付款方式 |
| payment_terms | Text | 付款条款详细描述 |
| currency | String(10) | 币种（默认 USD） |
| exchange_rate | Numeric(12,6) | 汇率 |
| subtotal | Numeric(14,2) | 小计 |
| discount_amount | Numeric(14,2) | 折扣金额 |
| tax_amount | Numeric(14,2) | 税额 |
| total_amount | Numeric(14,2) | 总金额 |
| port_of_loading | String(100) | 装货港 |
| port_of_discharge | String(100) | 卸货港 |
| contract_date | Date | 签约日期 |
| delivery_date | Date | 交货日期 |
| expected_arrival_date | Date | 预计到货日期 |
| expiry_date | Date | 合同有效期 |
| status | String(20) | 合同状态 |
| notes | Text | 备注 |
| attachments | JSON | 附件列表 |
| tags | JSON | 标签列表 |
| created_by | String(36) | 创建人 ID（外键） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### PurchaseLine（合同明细行）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| purchase_contract_id | String(36) | 采购合同 ID（外键） |
| line_no | Integer | 行号 |
| product_id | String(36) | 产品 ID（外键） |
| product_name | String(200) | 产品名称（快照） |
| specifications | Text | 规格参数 |
| unit | String(50) | 单位 |
| quantity | Numeric(14,4) | 数量 |
| unit_price | Numeric(14,4) | 单价 |
| discount_rate | Numeric(5,2) | 折扣率 |
| discount_amount | Numeric(14,2) | 折扣额 |
| tax_rate | Numeric(5,2) | 税率 |
| tax_amount | Numeric(14,2) | 税额 |
| amount | Numeric(14,2) | 金额 |
| amount_with_tax | Numeric(14,2) | 含税金额 |
| received_quantity | Numeric(14,4) | 已收货数量 |
| hs_code | String(20) | HS 编码 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 状态流转

```
draft → pending_approval → approved → signed → in_progress → partial_received → received → completed
                                                                                      ↘ cancelled
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/purchase-contracts | 合同列表 |
| POST | /admin/purchase-contracts | 创建合同 |
| GET | /admin/purchase-contracts/{id} | 合同详情 |
| PUT | /admin/purchase-contracts/{id} | 更新合同 |
| DELETE | /admin/purchase-contracts/{id} | 删除合同 |

## 相关文件

- Model: `backend/app/models/purchase_contract.py`
- Schema: `backend/app/schemas/purchase_contract.py`
- API: `backend/app/api/purchase_contracts.py`
- Frontend: `frontend/src/app/admin/purchase-contracts/`
