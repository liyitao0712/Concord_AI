# Intent 意图

## 概述

Intent 是意图定义实体，用于管理系统支持的意图类型和对应的处理规则。

## 数据模型

### Intent（意图定义）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| code | String(50) | 意图代码（唯一） |
| name | String(100) | 中文名称 |
| description | Text | 描述 |
| category | String(50) | 分类 |
| priority | Integer | 优先级 |
| examples | JSON | 示例列表 |
| keywords | JSON | 关键词列表 |
| is_active | Boolean | 是否启用 |
| is_system | Boolean | 是否系统内置 |
| created_at | DateTime | 创建时间 |

### IntentSuggestion（AI 建议）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| suggested_code | String(50) | 建议代码 |
| suggested_name | String(100) | 建议名称 |
| confidence | Float | 置信度 |
| reasoning | Text | 推理说明 |
| status | String(20) | pending/approved/rejected |
| created_at | DateTime | 创建时间 |

## 内置意图

| Code | Name |
|------|------|
| inquiry | 询价/询盘 |
| quotation | 报价/还价 |
| order | 下单/订单确认 |
| order_change | 订单修改/取消 |
| payment | 付款/汇款通知 |
| shipment | 发货/物流跟踪 |
| sample | 样品请求 |
| complaint | 投诉/质量问题 |
| after_sales | 售后服务 |
| negotiation | 价格谈判 |
| follow_up | 跟进/催促 |
| introduction | 公司/产品介绍 |
| general | 一般沟通 |
| spam | 垃圾邮件/营销 |
| other | 其他 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /admin/intents | 意图列表 |
| POST | /admin/intents | 创建意图 |
| PUT | /admin/intents/{id} | 更新意图 |
| DELETE | /admin/intents/{id} | 删除意图 |

## 相关文件

- Model: `backend/app/models/intent.py`
- API: `backend/app/api/intents.py`
