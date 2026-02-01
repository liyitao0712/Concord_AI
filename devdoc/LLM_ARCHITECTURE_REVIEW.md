# LLM 调用架构审查报告

> 2026-02-01

---

## 📊 当前状况总览

### ✅ 优点

1. **基本日志记录**：所有 LLM 调用都有基本的日志输出
2. **性能追踪**：记录了耗时、Token 使用量
3. **错误处理**：有完整的 try-catch 和错误日志
4. **支持流式输出**：Gateway 和 Service 都支持 SSE

### ❌ 发现的问题

| 问题 | 严重程度 | 影响范围 |
|------|---------|---------|
| **两个并存的 LLM 封装层** | 🔴 高 | 全局架构 |
| **缺少 LLM 调用日志表** | 🟡 中 | 监控和审计 |
| **没有统一的调用拦截器** | 🟡 中 | Token 统计不完整 |
| **使用统计未入库** | 🟡 中 | 数据丢失风险 |
| **缺少调用链追踪** | 🟡 中 | 问题定位困难 |

---

## 🔍 详细分析

### 问题 1: 两个并存的 LLM 封装层

**现状**：

```
项目中存在两个 LLM 封装：

1. LLMGateway (app/llm/gateway.py)
   - 使用者：BaseAgent, RouterAgent, ChatAgent 等
   - 特点：功能全面，支持 tools、JSON 模式

2. LLMService (app/services/llm_service.py)
   - 使用者：API 层 (app/api/llm.py)
   - 特点：简单封装，面向 API 调用
```

**问题**：
- 维护两套代码，容易不一致
- 日志格式不统一
- Token 统计分散，无法汇总
- 新功能要在两处添加

**建议**：
```
方案 A：统一为 LLMGateway（推荐）
- 废弃 LLMService
- API 层改用 LLMGateway
- 理由：LLMGateway 功能更完善

方案 B：统一为 LLMService
- 废弃 LLMGateway
- BaseAgent 改用 LLMService
- 理由：LLMService 更简单

推荐方案 A，因为 LLMGateway 已支持 tools、JSON 模式等高级功能。
```

---

### 问题 2: 缺少 LLM 调用日志表

**现状**：

只有文件日志，没有数据库记录：
```python
# app/llm/gateway.py:163
logger.info(f"[LLM] 调用模型: {model}")
logger.info(f"[LLM] 完成，使用 {usage['total_tokens']} tokens")
```

**问题**：
- 无法查询历史调用记录
- 无法按用户/Agent/时间段统计
- 日志轮转后数据丢失
- 无法追溯成本

**建议**：

创建 `llm_call_logs` 表：

```python
# app/models/llm_call_log.py

class LLMCallLog(Base):
    __tablename__ = "llm_call_logs"

    id = Column(String(36), primary_key=True)

    # 调用信息
    model = Column(String(100), index=True)       # 使用的模型
    provider = Column(String(50), index=True)     # 提供商

    # 调用者信息
    caller_type = Column(String(50), index=True)  # agent / api / workflow
    caller_name = Column(String(100))             # agent 名称或 API 路径
    user_id = Column(String(36), nullable=True, index=True)  # 用户 ID

    # 请求内容
    system_prompt = Column(Text, nullable=True)   # 系统提示
    user_message = Column(Text)                   # 用户消息
    messages_count = Column(Integer, default=1)   # 消息数量（含历史）

    # 响应内容
    response_content = Column(Text)               # LLM 响应
    finish_reason = Column(String(50))            # 完成原因

    # 使用统计
    prompt_tokens = Column(Integer)               # 输入 Token
    completion_tokens = Column(Integer)           # 输出 Token
    total_tokens = Column(Integer, index=True)    # 总 Token

    # 性能指标
    latency_ms = Column(Integer)                  # 延迟（毫秒）

    # 状态
    status = Column(String(20), index=True)       # success / error
    error_message = Column(Text, nullable=True)   # 错误信息

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

**优点**：
- ✅ 可查询历史调用
- ✅ 可统计成本
- ✅ 可分析使用模式
- ✅ 可追踪问题
- ✅ 可生成报表

---

### 问题 3: 没有统一的调用拦截器

**现状**：

每个调用点都手动记录日志：

```python
# app/llm/gateway.py:163-183
logger.info(f"[LLM] 调用模型: {model}")
# ... 调用 LLM ...
logger.info(f"[LLM] 完成，使用 {usage['total_tokens']} tokens")
```

**问题**：
- 重复代码
- 容易遗漏
- 不统一

**建议**：

创建装饰器统一拦截：

```python
# app/llm/interceptor.py

import functools
from typing import Optional
from contextlib import asynccontextmanager

class LLMCallInterceptor:
    """LLM 调用拦截器"""

    @staticmethod
    async def log_call(
        model: str,
        caller_type: str,
        caller_name: str,
        user_id: Optional[str],
        system_prompt: Optional[str],
        messages: list,
        response_content: str,
        usage: dict,
        latency_ms: int,
        status: str,
        error: Optional[str] = None,
    ):
        """记录 LLM 调用到数据库"""
        from app.core.database import async_session_maker
        from app.models.llm_call_log import LLMCallLog
        import uuid

        async with async_session_maker() as session:
            log = LLMCallLog(
                id=str(uuid.uuid4()),
                model=model,
                provider=model.split("/")[0] if "/" in model else "anthropic",
                caller_type=caller_type,
                caller_name=caller_name,
                user_id=user_id,
                system_prompt=system_prompt,
                user_message=messages[-1]["content"] if messages else "",
                messages_count=len(messages),
                response_content=response_content,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=latency_ms,
                status=status,
                error_message=error,
            )
            session.add(log)
            await session.commit()

    @staticmethod
    async def update_model_stats(model_id: str, tokens: int):
        """更新模型使用统计"""
        from app.core.database import async_session_maker
        from app.models.llm_model_config import LLMModelConfig
        from sqlalchemy import update

        async with async_session_maker() as session:
            stmt = (
                update(LLMModelConfig)
                .where(LLMModelConfig.model_id == model_id)
                .values(
                    total_requests=LLMModelConfig.total_requests + 1,
                    total_tokens=LLMModelConfig.total_tokens + tokens,
                    last_used_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)
            await session.commit()


@asynccontextmanager
async def track_llm_call(
    model: str,
    caller_type: str = "api",
    caller_name: str = "unknown",
    user_id: Optional[str] = None,
):
    """
    LLM 调用追踪上下文管理器

    用法：
        async with track_llm_call("claude-sonnet-4", "agent", "email_summarizer"):
            response = await llm.chat(...)
    """
    import time

    start_time = time.time()

    try:
        # 调用前记录
        logger.info(f"[LLM] {caller_type}:{caller_name} -> {model}")

        yield

        # 调用后记录
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[LLM] 完成，耗时 {latency_ms}ms")

    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[LLM] 失败: {e}")
        raise
```

**使用示例**：

```python
# 在 LLMGateway.chat() 中
async def chat(self, message: str, **kwargs) -> LLMResponse:
    # ... 构建 messages ...

    start_time = time.time()

    try:
        response = await acompletion(...)
        latency_ms = int((time.time() - start_time) * 1000)

        # 记录到数据库
        await LLMCallInterceptor.log_call(
            model=model,
            caller_type=getattr(self, "_caller_type", "api"),
            caller_name=getattr(self, "_caller_name", "unknown"),
            user_id=getattr(self, "_user_id", None),
            system_prompt=system,
            messages=messages,
            response_content=content,
            usage=usage,
            latency_ms=latency_ms,
            status="success",
        )

        # 更新模型统计
        await LLMCallInterceptor.update_model_stats(model, usage["total_tokens"])

        return LLMResponse(...)

    except Exception as e:
        # 记录错误
        await LLMCallInterceptor.log_call(..., status="error", error=str(e))
        raise
```

---

### 问题 4: 使用统计未实时入库

**现状**：

`llm_model_configs` 表有统计字段，但没有自动更新：

```sql
SELECT model_id, total_requests, total_tokens FROM llm_model_configs;
-- 结果：都是 0，因为没有自动更新机制
```

**建议**：

参见问题 3 的解决方案，在拦截器中自动更新。

---

### 问题 5: 缺少调用链追踪

**现状**：

无法追踪一个请求的完整调用链：

```
用户请求 -> API -> Agent -> LLM
                        ↓
                    Tool 调用 -> 数据库查询
```

**建议**：

添加 `trace_id` 字段：

```python
# 在 LLMCallLog 表添加
trace_id = Column(String(36), index=True)  # 追踪 ID
parent_call_id = Column(String(36), nullable=True)  # 父调用 ID

# 使用方式
import contextvars

# 创建上下文变量
current_trace_id = contextvars.ContextVar("trace_id", default=None)

# 在 FastAPI 中间件中设置
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    import uuid
    trace_id = str(uuid.uuid4())
    current_trace_id.set(trace_id)
    response = await call_next(request)
    return response

# 在 LLM 调用时自动获取
trace_id = current_trace_id.get()
```

---

## 🎯 优化建议总结

### 优先级 P0（立即执行）

1. **创建 `llm_call_logs` 表**
   - 迁移文件：`alembic revision -m "add llm_call_logs table"`
   - 影响：可追溯所有 LLM 调用

2. **统一 LLM 入口为 `LLMGateway`**
   - 废弃 `LLMService`
   - API 层改用 `LLMGateway`
   - 影响：减少维护成本，统一日志

### 优先级 P1（本周完成）

3. **添加 LLM 调用拦截器**
   - 创建 `app/llm/interceptor.py`
   - 在 `LLMGateway` 中集成
   - 影响：自动记录所有调用

4. **实时更新模型统计**
   - 每次调用自动更新 `llm_model_configs.total_requests` 和 `total_tokens`
   - 影响：准确的使用统计

### 优先级 P2（下周完成）

5. **添加调用链追踪（Trace ID）**
   - 添加 FastAPI 中间件
   - LLM 日志记录 trace_id
   - 影响：可追踪完整调用链

6. **创建 LLM 使用统计 Dashboard**
   - 按模型统计
   - 按 Agent 统计
   - 按用户统计
   - 按时间段统计

---

## 📈 预期效果

实施后的改进：

| 指标 | 当前 | 优化后 |
|------|------|--------|
| LLM 调用可追溯性 | ❌ 无 | ✅ 100% 可查询 |
| Token 统计准确性 | ⚠️ 部分 | ✅ 实时准确 |
| 问题定位时间 | 🔴 > 1 小时 | 🟢 < 5 分钟 |
| 成本分析能力 | ❌ 无 | ✅ 完整报表 |
| 代码维护成本 | 🔴 高（两套） | 🟢 低（一套）|

---

## 📝 实施清单

### Step 1: 数据库迁移

```bash
# 创建迁移
cd backend
alembic revision -m "add llm_call_logs table"

# 编辑迁移文件，添加表定义
# 执行迁移
alembic upgrade head
```

### Step 2: 创建模型和拦截器

```bash
# 创建文件
touch app/models/llm_call_log.py
touch app/llm/interceptor.py
```

### Step 3: 修改 LLMGateway

在 `app/llm/gateway.py` 的 `chat()` 方法中集成拦截器。

### Step 4: 废弃 LLMService

```bash
# 查找所有使用 LLMService 的地方
grep -r "from app.services.llm_service import" app/

# 逐个替换为 LLMGateway
# ...

# 删除文件
rm app/services/llm_service.py
```

### Step 5: 测试验证

```bash
# 调用一次 LLM
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "hello"}'

# 检查数据库
psql -d concord_ai -c "SELECT * FROM llm_call_logs ORDER BY created_at DESC LIMIT 1;"

# 检查模型统计是否更新
psql -d concord_ai -c "SELECT model_id, total_requests, total_tokens FROM llm_model_configs;"
```

---

## 🔗 相关文档

- [LLM_MANUAL.md](LLM_MANUAL.md) - LLM 管理完整手册
- [MANUAL.md](MANUAL.md#7-llm-服务) - 代码手册 LLM 部分
- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构文档

---

*审查完成时间: 2026-02-01*
