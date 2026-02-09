# Concord AI - 文档中心

> AI 中台系统技术文档，基于 FastAPI + Next.js + Temporal + Celery + LangGraph 构建。

## 快速导航

| 文档 | 说明 |
|------|------|
| [系统架构概览](./architecture/SYSTEM_OVERVIEW.md) | 整体架构、技术栈、部署拓扑 |
| [后端开发手册](./guides/BACKEND_HANDBOOK.md) | FastAPI + SQLAlchemy 开发规范 |
| [前端开发手册](./guides/FRONTEND_HANDBOOK.md) | Next.js + TypeScript 开发规范 |
| [开发日志](./DEVELOPMENT_LOG.md) | 迭代记录、待改进汇总 |

---

## 架构文档 (`architecture/`)

系统顶层设计与核心架构说明。

| 文档 | 说明 |
|------|------|
| [SYSTEM_OVERVIEW.md](./architecture/SYSTEM_OVERVIEW.md) | 系统整体架构、模块划分、部署拓扑 |
| [AI_FRAMEWORK.md](./architecture/AI_FRAMEWORK.md) | AI 框架设计：LangGraph Agent + LiteLLM + Prompt 管理 |
| [BUSINESS_FLOWS.md](./architecture/BUSINESS_FLOWS.md) | 核心业务流程：邮件处理、客户管理、合同流转 |
| [PERMISSION_SYSTEM.md](./architecture/PERMISSION_SYSTEM.md) | 权限系统设计：角色、部门、数据权限 |
| [EMAIL_PIPELINE.md](./architecture/EMAIL_PIPELINE.md) | 邮件处理管线：收取、解析、AI 分析、通知 |

---

## 开发手册 (`guides/`)

面向开发者的实操指南。

| 文档 | 说明 |
|------|------|
| [BACKEND_HANDBOOK.md](./guides/BACKEND_HANDBOOK.md) | 后端开发规范：API 设计、ORM 用法、错误处理 |
| [FRONTEND_HANDBOOK.md](./guides/FRONTEND_HANDBOOK.md) | 前端开发规范：组件结构、状态管理、API 调用 |
| [LLM_GUIDE.md](./guides/LLM_GUIDE.md) | LLM 集成指南：LiteLLM 配置、Prompt 模板、模型切换 |
| [CELERY_GUIDE.md](./guides/CELERY_GUIDE.md) | Celery 任务指南：异步任务、定时调度、Event Loop 陷阱 |
| [TEMPORAL_GUIDE.md](./guides/TEMPORAL_GUIDE.md) | Temporal 工作流指南：Workflow/Activity 开发、部署 |
| [OPS_SCRIPTS.md](./guides/OPS_SCRIPTS.md) | 运维脚本说明：setup、restart、数据库迁移 |

---

## Agent 文档 (`agents/`)

系统中所有 AI Agent 的详细说明，参见 [agents/README.md](./agents/README.md)。

| Agent | 说明 | 文档 |
|-------|------|------|
| EmailSummarizer | 邮件摘要与意图分析 | [EmailSummarizer.md](./agents/EmailSummarizer.md) |
| WorkTypeAnalyzer | 工作类型自动分类 | [WorkTypeAnalyzer.md](./agents/WorkTypeAnalyzer.md) |
| ChatAgent | 聊天对话（带工具调用） | [ChatAgent.md](./agents/ChatAgent.md) |
| CustomerExtractor | 客户信息提取 | [CustomerExtractor.md](./agents/CustomerExtractor.md) |
| AddNewClientHelper | 新客户录入辅助 | [AddNewClientHelper.md](./agents/AddNewClientHelper.md) |
| AddNewSupplierHelper | 新供应商录入辅助 | [AddNewSupplierHelper.md](./agents/AddNewSupplierHelper.md) |

---

## 数据实体 (`entities/`)

所有数据库模型的字段定义与关系说明，参见 [entities/README.md](./entities/README.md)。

涵盖：Customer、Supplier、Product、EmailAnalysis、PurchaseContract、SalesContract、Inventory、Warehouse 等 20+ 实体。

---

## Temporal 工作流 (`temporal-workflows/`)

Temporal 工作流定义与说明，参见 [temporal-workflows/README.md](./temporal-workflows/README.md)。

| 工作流 | 说明 |
|--------|------|
| [WorkTypeSuggestionWorkflow](./temporal-workflows/WorkTypeSuggestionWorkflow.md) | 工作类型建议工作流 |

---

## 参考资料 (`reference/`)

| 文档 | 说明 |
|------|------|
| [VERSION_MANIFEST.md](./reference/VERSION_MANIFEST.md) | 依赖版本清单：Python/Node 包版本锁定 |
| [EMAIL_ACCOUNT_CASCADE_DELETE.md](./reference/EMAIL_ACCOUNT_CASCADE_DELETE.md) | 邮箱账户级联删除方案 |

---

## 归档 (`archive/`)

早期文档已归档至 `archive/` 目录，包括：

- `FINAL_TECHNICAL_SPEC.md` - 初版技术规格（已拆分至 architecture/）
- `MVP_DEVELOPMENT_PLAN.md` - MVP 开发计划（已完成）
- `DEV_PROMPT.md` - 早期开发提示词
- `PROMPT_SYSTEM_MIGRATION.md` - Prompt 系统迁移记录
- `prompts/` - 早期 Prompt 模板文档（已迁移至代码）

> 归档文件仅供历史参考，不再维护更新。

---

## 开发日志

[DEVELOPMENT_LOG.md](./DEVELOPMENT_LOG.md) - 记录每次迭代的开发内容、技术决策和待改进事项。

---

## Prompt 模板

Prompt 模板以代码为准，不再维护独立文档：

- 默认模板定义: `backend/app/llm/prompts/defaults.py`
- Prompt 管理器: `backend/app/llm/prompts/manager.py`（DB 优先 + defaults.py 回退，5 分钟缓存）
- 数据库可在线编辑覆盖默认模板（管理后台 -> Prompt 管理）
