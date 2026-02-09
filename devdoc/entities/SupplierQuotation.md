# SupplierQuotation 供应商报价单

## 概述

SupplierQuotation 是供应商报价单实体，记录供应商给我们的报价信息。可从供应商询价单（SupplierRFQ）流转而来，并可进一步流转为采购合同（PurchaseContract）。SupplierQuotationLine 是报价单中的产品明细行。

## 数据模型

### 基本信息

| 项目 | 值 |
|------|------|
| 数据表名 | `supplier_quotations` |
| 模型路径 | `backend/app/models/supplier_quotation.py` |
| Schema 路径 | `backend/app/schemas/supplier_quotation.py` |

### 状态流转

```
draft → received → reviewing → accepted / rejected / expired
任何状态均可 → cancelled
```

### SupplierQuotation（供应商报价单）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| quotation_no | String(50) | 报价单编号（唯一） |
| supplier_id | String(36) | 供应商 ID（外键 → suppliers） |
| contact_id | String(36) | 供应商联系人 ID（外键 → supplier_contacts） |
| linked_supplier_rfq_id | String(36) | 来源供应商询价单 ID（外键 → supplier_rfqs） |
| trade_term | String(20) | 贸易术语（FOB/CIF 等） |
| payment_method | String(50) | 付款方式 |
| payment_terms | Text | 付款条款详细描述 |
| currency | String(10) | 币种，默认 USD |
| exchange_rate | Numeric(12,6) | 汇率 |
| subtotal | Numeric(14,2) | 小计（明细行合计） |
| discount_amount | Numeric(14,2) | 整单折扣金额 |
| tax_amount | Numeric(14,2) | 税额 |
| total_amount | Numeric(14,2) | 总金额 |
| port_of_loading | String(100) | 装运港 |
| port_of_discharge | String(100) | 目的港 |
| quotation_date | Date | 报价日期 |
| valid_until | Date | 报价有效期 |
| status | String(20) | 状态: draft/received/reviewing/accepted/rejected/expired/cancelled |
| notes | Text | 备注 |
| attachments | JSON | 附件列表 [{name, key, storage_type}] |
| tags | JSON | 标签列表 |
| created_by | String(36) | 创建人 ID（外键 → users） |
| org_id | String(36) | 所属组织（外键 → organizations） |
| owner_id | String(36) | 负责人（外键 → users） |
| owner_dept_id | String(36) | 负责人部门（外键 → departments） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### SupplierQuotationLine（供应商报价单明细）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| supplier_quotation_id | String(36) | 供应商报价单 ID（外键 → supplier_quotations） |
| line_no | Integer | 行号（报价单内排序） |
| product_id | String(36) | 产品 ID（外键 → products） |
| product_name | String(200) | 品名（冗余） |
| specifications | Text | 规格 |
| unit | String(50) | 单位 |
| quantity | Numeric(14,4) | 数量 |
| unit_price | Numeric(14,4) | 单价 |
| discount_rate | Numeric(5,2) | 折扣率 % |
| discount_amount | Numeric(14,2) | 折扣金额 |
| tax_rate | Numeric(5,2) | 税率 % |
| tax_amount | Numeric(14,2) | 税额 |
| amount | Numeric(14,2) | 金额（数量 x 单价 - 折扣） |
| amount_with_tax | Numeric(14,2) | 含税金额 |
| hs_code | String(20) | HS 编码 |
| notes | Text | 备注 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 关系

- **Supplier**: 多对一，每个报价单属于一个供应商
- **SupplierContact**: 多对一，可选关联供应商联系人
- **SupplierRFQ**: 多对一，可选关联来源询价单
- **SupplierQuotationLine**: 一对多，包含多个明细行（级联删除）
- **Product**: 明细行通过 product_id 关联产品

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/supplier-quotations | 报价单列表（分页、搜索） |
| POST | /admin/supplier-quotations | 创建报价单 |
| GET | /admin/supplier-quotations/{quotation_id} | 报价单详情 |
| PUT | /admin/supplier-quotations/{quotation_id} | 更新报价单 |
| DELETE | /admin/supplier-quotations/{quotation_id} | 删除报价单 |
| PUT | /admin/supplier-quotations/{quotation_id}/status | 更新状态 |
| PUT | /admin/supplier-quotations/{quotation_id}/lines | 批量更新明细行 |

## 相关文件

- Model: `backend/app/models/supplier_quotation.py`
- Schema: `backend/app/schemas/supplier_quotation.py`
- API: `backend/app/api/supplier_quotations.py`
- Frontend: `frontend/src/app/admin/supplier-quotations/page.tsx`
