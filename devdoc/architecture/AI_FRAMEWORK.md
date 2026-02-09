# Concord AI - AI 框架架构图

> 最后更新: 2026-02-07

## AI 技术框架总览

| 层级 | 技术 | 用途 |
|------|------|------|
| **LLM 网关** | LiteLLM | 统一多模型 API（Claude / GPT / Gemini / Qwen / 火山引擎） |
| **Agent 引擎** | LangGraph | 基于 StateGraph 的 Agent 执行图（think → tools → output） |
| **工作流编排** | Temporal | 长时间审批流程（工作类型建议 7 天审批） |
| **任务队列** | Celery + Redis | 邮件轮询、定时任务、异步处理 |
| **Prompt 管理** | 自研 PromptManager | 数据库优先 + defaults.py 回退，支持变量渲染 |
| **Tool 框架** | 自研 @tool 装饰器 | 自动生成 OpenAI/Anthropic Function Calling Schema |

---

## 现有 Agent 一览

| Agent | 文件 | 用途 | 工具 |
|-------|------|------|------|
| **ChatAgent** | `agents/chat_agent.py` | 通用多轮对话，Redis 维护会话上下文 | 可选启用 |
| **EmailSummarizerAgent** | `agents/email_summarizer.py` | 邮件摘要分析（意图/产品/金额/情绪） | `clean_email` |
| **WorkTypeAnalyzerAgent** | `agents/work_type_analyzer.py` | 邮件工作类型匹配/建议新类型 | 无 |

---

## Agent 关联框架图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        用户 / 前端 (Next.js)                         │
└──────────────┬──────────────────────────────────┬───────────────────┘
               │ REST API                         │ WebSocket/Stream
               ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       FastAPI 后端 (main.py)                         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    AgentRegistry (单例)                       │   │
│  │  ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐  │   │
│  │  │  ChatAgent   │  │EmailSummarizer   │  │WorkTypeAnalyzer│  │   │
│  │  │  (多轮对话)   │  │Agent (邮件摘要)   │  │Agent (类型匹配) │  │   │
│  │  └──────┬──────┘  └────────┬─────────┘  └───────┬────────┘  │   │
│  └─────────┼──────────────────┼─────────────────────┼──────────┘   │
│            │                  │                     │               │
│  ┌─────────▼──────────────────▼─────────────────────▼──────────┐   │
│  │              BaseAgent (LangGraph StateGraph)                │   │
│  │                                                              │   │
│  │   ┌───────┐    ┌──────────────────┐    ┌────────┐           │   │
│  │   │ think │───▶│should_exec_tools?│───▶│ output │──▶ END    │   │
│  │   └───┬───┘    └────────┬─────────┘    └────────┘           │   │
│  │       ▲                 │ yes                                │   │
│  │       │          ┌──────▼───────┐                            │   │
│  │       └──────────│execute_tools │                            │   │
│  │                  └──────────────┘                            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│            │                  │                     │               │
│  ┌─────────▼──────────────────▼─────────────────────▼──────────┐   │
│  │                     共享基础设施                               │   │
│  │                                                              │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐ │   │
│  │  │ LLMGateway │  │ToolRegistry  │  │  PromptManager       │ │   │
│  │  │ (LiteLLM)  │  │(@tool 装饰器) │  │  (DB + 缓存 + 回退)  │ │   │
│  │  └─────┬──────┘  └──────┬───────┘  └──────────────────────┘ │   │
│  │        │                │                                    │   │
│  │        ▼                ▼                                    │   │
│  │  ┌──────────┐   ┌──────────────────────────────────────┐    │   │
│  │  │ 多模型    │   │ Tools:                                │    │   │
│  │  │ ├ Claude  │   │ ├ EmailCleanerTool (邮件清洗)         │    │   │
│  │  │ ├ GPT-4   │   │ ├ DatabaseTool    (数据库查询)        │    │   │
│  │  │ ├ Gemini  │   │ ├ EmailTool       (收发邮件)          │    │   │
│  │  │ ├ Qwen    │   │ ├ HTTPTool        (HTTP 请求)         │    │   │
│  │  │ └ 火山引擎 │   │ ├ FileTool        (文件操作)          │    │   │
│  │  └──────────┘   │ └ PDFTool         (PDF 生成)          │    │   │
│  │                  └──────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                      异步任务 & 工作流层                              │
│                                                                      │
│  ┌─────────── Celery (Redis Broker) ────────────┐                   │
│  │                                               │                   │
│  │  [email 队列]              [workflow 队列]      │                   │
│  │  ├ poll_email_account     ├ process_workflow  │                   │
│  │  └ process_email ─────────┤                   │                   │
│  │         │                 │                   │                   │
│  │         ▼                 │                   │                   │
│  │  ┌──────────────┐        │                   │                   │
│  │  │运行 Agent:    │        │                   │                   │
│  │  │├ EmailSumma-  │        │                   │                   │
│  │  ││  rizerAgent  │        │                   │                   │
│  │  │└ WorkType-    │        │                   │                   │
│  │  │   Analyzer    │────────┘                   │                   │
│  │  └──────┬───────┘                             │                   │
│  └─────────┼─────────────────────────────────────┘                   │
│            │ 建议新类型时                                             │
│            ▼                                                         │
│  ┌─────────── Temporal ─────────────────────────┐                   │
│  │  WorkTypeSuggestionWorkflow                   │                   │
│  │                                               │                   │
│  │  notify_admin ──▶ 等待审批信号 (7天超时)        │                   │
│  │                    ├─ approve ──▶ 创建 WorkType │                   │
│  │                    ├─ reject  ──▶ 标记拒绝      │                   │
│  │                    └─ timeout ──▶ 自动拒绝      │                   │
│  └───────────────────────────────────────────────┘                   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                         数据 & 存储层                                 │
│  ┌────────────┐  ┌───────────┐  ┌──────────────────────────────┐    │
│  │ PostgreSQL │  │   Redis   │  │      IMAP 邮件服务器          │    │
│  │ (SQLAlchemy│  │ • Broker  │  │  (轮询获取新邮件)              │    │
│  │  AsyncIO)  │  │ • Cache   │  └──────────────────────────────┘    │
│  │            │  │ • Session │                                      │
│  └────────────┘  └───────────┘                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 核心执行流程（邮件处理）

```
Celery 定时任务 (每5分钟)
    │
    ▼
poll_email_account → IMAP 拉取新邮件
    │
    ▼
process_email (Celery Task)
    │
    ├──▶ EmailSummarizerAgent.analyze()
    │       ├─ clean_email (工具调用)
    │       ├─ LLM 分析 → 摘要/意图/产品/金额/情绪
    │       └─ 返回结构化 JSON
    │
    └──▶ WorkTypeAnalyzerAgent.analyze()
            ├─ 从 DB 加载现有工作类型
            ├─ LLM 匹配或建议新类型
            └─ 若建议新类型 → Temporal Workflow
                                └─ 管理员审批 (7天)
```

---

## BaseAgent 执行循环

```
                    ┌─────────────────────┐
                    │      AgentState     │
                    │  input, messages,   │
                    │  tool_calls,        │
                    │  iterations, error  │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
              ┌────▶│      think          │
              │     │  (LLM 推理节点)      │
              │     └─────────┬───────────┘
              │               │
              │               ▼
              │     ┌─────────────────────┐
              │     │ should_exec_tools?  │
              │     └────┬──────────┬─────┘
              │          │ yes      │ no
              │          ▼          ▼
              │  ┌──────────────┐  ┌──────────┐
              │  │execute_tools │  │  output   │
              │  │ (工具执行)    │  │  (输出)   │
              │  └──────┬───────┘  └─────┬────┘
              │         │                │
              └─────────┘                ▼
                                       END
```

---

## 关键文件索引

| 组件 | 路径 |
|------|------|
| Agent 基类 | `backend/app/agents/base.py` |
| Agent 注册表 | `backend/app/agents/registry.py` |
| ChatAgent | `backend/app/agents/chat_agent.py` |
| EmailSummarizerAgent | `backend/app/agents/email_summarizer.py` |
| WorkTypeAnalyzerAgent | `backend/app/agents/work_type_analyzer.py` |
| LLM 网关 | `backend/app/llm/gateway.py` |
| Tool 框架 | `backend/app/tools/base.py` |
| Tool 注册表 | `backend/app/tools/registry.py` |
| Prompt 管理 | `backend/app/llm/prompts/manager.py` |
| Prompt 默认值 | `backend/app/llm/prompts/defaults.py` |
| Celery 配置 | `backend/app/celery_app.py` |
| Temporal 客户端 | `backend/app/temporal/client.py` |
| Temporal 工作流 | `backend/app/temporal/workflows/work_type_suggestion.py` |
| Temporal Activities | `backend/app/temporal/activities/work_type.py` |
