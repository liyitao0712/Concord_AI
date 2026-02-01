# Concord AI - 业务流程

> 记录业务需求和处理流程，作为开发实施的依据

---

## 公司背景

- **行业**：工具出口外贸
- **产品**：装修工具（putty knives, taping knives 等）
- **客户**：美国等海外客户（如 Hyde Tools）
- **团队**：约 10+ 人

---

## 核心理念

> **先看懂，再处理**

邮件处理分两个阶段：
1. **分析阶段**：把邮件"读完"，提取关键信息，存储分析结果
2. **处理阶段**：基于分析结果，触发后续业务流程（人工或自动）

```
┌─────────────────────────────────────────────────────────────────┐
│                     阶段一：邮件分析                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   收到邮件 → 提取信息 → AI 分析 → 存储结果 → 可供查看           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    [人查看 / 系统自动决策]
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     阶段二：业务处理（后续）                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   询价 → 生成报价                                               │
│   订单 → 创建订单                                               │
│   催单 → 查询物流                                               │
│   ...                                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 阶段一：邮件分析工作流

### 目标

收到邮件后，自动完成分析，将结果存入数据库，供人查看或后续流程使用。

### 分析结果应包含

| 字段 | 说明 | 示例 |
|------|------|------|
| `summary` | 邮件摘要（1-2句话） | "客户询问 putty knife 100pcs 的价格" |
| `intent` | 意图分类 | inquiry / follow_up / order / complaint / info / other |
| `urgency` | 紧急程度 | high / medium / low |
| `sentiment` | 情感倾向 | positive / neutral / negative |
| `action_required` | 是否需要回复 | true / false |
| `key_points` | 关键信息提取 | ["产品: putty knife", "数量: 100pcs", "交期: ASAP"] |
| `entities` | 结构化实体 | {product: "...", quantity: 100, customer: "..."} |
| `suggested_reply` | 建议回复（可选） | "感谢询价，报价如下..." |
| `related_threads` | 关联邮件线程 | 同一客户的历史邮件 |

---

## 可配置项详解

### 1. 分析字段（用户可自定义）

存储在 `analysis_fields` 表，定义分析结果包含哪些字段。

**系统预设字段：**

| 字段名 | 类型 | 说明 | 必填 |
|--------|------|------|------|
| `summary` | string | 邮件摘要（1-2句话） | 是 |
| `intent` | enum | 意图分类 | 是 |
| `urgency` | enum | 紧急程度 (high/medium/low) | 是 |
| `action_required` | bool | 是否需要回复 | 是 |
| `sentiment` | enum | 情感倾向 (positive/neutral/negative) | 否 |
| `key_points` | array | 关键信息列表 | 是 |
| `entities` | object | 结构化实体提取 | 是 |

**用户自定义字段示例：**

| 字段名 | 类型 | 说明 | Prompt 描述 |
|--------|------|------|-------------|
| `is_new_customer` | bool | 是否新客户 | "判断发件人是否为新客户（首次联系）" |
| `product_category` | enum | 产品类别 | "提取涉及的产品类别：hand_tools/power_tools/accessories/other" |
| `has_attachment` | bool | 是否有附件 | "检查邮件是否包含附件" |
| `language` | string | 邮件语言 | "识别邮件的主要语言" |
| `quote_request` | bool | 是否询价 | "判断是否在询问价格或要求报价" |

**数据表设计：**

```sql
CREATE TABLE analysis_fields (
    id SERIAL PRIMARY KEY,
    field_name VARCHAR(50) NOT NULL UNIQUE,
    field_type VARCHAR(20) NOT NULL,  -- string/bool/enum/array/object
    display_name VARCHAR(100),         -- 显示名称
    description TEXT,                  -- 给 LLM 的提取说明
    enum_values JSONB,                 -- 如果是 enum 类型，可选值
    is_required BOOLEAN DEFAULT false,
    is_system BOOLEAN DEFAULT false,   -- 系统预设 vs 用户自定义
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 2. 分析 Prompt（用户可自定义）

存储在 `prompts` 表，`prompt_name = 'email_analyzer'`。

**默认 Prompt 结构：**

```
你是一个专业的邮件分析助手。请仔细阅读以下邮件，提取关键信息。

## 需要分析的字段

{动态生成：根据 analysis_fields 表}

### summary (摘要)
用1-2句话概括邮件的主要内容。

### intent (意图)
判断邮件意图，必须是以下之一：inquiry/order/complaint/follow_up/info/other

### urgency (紧急程度)
...

{用户自定义字段也会动态加入}

## 输出格式

请以 JSON 格式返回分析结果。
```

**Prompt 可配置部分：**

| 部分 | 可否自定义 | 说明 |
|------|-----------|------|
| 系统角色描述 | ✅ | 可以调整 AI 的角色定位 |
| 字段列表 | ✅ | 从 analysis_fields 动态生成 |
| 各字段的提取说明 | ✅ | 每个字段的 description |
| 输出格式要求 | ⚠️ | 建议保持 JSON，但可微调 |
| 示例 | ✅ | 可添加 few-shot 示例 |

---

### 3. 路由规则（用户可自定义）

存储在 `routing_rules` 表，定义"什么条件触发什么工作流"。

**规则结构：**

```json
{
  "rule_name": "紧急投诉处理",
  "priority": 100,
  "conditions": {
    "AND": [
      {"field": "intent", "op": "eq", "value": "complaint"},
      {"field": "urgency", "op": "eq", "value": "high"}
    ]
  },
  "actions": [
    {"type": "workflow", "workflow_id": "urgent_notification"},
    {"type": "workflow", "workflow_id": "complaint_handler"},
    {"type": "tag", "tag": "urgent"}
  ],
  "stop_processing": false
}
```

**支持的条件操作符：**

| 操作符 | 说明 | 示例 |
|--------|------|------|
| `eq` | 等于 | `{"field": "intent", "op": "eq", "value": "inquiry"}` |
| `ne` | 不等于 | `{"field": "urgency", "op": "ne", "value": "low"}` |
| `in` | 在列表中 | `{"field": "intent", "op": "in", "value": ["inquiry", "order"]}` |
| `contains` | 包含（字符串/数组） | `{"field": "key_points", "op": "contains", "value": "价格"}` |
| `exists` | 字段存在且非空 | `{"field": "entities.product", "op": "exists"}` |
| `gt/lt/gte/lte` | 数值比较 | `{"field": "entities.quantity", "op": "gt", "value": 100}` |

**支持的动作类型：**

| 动作类型 | 说明 |
|---------|------|
| `workflow` | 触发指定的 Temporal Workflow |
| `agent` | 调用指定的 Agent |
| `notify` | 发送通知（邮件/飞书/...） |
| `tag` | 添加标签 |
| `assign` | 分配给指定人员 |
| `queue` | 放入人工处理队列 |

**数据表设计：**

```sql
CREATE TABLE routing_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 0,        -- 数字越大优先级越高
    conditions JSONB NOT NULL,         -- 条件表达式
    actions JSONB NOT NULL,            -- 触发的动作列表
    stop_processing BOOLEAN DEFAULT false,  -- 匹配后是否停止后续规则
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### 4. Agent Prompt（用户可自定义）

存储在 `prompts` 表，每个 Agent 对应一条记录。

| prompt_name | 用途 |
|-------------|------|
| `email_analyzer` | 邮件分析 |
| `intent_classifier` | 意图分类（可能合并到 email_analyzer） |
| `quote_agent` | 报价生成 |
| `chat_agent` | 对话助手 |
| `summary_agent` | 摘要生成 |

---

## 系统处理流程（完整版）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. 数据采集                                                                 │
│    Email Worker / Feishu Worker / API                                       │
│    → 原始数据存入 email_raw_messages / events                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. AI 分析（Analysis Agent）                                                │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │ 读取配置：                                                          │  │
│    │   • analysis_fields 表 → 需要分析哪些字段                           │  │
│    │   • prompts 表 → 分析用的 Prompt                                    │  │
│    │                                                                     │  │
│    │ 调用 LLM：                                                          │  │
│    │   • 输入：邮件原文 + 动态 Prompt                                    │  │
│    │   • 输出：JSON 格式的分析结果                                       │  │
│    │                                                                     │  │
│    │ 保存结果：                                                          │  │
│    │   • event_analysis 表（或 events.analysis_result 字段）             │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. 规则匹配（Rule Engine）                                                  │
│    ┌─────────────────────────────────────────────────────────────────────┐  │
│    │ 读取配置：                                                          │  │
│    │   • routing_rules 表 → 所有激活的规则（按优先级排序）                │  │
│    │                                                                     │  │
│    │ 匹配逻辑：                                                          │  │
│    │   FOR each rule in rules:                                          │  │
│    │       IF evaluate(rule.conditions, analysis_result):               │  │
│    │           执行 rule.actions                                         │  │
│    │           IF rule.stop_processing: BREAK                           │  │
│    │                                                                     │  │
│    │ 兜底规则：                                                          │  │
│    │   • 如果没有任何规则匹配 → 进入人工处理队列                          │  │
│    └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. 执行动作（Temporal Workflows / Agents）                                  │
│    • 并行或串行执行规则匹配到的动作                                         │
│    • 每个 Workflow/Agent 可以有自己的 Prompt 配置                           │
│    • 执行结果更新回 events 表                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. 结果存储 & 人工审核                                                      │
│    • 分析结果、执行结果存入数据库                                           │
│    • 需要人工审核的进入审核队列                                             │
│    • 管理后台可查看所有处理记录                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 阶段二：业务处理（后续实现）

> 等阶段一（AI 分析 + 规则引擎）完成后再规划

### 询价处理 (Inquiry)
- TODO

### 跟进处理 (Follow-up)
- TODO

### 订单处理 (Order)
- TODO

### 投诉处理 (Complaint)
- TODO

---

## 讨论记录

> 按日期记录业务讨论内容

### 2026-01-31

（待记录）

---

## 实施优先级

| 优先级 | 流程 | 原因 |
|--------|------|------|
| P0 | ? | ? |
| P1 | ? | ? |
| P2 | ? | ? |

---

## 关联文档

- [系统架构](./ARCHITECTURE.md)
- [开发日志](./DEVELOPMENT_LOG.md)
