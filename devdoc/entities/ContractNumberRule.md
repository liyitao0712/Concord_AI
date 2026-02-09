# ContractNumberRule 合同编号规则

## 概述

ContractNumberRule 是合同自动编号规则实体，用于生成销售合同、采购合同等的流水号。按日期重置序号，支持自定义前缀、日期格式和序号长度。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| rule_type | String(30) | 规则类型（唯一，如 sales_contract、purchase_contract） |
| prefix | String(20) | 前缀（如 SC、PC） |
| date_format | String(20) | 日期格式（默认 %Y%m%d） |
| separator | String(5) | 分隔符（默认 "-"） |
| sequence_length | Integer | 序号位数（默认 3） |
| current_sequence | Integer | 当前序号 |
| last_date | String(20) | 上次生成日期（用于判断是否重置） |
| is_active | Boolean | 是否启用 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## 编号格式示例

```
前缀 + 分隔符 + 日期 + 分隔符 + 序号
SC-20260208-001    （销售合同）
PC-20260208-001    （采购合同）
IN-20260208-001    （入库单）
OUT-20260208-001   （出库单）
```

## 相关文件

- Model: `backend/app/models/contract_number_rule.py`
- Schema: `backend/app/schemas/contract_number_rule.py`
- Service: `backend/app/services/contract_number.py`
- API: `backend/app/api/contract_numbers.py`
