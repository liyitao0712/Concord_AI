# EmailAnalysis 邮件分析结果

## 概述

EmailAnalysis 存储 EmailSummarizerAgent 对邮件的 AI 分析结果，包括摘要、意图、发件方信息、产品、金额等业务信息。每封邮件可有多条分析记录（重新分析时生成新记录）。

## 数据模型

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| email_id | String(36) | 关联邮件 ID（外键） |
| summary | Text | 一句话摘要（中文） |
| broadcast | String(500) | 一句话播报（中文，≤50字） |
| key_points | JSON | 关键要点列表 |
| original_language | String(10) | 原文语言 (en/zh/es/ar 等) |
| sender_type | String(20) | 发件方类型 (customer/supplier/freight/bank/other) |
| sender_company | String(255) | 公司名称 |
| sender_country | String(50) | 国家/地区 |
| is_new_contact | Boolean | 是否新联系人 |
| intent | String(50) | 主意图 (inquiry/quotation/order 等) |
| intent_confidence | Float | 意图置信度 0-1 |
| urgency | String(20) | 紧急程度 (urgent/high/medium/low) |
| sentiment | String(20) | 情感倾向 (positive/neutral/negative) |
| products | JSON | 产品列表 [{name, specs, quantity, unit, target_price}] |
| amounts | JSON | 金额列表 [{value, currency, context}] |
| deadline | DateTime | 截止/交期要求 |
| questions | JSON | 对方提出的问题列表 |
| action_required | JSON | 需要我方做的事情列表 |
| suggested_reply | Text | 建议回复要点 |
| priority | String(10) | 处理优先级 (p0/p1/p2/p3) |
| cleaned_content | Text | 清洗后的邮件正文 |
| llm_model | String(100) | 使用的 LLM 模型 |
| token_used | Integer | 消耗的 token 数 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /admin/emails/{id}/ai-analyze | AI 分析邮件 |
| GET | /admin/emails/{id}/analysis | 获取已有分析结果 |
| GET | /admin/emails/today-briefing | 当日邮件播报 |

## 相关文件

- Model: `backend/app/models/email_analysis.py`
- API: `backend/app/api/emails.py`
- Agent: `backend/app/agents/email_summarizer.py`
- Prompt: `backend/app/llm/prompts/defaults.py` (email_summarizer)
