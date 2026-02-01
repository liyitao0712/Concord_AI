# Prompt 系统迁移报告

> 完成时间: 2026-02-01

---

## 迁移概述

废弃了旧的 `app/prompts/` 系统，统一使用新的 `app/llm/prompts/` 管理系统。

### 迁移目标

✅ 统一 Prompt 管理方式
✅ 支持后台动态修改 Prompt
✅ 减少代码维护成本
✅ 提供数据库 + 缓存机制

---

## 变更清单

### 1. 删除的文件

```
app/prompts/
├── __init__.py          # 已删除
├── base.py              # 已删除（PromptTemplate 和 SystemPrompt 类）
├── extraction.py        # 已删除（实体提取 Prompt）
└── intent.py            # 已删除（意图分类 Prompt）
```

### 2. 新增的 Prompt（添加到 defaults.py）

| Prompt 名称 | 类别 | 说明 |
|------------|------|------|
| `entity_extraction` | tool | 通用实体提取（客户、产品、订单） |
| `inquiry_extraction` | tool | 询价信息提取 |
| `order_extraction` | tool | 订单信息提取 |
| `contact_extraction` | tool | 联系人信息提取 |
| `email_intent` | tool | 邮件意图分类（带主题） |
| `batch_intent` | tool | 批量意图分类 |

### 3. 修改的文件

#### `app/llm/prompts/defaults.py`

**变更**：添加 6 个新 Prompt（从旧系统迁移）

**影响**：
- 现在包含 14 个 Prompt（原 8 个 + 新增 6 个）
- 所有旧系统的 Prompt 都已迁移

#### `app/api/llm.py`

**变更内容**：

```python
# 之前
from app.prompts import (
    ASSISTANT_SYSTEM,
    INTENT_SYSTEM,
    INTENT_CLASSIFIER_PROMPT,
)

system = request.system_prompt or ASSISTANT_SYSTEM.render()
prompt = INTENT_CLASSIFIER_PROMPT.render(content=request.content)

# 之后
from app.llm.prompts import render_prompt

system = await render_prompt("chat_agent")
prompt = await render_prompt("intent_classifier", content=request.content)
```

**修改位置**：
- 第 27 行：Import 语句
- 第 166-173 行：`/chat` 端点使用 `chat_agent` Prompt
- 第 256-263 行：`/stream` 端点使用 `chat_agent` Prompt
- 第 338-347 行：`/classify` 端点使用 `intent_classifier` Prompt

---

## 新旧系统对比

### 旧系统 (`app/prompts/`)

**特点**：
- 基于类的 Prompt 模板（`PromptTemplate` 和 `SystemPrompt`）
- 硬编码在 Python 文件中
- 使用 `{variable}` 语法
- 修改需要重启服务

**使用方式**：
```python
from app.prompts import INTENT_CLASSIFIER_PROMPT, INTENT_SYSTEM

prompt = INTENT_CLASSIFIER_PROMPT.render(content="...")
system = INTENT_SYSTEM.render()
```

### 新系统 (`app/llm/prompts/`)

**特点**：
- 数据库优先 + `defaults.py` fallback
- 支持后台管理界面修改
- 使用 `{{variable}}` 语法（Jinja2）
- 5 分钟 TTL 缓存
- 修改后无需重启

**使用方式**：
```python
from app.llm.prompts import render_prompt

# 自动从数据库加载，fallback 到 defaults.py
prompt = await render_prompt("intent_classifier", content="...")
```

---

## Prompt 映射表

| 旧 Prompt | 新 Prompt | 说明 |
|-----------|-----------|------|
| `ASSISTANT_SYSTEM` | `chat_agent` | 通用聊天助手系统提示 |
| `INTENT_SYSTEM` + `INTENT_CLASSIFIER_PROMPT` | `intent_classifier` | 意图分类（已合并） |
| `ENTITY_EXTRACTION_PROMPT` | `entity_extraction` | 通用实体提取 |
| `INQUIRY_EXTRACTION_PROMPT` | `inquiry_extraction` | 询价信息提取 |
| `ORDER_EXTRACTION_PROMPT` | `order_extraction` | 订单信息提取 |
| `CONTACT_EXTRACTION_PROMPT` | `contact_extraction` | 联系人信息提取 |
| `EMAIL_INTENT_PROMPT` | `email_intent` | 邮件意图分类 |
| `BATCH_INTENT_PROMPT` | `batch_intent` | 批量意图分类 |
| `JSON_OUTPUT_SYSTEM` | （合并到各 Prompt） | 已合并到具体 Prompt 的指令中 |

---

## 迁移验证

### 语法检查

```bash
python3 -m py_compile app/api/llm.py
python3 -m py_compile app/llm/prompts/defaults.py
```

✅ 无语法错误

### 依赖检查

```bash
grep -r "from app.prompts" app/
```

✅ 无外部引用

### 功能测试建议

1. **测试 `/api/llm/chat` 端点**
   ```bash
   curl -X POST http://localhost:8000/api/llm/chat \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message": "你好，请介绍一下自己"}'
   ```

2. **测试 `/api/llm/classify` 端点**
   ```bash
   curl -X POST http://localhost:8000/api/llm/classify \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"content": "请问产品A的价格是多少？"}'
   ```

3. **测试 Prompt 管理后台**
   - 访问 `/admin/prompts`
   - 修改 `chat_agent` Prompt
   - 调用 `/api/llm/chat` 验证修改生效

---

## 当前 Prompt 清单

### Agent Prompts（6 个）

1. `intent_classifier` - 意图分类器
2. `email_analyzer` - 邮件分析器
3. `quote_agent` - 报价生成器
4. `chat_agent` - 聊天助手
5. `email_summarizer` - 邮件摘要分析器
6. `router_agent` - 路由代理（未在 defaults.py，已在数据库）

### Tool Prompts（8 个）

1. `summarizer` - 摘要生成器
2. `translator` - 翻译器
3. `entity_extraction` - 通用实体提取
4. `inquiry_extraction` - 询价信息提取
5. `order_extraction` - 订单信息提取
6. `contact_extraction` - 联系人信息提取
7. `email_intent` - 邮件意图分类
8. `batch_intent` - 批量意图分类

**总计**: 14 个 Prompt

---

## 后续建议

### 1. 初始化数据库 Prompt

运行 Prompt 初始化 API：
```bash
curl -X POST http://localhost:8000/admin/prompts/init-defaults \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

这会将 `defaults.py` 中的所有 Prompt 同步到数据库。

### 2. 定期备份 Prompt

建议定期导出 Prompt 配置：
```sql
-- 导出所有 Prompt
SELECT name, content, variables
FROM prompts
ORDER BY category, name;
```

### 3. Prompt 版本控制

利用 `prompt_history` 表查看修改历史：
```sql
-- 查看某个 Prompt 的修改历史
SELECT version, changed_at, changed_by, change_summary
FROM prompt_history
WHERE prompt_name = 'chat_agent'
ORDER BY changed_at DESC
LIMIT 10;
```

### 4. 监控 Prompt 缓存

查看 Prompt 加载来源（数据库 vs fallback）：
```bash
# 查看日志
grep "Prompt.*fallback" logs/app.log
```

---

## 回滚方案

如果迁移出现问题，可以通过以下方式回滚：

### 方案 A：恢复旧系统（不推荐）

```bash
# 从 Git 历史恢复
git checkout HEAD~1 -- app/prompts/
git checkout HEAD~1 -- app/api/llm.py
```

### 方案 B：修复问题（推荐）

1. 检查日志中的具体错误
2. 修复 Prompt 内容或变量名
3. 使用后台管理界面调整 Prompt

---

## 已知问题

### 问题 1：render_prompt 返回 None

**原因**：数据库中没有该 Prompt，且 defaults.py 中也没有定义

**解决**：
1. 检查 Prompt 名称拼写
2. 运行 `/admin/prompts/init-defaults` 同步默认 Prompt
3. 或在后台手动创建 Prompt

### 问题 2：变量渲染失败

**原因**：变量名不匹配（旧系统用 `{var}`，新系统用 `{{var}}`）

**解决**：
- 检查 Prompt 内容中的变量语法
- 确保调用时传递了所有必需变量

---

## 相关文档

- [MANUAL.md](MANUAL.md#7-llm-服务) - LLM 服务说明
- [LLM_MANUAL.md](LLM_MANUAL.md) - LLM 管理完整手册
- [LLM_ARCHITECTURE_REVIEW.md](LLM_ARCHITECTURE_REVIEW.md) - LLM 调用架构审查

---

*迁移完成时间: 2026-02-01*
*执行人: Claude Code*
