# Prompt 文档索引

本目录包含所有 Agent Prompt 的完整内容，方便查看和对比。

> 源代码定义：`backend/app/llm/prompts/defaults.py`
> 运行时优先从数据库加载，数据库无记录时使用 defaults.py 中的默认值。

## Agent Prompts

| 文件 | Agent | 说明 |
|------|-------|------|
| [chat_agent.md](chat_agent.md) | Chat Agent | 通用 AI 聊天助手 |
| [email_summarizer.md](email_summarizer.md) | Email Summarizer | 外贸邮件分析，提取意图、产品、金额等结构化信息 |
| [work_type_analyzer.md](work_type_analyzer.md) | Work Type Analyzer | 邮件工作类型分类，匹配已有类型或建议新类型 |
| [customer_extractor.md](customer_extractor.md) | Customer Extractor | 从邮件中提取客户和联系人信息 |
| [add_new_client_helper.md](add_new_client_helper.md) | Add New Client Helper | 通过网络搜索研究公司信息，自动填充客户记录 |
| [add_new_supplier_helper.md](add_new_supplier_helper.md) | Add New Supplier Helper | 通过网络搜索研究供应商信息，自动填充供应商记录 |
