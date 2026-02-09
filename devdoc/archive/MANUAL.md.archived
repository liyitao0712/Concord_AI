# Concord AI - 代码手册

> 详细讲解核心代码的设计思路和使用方法

---

## 目录

1. [项目结构](#1-项目结构)
2. [配置管理](#2-配置管理)
3. [日志系统](#3-日志系统)
4. [数据库层](#4-数据库层)
5. [Redis 缓存层](#5-redis-缓存层)
6. [认证系统](#6-认证系统)
7. [LLM 服务](#7-llm-服务) - **详见 [LLM 完整手册](LLM_MANUAL.md)**
8. [Prompt 模板](#8-prompt-模板)
9. [API 层](#9-api-层)
10. [依赖注入](#10-依赖注入)
11. [存储层 (OSS)](#11-存储层-oss)
12. [幂等性中间件](#12-幂等性中间件)
13. [管理员后台 API](#13-管理员后台-api)
14. [前端结构](#14-前端结构)
15. [Temporal 工作流](#15-temporal-工作流)
16. [运维脚本](#16-运维脚本)
17. [系统设置](#17-系统设置)
18. [Chat 系统](#18-chat-系统)
19. [飞书集成](#19-飞书集成)

---

## 1. 项目结构

### 后端结构

```
backend/app/
├── main.py              # FastAPI 入口，应用生命周期管理
├── api/                 # API 路由层
│   ├── health.py        # 健康检查接口
│   ├── auth.py          # 认证接口（注册/登录/刷新）
│   ├── llm.py           # LLM 测试接口（对话/流式/分类）
│   ├── admin.py         # 管理员用户管理接口
│   ├── admin_monitor.py # 运行监控接口
│   ├── agents.py        # Agent 调用接口
│   ├── chat.py          # 聊天会话接口
│   ├── workflows.py     # 工作流接口
│   └── settings.py      # 系统设置接口（/admin/settings/*）
├── core/                # 核心基础设施
│   ├── config.py        # 配置管理
│   ├── database.py      # 数据库连接
│   ├── redis.py         # Redis 连接
│   ├── logging.py       # 日志系统
│   ├── security.py      # JWT 认证
│   └── idempotency.py   # 幂等性中间件
├── storage/             # 存储层
│   ├── oss.py           # 阿里云 OSS 文件存储
│   └── email.py         # 邮件收发 (IMAP/SMTP)
├── models/              # SQLAlchemy 数据模型
│   ├── user.py          # 用户模型
│   ├── chat.py          # 聊天会话/消息模型
│   ├── execution.py     # Agent 执行记录模型
│   ├── prompt.py        # Prompt 模板模型
│   └── settings.py      # 系统设置模型
├── schemas/             # Pydantic 请求/响应模式
│   ├── user.py          # 用户相关 Schema
│   ├── chat.py          # 聊天相关 Schema
│   └── event.py         # 统一事件模型
├── llm/                 # LLM 网关层
│   ├── gateway.py       # LiteLLM 统一封装
│   ├── settings_loader.py # 从数据库加载 LLM 设置
│   └── prompts/         # Prompt 模板
│       ├── defaults.py  # 默认模板
│       └── manager.py   # 模板管理器
├── agents/              # AI Agent 层
│   ├── base.py          # Agent 基类 (LangGraph)
│   ├── registry.py      # Agent 注册中心
│   ├── chat_agent.py    # 聊天 Agent（支持多轮对话）
│   ├── email_analyzer.py # 邮件分析 Agent
│   ├── intent_classifier.py # 意图分类 Agent
│   └── quote_agent.py   # 报价 Agent
├── adapters/            # 外部平台适配器
│   └── feishu.py        # 飞书客户端和适配器
├── tools/               # Agent 工具层
│   ├── base.py          # Tool 基类
│   ├── registry.py      # Tool 注册中心
│   ├── database.py      # 数据库查询工具
│   ├── http.py          # HTTP 请求工具
│   ├── email.py         # 邮件收发工具
│   └── file.py          # 文件操作工具
└── workflows/           # Temporal 工作流
    ├── worker.py        # Worker 入口
    ├── client.py        # Temporal 客户端
    ├── activities/      # Activity 定义
    └── definitions/     # Workflow 定义
```

### 前端结构

```
frontend/src/
├── app/                    # Next.js App Router 页面
│   ├── layout.tsx          # 根布局（全局 Provider）
│   ├── page.tsx            # 首页（自动重定向）
│   ├── login/
│   │   └── page.tsx        # 登录页
│   └── admin/
│       ├── layout.tsx      # 管理后台布局（侧边栏导航）
│       ├── page.tsx        # 仪表盘
│       ├── users/
│       │   └── page.tsx    # 用户管理
│       ├── llm/
│       │   └── page.tsx    # LLM 配置
│       ├── monitor/
│       │   └── page.tsx    # 运行监控
│       └── settings/
│           ├── page.tsx    # 系统设置
│           └── feishu/
│               └── page.tsx # 飞书配置
├── contexts/
│   └── AuthContext.tsx     # 认证上下文
└── lib/
    └── api.ts              # API 工具库
```

---

## 2. 配置管理

**文件**: `app/core/config.py`

### 设计思路

使用 Pydantic Settings 管理配置，好处：
- 自动从环境变量和 `.env` 文件加载
- 类型验证和转换
- IDE 自动补全支持
- 使用 `@lru_cache` 确保单例

### 代码讲解

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # 定义配置项，类型注解 + 默认值
    APP_NAME: str = "Concord AI"
    DATABASE_URL: str = "postgresql+asyncpg://..."
    REDIS_URL: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"       # 从 .env 加载
        case_sensitive = True   # 环境变量区分大小写

@lru_cache()  # 缓存，确保只创建一次
def get_settings() -> Settings:
    return Settings()

settings = get_settings()  # 全局单例
```

### 使用方法

```python
from app.core.config import settings

# 直接使用
print(settings.APP_NAME)
print(settings.REDIS_URL)
```

### 配置项一览

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `APP_NAME` | str | "Concord AI" | 应用名称 |
| `DEBUG` | bool | False | 调试模式 |
| `DATABASE_URL` | str | ... | PostgreSQL 连接串 |
| `REDIS_URL` | str | redis://localhost:6379/0 | Redis 连接串 |
| `ANTHROPIC_API_KEY` | str | "" | Claude API 密钥 |
| `JWT_SECRET` | str | ... | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | 15 | 访问令牌过期时间 |

---

## 3. 日志系统

**文件**: `app/core/logging.py`

### 设计思路

为什么选择 Python 标准库 logging：
- 与 Temporal SDK、SQLAlchemy、uvicorn 等框架天然兼容
- 所有库的日志统一出口，便于管理
- 未来集成 Temporal 无需额外配置
- 成熟稳定，无额外依赖

### 核心组件

#### 1. ColoredFormatter - 彩色格式化器

开发环境使用，让日志更易读：

```python
class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器，用于开发环境"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # 根据日志级别添加颜色
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)
```

#### 2. JSONFormatter - JSON 格式化器

生产环境使用，便于 ELK 等日志分析系统：

```python
class JSONFormatter(logging.Formatter):
    """JSON 日志格式化器，用于生产环境"""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # 如果有异常信息，添加到日志
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj, ensure_ascii=False)
```

#### 3. RequestLoggingMiddleware - 请求日志中间件

自动记录每个 HTTP 请求：

```python
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """HTTP 请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 执行请求
        response = await call_next(request)

        # 计算耗时
        duration = time.time() - start_time

        # 记录日志
        logger.info(
            f"{request.method} {request.url.path} "
            f"-> {response.status_code} "
            f"[{duration*1000:.0f}ms]"
        )
        return response
```

#### 4. log_execution 装饰器

自动记录函数执行：

```python
def log_execution(func):
    """函数执行日志装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"开始执行: {func_name}")
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.debug(f"完成执行: {func_name} [{duration*1000:.0f}ms]")
            return result
        except Exception as e:
            logger.error(f"执行失败: {func_name} - {e}")
            raise
    return wrapper
```

### 使用方法

```python
from app.core.logging import get_logger, log_execution

# 获取 logger
logger = get_logger(__name__)

# 基础使用
logger.info("这是一条信息日志")
logger.warning("这是一条警告日志")
logger.error("这是一条错误日志")

# 带参数
logger.info(f"用户 {user_id} 登录成功")

# 使用装饰器
@log_execution
async def process_email(email_id: str):
    # 函数执行会自动记录开始、结束、耗时
    ...
```

### 日志输出示例

开发环境（彩色）：
```
2026-01-30 10:30:45.123 | INFO     | app.api.auth:login:89 | 用户 test@example.com 登录成功
2026-01-30 10:30:45.456 | DEBUG    | app.services.llm:chat:45 | LLM 调用完成 [1234ms]
```

生产环境（JSON）：
```json
{"timestamp":"2026-01-30T10:30:45.123","level":"INFO","logger":"app.api.auth","message":"用户 test@example.com 登录成功","module":"auth","function":"login","line":89}
```

---

## 4. 数据库层

**文件**: `app/core/database.py`

### 设计思路

- 使用 SQLAlchemy 2.0 异步模式
- `asyncpg` 作为 PostgreSQL 驱动（高性能）
- 通过依赖注入管理 Session 生命周期
- 自动处理事务提交/回滚

### 代码讲解

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# 1. 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # DEBUG 模式下打印 SQL
)

# 2. 创建 Session 工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后不过期对象
)

# 3. 定义模型基类
class Base(DeclarativeBase):
    pass

# 4. 依赖注入函数
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()    # 成功则提交
        except Exception:
            await session.rollback()  # 失败则回滚
            raise
```

### 使用方法

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()
```

---

## 5. Redis 缓存层

**文件**: `app/core/redis.py`

### 设计思路

- 封装 `RedisClient` 类，统一管理连接
- 提供常用操作的便捷方法
- 支持连接池（`redis.asyncio` 内置）
- 通过 FastAPI lifespan 管理生命周期

### 当前实现状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 连接管理 | ✅ 已实现 | connect/disconnect |
| 基础操作 | ✅ 已实现 | get/set/delete/exists |
| 过期控制 | ✅ 已实现 | expire/ttl |
| 健康检查 | ✅ 已实现 | ping |
| 缓存装饰器 | ❌ 待开发 | 自动缓存函数结果 |
| Session 存储 | ❌ 待开发 | 用户会话管理 |
| 分布式锁 | ❌ 待开发 | 防止并发冲突 |
| 消息队列 | ❌ 待开发 | 简单的 pub/sub |

### 代码讲解

```python
import redis.asyncio as redis

class RedisClient:
    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """连接 Redis"""
        self._client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,  # 自动解码为字符串
        )
        await self._client.ping()  # 测试连接

    async def disconnect(self) -> None:
        """断开连接"""
        if self._client:
            await self._client.close()

    # 便捷方法
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    async def set(self, key: str, value: str,
                  ex: Optional[int] = None,  # 过期秒数
                  nx: bool = False           # 仅当 key 不存在时设置
                 ) -> bool:
        return await self.client.set(key, value, ex=ex, nx=nx)

    async def delete(self, key: str) -> int:
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """获取剩余过期时间（秒）"""
        return await self.client.ttl(key)

# 全局单例
redis_client = RedisClient()
```

### 生命周期管理

在 `app/main.py` 中通过 lifespan 管理连接：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时连接
    await redis_client.connect()
    print("Redis connected")

    yield

    # 关闭时断开
    await redis_client.disconnect()
```

### 使用方法

#### 方法一：直接使用全局实例

```python
from app.core.redis import redis_client

async def cache_user(user_id: int, user_data: dict):
    import json
    key = f"user:{user_id}"
    await redis_client.set(key, json.dumps(user_data), ex=3600)  # 1小时过期

async def get_cached_user(user_id: int) -> Optional[dict]:
    import json
    key = f"user:{user_id}"
    data = await redis_client.get(key)
    return json.loads(data) if data else None
```

#### 方法二：依赖注入（可选）

```python
from fastapi import Depends
from app.core.redis import get_redis

@router.get("/cache/{key}")
async def get_cache(key: str, redis = Depends(get_redis)):
    return await redis.get(key)
```

### 常见使用场景（待开发）

#### 1. API 响应缓存

```python
# 缓存 LLM 分析结果，避免重复调用
async def get_email_analysis(email_id: str):
    cache_key = f"analysis:{email_id}"

    # 先查缓存
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # 调用 LLM 分析
    result = await llm_analyze(email_id)

    # 写入缓存，1小时过期
    await redis_client.set(cache_key, json.dumps(result), ex=3600)
    return result
```

#### 2. 速率限制

```python
async def check_rate_limit(user_id: str, limit: int = 100) -> bool:
    """每分钟限制请求次数"""
    key = f"rate:{user_id}:{int(time.time() // 60)}"

    count = await redis_client.client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)

    return count <= limit
```

#### 3. 分布式锁

```python
async def acquire_lock(lock_name: str, timeout: int = 10) -> bool:
    """获取分布式锁"""
    key = f"lock:{lock_name}"
    return await redis_client.set(key, "1", ex=timeout, nx=True)

async def release_lock(lock_name: str):
    """释放锁"""
    await redis_client.delete(f"lock:{lock_name}")
```

---

## 6. 认证系统

**文件**: `app/core/security.py`

### 设计思路

- **双 Token 机制**：Access Token (15分钟) + Refresh Token (7天)
- **bcrypt 哈希**：自动加盐，抗彩虹表攻击
- **依赖注入**：通过 FastAPI Depends 获取当前用户

### 核心组件

#### 1. 密码哈希

```python
from passlib.context import CryptContext

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """将明文密码转换为哈希值"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否正确"""
    return pwd_context.verify(plain_password, hashed_password)
```

#### 2. JWT Token 生成

```python
from jose import jwt
from datetime import datetime, timedelta

def create_access_token(data: dict) -> str:
    """创建访问令牌（15分钟有效）"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

def create_refresh_token(data: dict) -> str:
    """创建刷新令牌（7天有效）"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")
```

#### 3. 用户认证依赖

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭据")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user
```

### 使用方法

```python
from app.core.security import get_current_user
from app.models.user import User

@router.get("/protected")
async def protected_route(current_user: User = Depends(get_current_user)):
    """需要登录才能访问的接口"""
    return {"user": current_user.email}
```

### 认证流程

```
1. 用户注册 POST /api/auth/register
   - 接收 email, password, name
   - 密码 bcrypt 哈希存储
   - 返回用户信息

2. 用户登录 POST /api/auth/login
   - 验证邮箱和密码
   - 返回 access_token + refresh_token

3. 访问受保护接口
   - Header: Authorization: Bearer <access_token>
   - 自动解析用户信息

4. Token 刷新 POST /api/auth/refresh
   - 使用 refresh_token 获取新的 access_token
```

---

## 7. LLM 服务

**文件**: `app/services/llm_service.py`

### 设计思路

- 使用 LiteLLM 统一封装不同的 LLM 提供商（Claude、GPT、Gemini 等）
- 支持普通调用和流式输出
- 自动记录 Token 消耗和延迟

### 核心组件

#### LLMService 类

```python
import litellm

class LLMService:
    def __init__(self):
        self.default_model = settings.DEFAULT_LLM_MODEL

    async def chat(
        self,
        message: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """普通对话，返回完整响应"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        response = await litellm.acompletion(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature or 0.7,
        )
        return response.choices[0].message.content

    async def chat_stream(
        self,
        message: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """流式对话，逐字返回"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        response = await litellm.acompletion(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature or 0.7,
            stream=True,  # 启用流式
        )

        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
```

### 使用方法

```python
from app.services.llm_service import llm_service

# 普通对话
response = await llm_service.chat(
    message="你好，请介绍一下自己",
    system_prompt="你是一个友好的助手"
)

# 流式对话
async for chunk in llm_service.chat_stream(message="写一首诗"):
    print(chunk, end="", flush=True)
```

### 配置说明

在 `.env` 中配置 API Key：
```bash
ANTHROPIC_API_KEY=sk-xxx    # Claude API
OPENAI_API_KEY=sk-xxx       # OpenAI API（可选）
DEFAULT_LLM_MODEL=claude-sonnet-4-20250514
```

---

## 8. Prompt 模板

**文件**: `app/prompts/`

### 设计思路

- **PromptTemplate**：简单的变量替换模板
- **SystemPrompt**：结构化的系统提示词（角色、指令、约束、示例）
- **预定义模板**：常用的意图分类、实体提取模板

### 核心组件

#### 1. PromptTemplate 类

```python
class PromptTemplate:
    """Prompt 模板类，支持变量替换"""

    def __init__(self, name: str, description: str, template: str):
        self.name = name
        self.description = description
        self.template = template

    def render(self, **kwargs) -> str:
        """渲染模板，替换变量"""
        return self.template.format(**kwargs)

# 示例
INTENT_CLASSIFIER_PROMPT = PromptTemplate(
    name="intent_classifier",
    description="意图分类",
    template="""请分析以下内容的意图：

<content>
{content}
</content>

请返回 JSON 格式：
{{"intent": "意图类型", "confidence": 置信度}}"""
)

# 使用
prompt = INTENT_CLASSIFIER_PROMPT.render(content="请问产品A价格多少？")
```

#### 2. SystemPrompt 类

```python
class SystemPrompt:
    """结构化系统提示词"""

    def __init__(
        self,
        role: str,
        instructions: list = None,
        constraints: list = None,
        examples: list = None,
    ):
        self.role = role
        self.instructions = instructions or []
        self.constraints = constraints or []
        self.examples = examples or []

    def render(self) -> str:
        """生成完整的系统提示词"""
        parts = [f"你是{self.role}"]

        if self.instructions:
            parts.append("\n## 工作指令\n" + "\n".join(f"- {i}" for i in self.instructions))

        if self.constraints:
            parts.append("\n## 约束条件\n" + "\n".join(f"- {c}" for c in self.constraints))

        if self.examples:
            parts.append("\n## 示例\n" + "\n".join(self.examples))

        return "\n".join(parts)

# 示例
INTENT_SYSTEM = SystemPrompt(
    role="一个意图分类专家",
    instructions=["分析输入内容的意图", "返回 JSON 格式"],
    constraints=["只输出 JSON", "不要解释"],
)
```

### 预定义模板

| 模板 | 文件 | 用途 |
|------|------|------|
| `INTENT_CLASSIFIER_PROMPT` | intent.py | 通用意图分类 |
| `EMAIL_INTENT_PROMPT` | intent.py | 邮件意图分类 |
| `ENTITY_EXTRACTION_PROMPT` | extraction.py | 通用实体提取 |
| `INQUIRY_EXTRACTION_PROMPT` | extraction.py | 询价邮件提取 |
| `ORDER_EXTRACTION_PROMPT` | extraction.py | 订单信息提取 |
| `CONTACT_EXTRACTION_PROMPT` | extraction.py | 联系人提取 |

### 使用方法

```python
from app.prompts import INTENT_CLASSIFIER_PROMPT, INTENT_SYSTEM
from app.services.llm_service import llm_service

# 渲染 Prompt
prompt = INTENT_CLASSIFIER_PROMPT.render(content="请问产品A价格多少？")

# 调用 LLM
response = await llm_service.chat(
    message=prompt,
    system_prompt=INTENT_SYSTEM.render(),
    temperature=0.2,  # 分类任务用低温度
)
```

---

## 8.5 Agent 架构

**文件**: `app/agents/`

### 设计思路

Agent 是 LLM + Prompt + Tools 的组合，使用 LangGraph 状态机架构：
- 统一的基类 `BaseAgent`
- 装饰器 `@register_agent` 自动注册
- 支持工具调用和多轮迭代
- 支持同步和流式输出

### 核心组件

#### 1. BaseAgent 基类

```python
from app.agents.base import BaseAgent, AgentState, AgentResult

class MyAgent(BaseAgent):
    name = "my_agent"           # 唯一标识
    description = "Agent 描述"
    prompt_name = "my_prompt"   # 对应的 Prompt 模板名
    tools = ["tool1", "tool2"]  # 可用工具列表
    model = None                # 使用默认模型
    max_iterations = 10         # 最大迭代次数

    async def _get_system_prompt(self) -> str:
        """返回系统提示词"""
        return "你是一个助手..."

    async def process_output(self, state: AgentState) -> dict:
        """处理输出，返回结构化数据"""
        return {"result": state.get("output", "")}
```

#### 2. Agent 注册机制

```python
from app.agents.registry import register_agent, agent_registry

# 使用装饰器自动注册
@register_agent
class EmailAnalyzerAgent(BaseAgent):
    name = "email_analyzer"
    ...

# 通过注册中心调用
result = await agent_registry.run(
    "email_analyzer",
    input_text="邮件内容...",
    input_data={"subject": "询价"},
)

# 列出所有 Agent
agents = agent_registry.list_agents()
```

#### 3. AgentResult 返回结构

```python
@dataclass
class AgentResult:
    success: bool           # 是否成功
    output: str             # 文本输出
    data: dict              # 结构化数据
    iterations: int         # 迭代次数
    tool_calls: list        # 工具调用记录
    error: Optional[str]    # 错误信息
```

### 已注册的 Agent

| Agent | 名称 | 说明 |
|-------|------|------|
| `chat_agent` | 聊天助手 | 多轮对话，支持上下文 |
| `email_analyzer` | 邮件分析 | 分析邮件意图和实体 |
| `intent_classifier` | 意图分类 | 快速分类用户意图 |
| `quote_agent` | 报价助手 | 生成报价方案 |

### 添加新 Agent

1. 在 `app/agents/` 创建新文件
2. 继承 `BaseAgent` 并实现必要方法
3. 使用 `@register_agent` 装饰器
4. 在 `app/agents/__init__.py` 中导入

```python
# app/agents/my_agent.py
from app.agents.base import BaseAgent
from app.agents.registry import register_agent

@register_agent
class MyAgent(BaseAgent):
    name = "my_agent"
    description = "我的自定义 Agent"

    async def process_output(self, state):
        return {"custom_field": state.get("output")}

# app/agents/__init__.py
from app.agents import my_agent  # noqa: F401
```

---

## 9. API 层

**文件**: `app/api/`

### 设计思路

- 每个模块一个路由文件
- 使用 `APIRouter` 分组管理
- 在 `main.py` 中注册路由
- 需要认证的接口使用 `Depends(get_current_user)`

### 路由文件列表

| 文件 | 前缀 | 说明 |
|------|------|------|
| `health.py` | `/health` | 健康检查 |
| `auth.py` | `/api/auth` | 用户认证 |
| `llm.py` | `/api/llm` | LLM 测试 |
| `agents.py` | `/api/agents` | Agent 调用 |
| `chat.py` | `/api/chat` | 聊天会话 |
| `workflows.py` | `/api/workflows` | 工作流管理 |
| `admin.py` | `/admin` | 管理员用户管理 |
| `admin_monitor.py` | `/admin/monitor` | 运行监控 |
| `settings.py` | `/admin/settings` | 系统设置（LLM/邮件/飞书） |

### 健康检查示例

```python
from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "ok"}
```

### 认证接口示例

```python
from fastapi import APIRouter, Depends
from app.core.security import get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])

@router.post("/login")
async def login(request: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    user = await db.execute(select(User).where(User.email == request.email))
    user = user.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    return {
        "access_token": create_access_token({"sub": user.id}),
        "refresh_token": create_refresh_token({"sub": user.id}),
        "token_type": "bearer"
    }

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息（需要登录）"""
    return UserResponse.model_validate(current_user)
```

### LLM 接口示例

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/llm", tags=["LLM"])

@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),  # 需要登录
    llm: LLMService = Depends(get_llm_service)
):
    """普通对话"""
    response = await llm.chat(message=request.message)
    return {"response": response}

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """流式对话（SSE）"""
    async def generate():
        async for chunk in llm_service.chat_stream(message=request.message):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

### 注册路由

在 `main.py` 中：

```python
from app.api import health, auth, llm

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(llm.router)
```

---

## 10. 依赖注入

FastAPI 的依赖注入系统是核心特性。通过 `Depends()` 可以自动处理资源获取和生命周期管理。

### 数据库 Session

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()    # 成功则提交
        except Exception:
            await session.rollback()  # 失败则回滚
            raise
```

使用：`db: AsyncSession = Depends(get_db)`

### Redis 客户端

```python
async def get_redis() -> redis.Redis:
    return redis_client.client
```

使用：`redis = Depends(get_redis)`

### 当前用户

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """从 JWT Token 解析当前用户"""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    user = await db.get(User, payload.get("sub"))
    return user
```

使用：`current_user: User = Depends(get_current_user)`

### 管理员用户

```python
async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取管理员用户，非管理员返回 403"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
```

使用：`admin: User = Depends(get_current_admin_user)`

### LLM 服务

```python
def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    return llm_service
```

使用：`llm: LLMService = Depends(get_llm_service)`

### 依赖链示例

```python
@router.post("/admin/users")
async def create_user(
    request: UserCreate,
    admin: User = Depends(get_current_admin_user),  # 验证管理员
    db: AsyncSession = Depends(get_db),              # 获取数据库
    llm: LLMService = Depends(get_llm_service),      # 获取 LLM
):
    # 依赖自动按顺序解析
    ...
```

---

## 附录：命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | snake_case | `email_service.py` |
| 类名 | PascalCase | `RedisClient` |
| 函数名 | snake_case | `get_cached_user` |
| 变量名 | snake_case | `redis_client` |
| 常量 | UPPER_SNAKE | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| API 路径 | kebab-case | `/health/detailed` |
| Redis Key | colon 分隔 | `user:123:profile` |

---

## 11. 存储层 (OSS)

**文件**: `app/storage/oss.py`

### 设计思路

- 封装阿里云 OSS SDK，提供简单易用的接口
- 使用 `asyncio.to_thread()` 将同步操作转为异步，避免阻塞事件循环
- 支持文件上传、下载、删除、签名 URL 等功能
- 全局单例模式，通过依赖注入使用

### 核心组件

#### OSSClient 类

```python
class OSSClient:
    def __init__(self):
        self.auth = None
        self.bucket = None
        self._initialized = False

    def connect(self) -> bool:
        """建立 OSS 连接"""
        self.auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )
        self.bucket = oss2.Bucket(
            self.auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET
        )
        return True

    async def upload(self, key: str, data: bytes) -> str:
        """上传文件，返回 URL"""
        await asyncio.to_thread(self.bucket.put_object, key, data)
        return f"https://{settings.OSS_BUCKET}.{settings.OSS_ENDPOINT}/{key}"

    async def download(self, key: str) -> bytes:
        """下载文件"""
        result = await asyncio.to_thread(self.bucket.get_object, key)
        return await asyncio.to_thread(result.read)

    def get_signed_url(self, key: str, expires: int = 3600) -> str:
        """生成临时访问 URL"""
        return self.bucket.sign_url("GET", key, expires)

# 全局单例
oss_client = OSSClient()
```

### 使用方法

```python
from app.storage.oss import oss_client

# 上传文件
url = await oss_client.upload("documents/test.pdf", file_content)

# 下载文件
content = await oss_client.download("documents/test.pdf")

# 生成临时链接（1小时有效）
url = oss_client.get_signed_url("documents/test.pdf", expires=3600)

# 检查文件是否存在
exists = await oss_client.exists("documents/test.pdf")
```

### 配置

在 `.env` 中配置：
```bash
OSS_ACCESS_KEY_ID=xxx
OSS_ACCESS_KEY_SECRET=xxx
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET=concord-ai-files
```

---

## 12. 幂等性中间件

**文件**: `app/core/idempotency.py`

### 设计思路

实现三层幂等性防护，防止重复请求：
1. **第一层**：Request ID 快速去重（Redis 缓存）
2. **第二层**：Redis 分布式锁（防止并发重复）
3. **第三层**：数据库唯一约束（最终保障）

### 三种使用方式

#### 方式一：中间件（自动处理）

```python
# main.py
from app.core.idempotency import IdempotencyMiddleware

app.add_middleware(IdempotencyMiddleware)
```

客户端请求时添加幂等 Key：
```bash
curl -X POST http://localhost:8000/api/orders \
  -H "X-Idempotency-Key: order-123-abc" \
  -d '{"product": "A", "quantity": 10}'
```

#### 方式二：装饰器（函数级别）

```python
from app.core.idempotency import idempotent

@idempotent(key_prefix="create_order")
async def create_order(order_data: dict):
    # 同样的 order_data 只会执行一次
    ...

# 自定义 Key 生成
@idempotent(
    key_prefix="process_payment",
    key_func=lambda payment_id, **kwargs: payment_id
)
async def process_payment(payment_id: str, amount: float):
    ...
```

#### 方式三：手动检查

```python
from app.core.idempotency import check_idempotency, mark_processed

async def process_order(order_id: str):
    # 检查是否已处理
    if not await check_idempotency("order", order_id):
        return {"message": "订单已处理"}

    # 处理订单
    result = await do_process_order(order_id)

    # 标记已处理
    await mark_processed("order", order_id, result)
    return result
```

### 核心函数

| 函数 | 说明 |
|------|------|
| `get_cached_response()` | 获取缓存的响应 |
| `cache_response()` | 缓存响应结果 |
| `acquire_lock()` | 获取分布式锁 |
| `release_lock()` | 释放分布式锁 |
| `check_idempotency()` | 检查是否为重复请求 |
| `mark_processed()` | 标记请求已处理 |

---

## 13. 管理员后台 API

**文件**: `app/api/admin.py`

### 设计思路

- 所有接口需要管理员权限（`role=admin`）
- 使用 `Depends(get_current_admin_user)` 统一鉴权
- 提供用户管理和系统统计功能

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/stats` | 系统统计（用户数、活跃数） |
| GET | `/admin/users` | 用户列表（分页、搜索） |
| GET | `/admin/users/{id}` | 获取单个用户 |
| POST | `/admin/users` | 创建新用户 |
| PUT | `/admin/users/{id}` | 更新用户信息 |
| DELETE | `/admin/users/{id}` | 删除用户 |
| POST | `/admin/users/{id}/toggle` | 启用/禁用用户 |
| POST | `/admin/users/{id}/reset-password` | 重置密码 |

### 代码示例

```python
from fastapi import APIRouter, Depends
from app.core.security import get_current_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)]  # 所有接口需要管理员
)

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """获取系统统计"""
    total = await db.execute(select(func.count()).select_from(User))
    active = await db.execute(
        select(func.count()).select_from(User).where(User.is_active == True)
    )
    return {
        "total_users": total.scalar(),
        "active_users": active.scalar()
    }

@router.get("/users")
async def list_users(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取用户列表"""
    query = select(User)
    if search:
        query = query.where(
            User.email.ilike(f"%{search}%") |
            User.name.ilike(f"%{search}%")
        )
    # ... 分页逻辑
```

---

## 14. 前端结构

**目录**: `frontend/src/`

### 项目结构

```
frontend/src/
├── app/                    # Next.js App Router 页面
│   ├── layout.tsx          # 根布局（全局 Provider）
│   ├── page.tsx            # 首页（自动重定向）
│   ├── login/
│   │   └── page.tsx        # 登录页
│   └── admin/
│       ├── layout.tsx      # 管理后台布局（侧边栏+顶栏）
│       ├── page.tsx        # 仪表盘
│       └── users/
│           └── page.tsx    # 用户管理
├── contexts/
│   └── AuthContext.tsx     # 认证上下文（登录状态管理）
└── lib/
    └── api.ts              # API 工具库（封装 fetch）
```

### 认证上下文

```tsx
// contexts/AuthContext.tsx

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 检查 Token 并获取用户信息
    const token = localStorage.getItem('access_token');
    if (token) {
      getCurrentUser().then(setUser).finally(() => setLoading(false));
    }
  }, []);

  const login = async (email: string, password: string) => {
    const response = await api.login({ email, password });
    localStorage.setItem('access_token', response.access_token);
    const user = await getCurrentUser();
    setUser(user);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

### API 工具库

```typescript
// lib/api.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token');

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
  }

  return response.json();
}

// 认证 API
export const login = (data: LoginRequest) =>
  request<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

export const getCurrentUser = () =>
  request<User>('/api/auth/me');

// 管理员 API
export const getStats = () =>
  request<StatsResponse>('/admin/stats');

export const getUsers = (params?: { page?: number; search?: string }) =>
  request<UserListResponse>(`/admin/users?${new URLSearchParams(params)}`);
```

### 页面保护

```tsx
// app/admin/layout.tsx

export default function AdminLayout({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
    if (!loading && user && user.role !== 'admin') {
      router.replace('/');  // 非管理员不能访问
    }
  }, [user, loading]);

  if (loading) return <Loading />;
  if (!user || user.role !== 'admin') return null;

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1">{children}</main>
    </div>
  );
}
```

---

## 15. Temporal 工作流

**目录**: `app/workflows/`

### 设计思路

- 使用 Temporal 实现长时间运行的业务流程
- Workflow 编排流程，Activity 执行实际任务
- 支持 Signal（外部信号）和 Query（状态查询）
- 自动重试、持久化、可视化

### 目录结构

```
app/workflows/
├── __init__.py                # 模块导出
├── worker.py                  # Temporal Worker（监听队列执行任务）
├── client.py                  # Temporal Client（启动/查询/发信号）
├── activities/
│   ├── __init__.py            # Activity 导出
│   └── base.py                # 基础 Activity（通知、日志）
└── definitions/
    ├── __init__.py            # Workflow 导出
    └── approval.py            # 审批工作流
```

### 核心概念

| 概念 | 说明 |
|------|------|
| **Workflow** | 业务流程定义，必须是确定性代码 |
| **Activity** | 实际执行的任务，可以包含 I/O 操作 |
| **Worker** | 监听任务队列，执行 Workflow 和 Activity |
| **Client** | 与 Temporal Server 交互的客户端 |
| **Signal** | 外部发送给运行中 Workflow 的信号 |
| **Query** | 查询运行中 Workflow 的状态（只读） |

### Workflow 定义示例

```python
# workflows/definitions/approval.py

from temporalio import workflow
from datetime import timedelta

@workflow.defn
class ApprovalWorkflow:
    def __init__(self):
        self._status = ApprovalStatus.PENDING
        self._approver_id = None

    @workflow.run
    async def run(self, request: ApprovalRequest) -> ApprovalResult:
        """工作流主函数"""
        # 1. 发送通知
        await workflow.execute_activity(
            send_notification,
            args=[notification_request],
            start_to_close_timeout=timedelta(seconds=30),
        )

        # 2. 等待审批或超时
        await workflow.wait_condition(
            lambda: self._status != ApprovalStatus.PENDING,
            timeout=timedelta(hours=24),
        )

        # 3. 返回结果
        return ApprovalResult(
            status=self._status,
            approver_id=self._approver_id,
        )

    @workflow.signal
    async def approve(self, approver_id: str, comment: str):
        """审批通过信号"""
        self._status = ApprovalStatus.APPROVED
        self._approver_id = approver_id

    @workflow.signal
    async def reject(self, approver_id: str, comment: str):
        """审批拒绝信号"""
        self._status = ApprovalStatus.REJECTED
        self._approver_id = approver_id

    @workflow.query
    def get_status(self) -> ApprovalStatus:
        """查询当前状态"""
        return self._status
```

### Activity 定义示例

```python
# workflows/activities/base.py

from temporalio import activity

@activity.defn
async def send_notification(request: NotificationRequest) -> bool:
    """发送通知 Activity"""
    info = activity.info()
    logger.info(f"[Activity] 发送通知")
    logger.info(f"  Workflow ID: {info.workflow_id}")

    if request.type == NotificationType.EMAIL:
        # 实际发送邮件
        await send_email_impl(request)
        return True

    raise ValueError(f"不支持的通知类型: {request.type}")
```

### Worker 启动

```python
# workflows/worker.py

from temporalio.client import Client
from temporalio.worker import Worker

async def run_worker():
    # 连接 Temporal Server
    client = await Client.connect("localhost:7233")

    # 创建 Worker
    worker = Worker(
        client=client,
        task_queue="concord-main-queue",
        workflows=[ApprovalWorkflow],
        activities=[send_notification, log_workflow_event],
    )

    # 开始监听任务
    await worker.run()

# 启动：python -m app.workflows.worker
```

### Client 使用

```python
# workflows/client.py

from temporalio.client import Client

# 启动工作流
client = await Client.connect("localhost:7233")
handle = await client.start_workflow(
    ApprovalWorkflow.run,
    args=(approval_request,),
    id="approval-order-001",
    task_queue="concord-main-queue",
)

# 发送信号
await handle.signal(ApprovalWorkflow.approve, "user-001", "同意")

# 查询状态
status = await handle.query(ApprovalWorkflow.get_status)

# 等待结果
result = await handle.result()
```

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workflows/approval` | 创建审批工作流 |
| GET | `/api/workflows/{id}/status` | 查询工作流状态 |
| POST | `/api/workflows/{id}/approve` | 审批通过 |
| POST | `/api/workflows/{id}/reject` | 审批拒绝 |
| POST | `/api/workflows/{id}/cancel` | 取消工作流 |

### 配置

```python
# core/config.py
TEMPORAL_HOST: str = "localhost:7233"
TEMPORAL_NAMESPACE: str = "default"
TEMPORAL_TASK_QUEUE: str = "concord-main-queue"
```

### 运维命令

```bash
# 启动 Temporal Server
docker-compose up -d temporal temporal-ui

# 查看 Temporal UI
open http://localhost:8080

# 启动 Worker
cd backend && python -m app.workflows.worker

# 查看 Temporal 日志
docker-compose logs -f temporal
```

### Workflow vs Activity 选择

| 操作 | 放在 Workflow | 放在 Activity |
|------|---------------|---------------|
| 流程控制（if/for） | ✅ | ❌ |
| 等待（sleep/wait） | ✅ | ❌ |
| 数据库读写 | ❌ | ✅ |
| HTTP 请求 | ❌ | ✅ |
| 发送邮件 | ❌ | ✅ |
| LLM 调用 | ❌ | ✅ |

### 注意事项

1. **Workflow 必须是确定性的**：
   - 不能用 `random.random()`，用 `workflow.random()`
   - 不能用 `datetime.now()`，用 `workflow.now()`
   - 不能直接做 I/O，用 Activity

2. **Activity 设计原则**：
   - 每个 Activity 应该是幂等的
   - 设置合理的超时和重试策略
   - 长时间运行的 Activity 需要发送心跳

3. **Signal 注意事项**：
   - Signal 是异步的，发送后不等待处理
   - 多次发送相同 Signal 会多次触发
   - Workflow 应该检查状态避免重复处理

---

## 16. 运维脚本

**目录**: `scripts/`

### 脚本列表

| 脚本 | 说明 |
|------|------|
| `setup.sh` | 一键部署（安装所有依赖） |
| `start.sh` | 启动所有服务 |
| `stop.sh` | 停止所有服务 |
| `restart.sh` | 重启所有服务 |
| `status.sh` | 查看服务状态 |
| `logs.sh` | 查看日志 |
| `migrate.sh` | 数据库迁移 |
| `reset-db.sh` | 重置数据库 |
| `create_admin.py` | 创建管理员账号 |

### 一键部署

```bash
./scripts/setup.sh
```

执行步骤：
1. 检查系统依赖（Docker、Python、Node.js）
2. 创建 `.env` 配置文件
3. 启动 Docker 容器（PostgreSQL、Redis、Temporal）
4. 等待容器就绪
5. 创建 Python 虚拟环境
6. 安装后端依赖
7. 执行数据库迁移
8. 安装前端依赖

### 启动服务

```bash
# 启动所有服务（API 前台运行）
./scripts/start.sh

# 所有服务后台运行
./scripts/start.sh --bg

# 只启动特定服务
./scripts/start.sh --api       # 只启动后端 API
./scripts/start.sh --worker    # 只启动 Temporal Worker
./scripts/start.sh --frontend  # 只启动前端
```

启动的服务：
- Docker 容器（PostgreSQL、Redis、Temporal、Temporal UI）
- Temporal Worker（后台运行，日志在 `logs/worker.log`）
- Next.js 前端（后台运行，日志在 `logs/frontend.log`）
- FastAPI 后端（前台或后台运行）

### 停止服务

```bash
# 停止所有服务（包括 Docker）
./scripts/stop.sh

# 只停止应用，保留 Docker 容器
./scripts/stop.sh --keep
```

### 重启服务

```bash
# 重启所有服务
./scripts/restart.sh

# 后台重启
./scripts/restart.sh --bg

# 只重启特定服务
./scripts/restart.sh --api
./scripts/restart.sh --worker
./scripts/restart.sh --frontend
```

### 查看状态

```bash
./scripts/status.sh
```

输出示例：
```
Docker 容器:
------------------------------------------
NAME                STATUS              PORTS
concord-postgres    Up 2 hours          0.0.0.0:5432->5432/tcp
concord-redis       Up 2 hours          0.0.0.0:6379->6379/tcp
concord-temporal    Up 2 hours          0.0.0.0:7233->7233/tcp

健康检查:
------------------------------------------
  PostgreSQL:     [运行中]
  Redis:          [运行中]
  Temporal:       [运行中]
  Temporal UI:    [运行中] http://localhost:8080
  FastAPI:        [运行中] http://localhost:8000 (PID: 12345)
  Temporal Worker:[运行中] (PID: 12346)
  Frontend:       [运行中] http://localhost:3000 (PID: 12347)
```

### 查看日志

```bash
# 查看所有 Docker 服务日志
./scripts/logs.sh

# 查看特定 Docker 服务
./scripts/logs.sh postgres
./scripts/logs.sh redis
./scripts/logs.sh temporal
./scripts/logs.sh temporal-ui

# 查看应用日志
./scripts/logs.sh api        # FastAPI 日志
./scripts/logs.sh worker     # Temporal Worker 日志
./scripts/logs.sh frontend   # 前端日志
./scripts/logs.sh all        # 所有应用日志
```

### 数据库操作

```bash
# 执行数据库迁移
./scripts/migrate.sh

# 创建新的迁移文件
./scripts/migrate.sh "add user table"

# 重置数据库（删除所有数据）
./scripts/reset-db.sh
```

### 创建管理员

```bash
cd backend
source venv/bin/activate
python ../scripts/create_admin.py
```

默认创建：
- 邮箱: `admin@concordai.com`
- 密码: `admin123456`

### 服务地址一览

| 服务 | 地址 | 说明 |
|------|------|------|
| 后端 API | http://localhost:8000 | FastAPI 服务 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| 前端 | http://localhost:3000 | Next.js 应用 |
| Temporal UI | http://localhost:8080 | 工作流管理界面 |
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存 |
| Temporal | localhost:7233 | 工作流引擎（gRPC） |

### 日志文件位置

| 文件 | 说明 |
|------|------|
| `logs/api.log` | FastAPI 后端日志 |
| `logs/worker.log` | Temporal Worker 日志 |
| `logs/frontend.log` | Next.js 前端日志 |

---

## 17. 系统设置

管理员可以在后台界面配置系统设置，无需修改环境变量或重启服务。

### 17.1 访问设置页面

1. 登录管理后台: http://localhost:3000/admin
2. 点击侧边栏 "系统设置"

### 17.2 LLM 配置

#### 选择默认模型

系统支持以下 LLM 模型：

| 模型 ID | 名称 | 提供商 | 说明 |
|---------|------|--------|------|
| claude-sonnet-4-20250514 | Claude Sonnet 4 | Anthropic | 推荐，性能均衡 |
| claude-3-5-sonnet-20241022 | Claude 3.5 Sonnet | Anthropic | 高性能通用模型 |
| claude-3-opus-20240229 | Claude 3 Opus | Anthropic | 最强大，适合复杂任务 |
| claude-3-haiku-20240307 | Claude 3 Haiku | Anthropic | 最快速，适合简单任务 |
| gpt-4o | GPT-4o | OpenAI | 多模态模型 |
| gpt-4-turbo | GPT-4 Turbo | OpenAI | 更快更便宜 |
| gpt-3.5-turbo | GPT-3.5 Turbo | OpenAI | 性价比高 |

#### 配置 API Key

1. **Anthropic API Key**: 从 https://console.anthropic.com 获取
2. **OpenAI API Key**: 从 https://platform.openai.com 获取

输入 API Key 后点击 "保存配置"。系统会安全存储（只显示部分字符）。

#### 测试连接

点击 "测试连接" 按钮验证配置是否正确。成功会显示模型名称，失败会显示错误信息。

### 17.3 邮件配置

#### SMTP 发件服务器

| 字段 | 说明 | 示例 |
|------|------|------|
| 服务器地址 | SMTP 主机名 | smtp.qq.com |
| 端口 | 通常 465 (SSL) 或 587 (STARTTLS) | 465 |
| 用户名 | 发件邮箱地址 | your@qq.com |
| 密码 | 授权码（不是登录密码） | 从邮箱设置获取 |

#### IMAP 收件服务器

| 字段 | 说明 | 示例 |
|------|------|------|
| 服务器地址 | IMAP 主机名 | imap.qq.com |
| 端口 | 通常 993 (SSL) | 993 |
| 用户名 | 收件邮箱地址 | your@qq.com |
| 密码 | 授权码 | 从邮箱设置获取 |

### 17.4 配置优先级

设置按以下优先级生效：

1. **数据库设置**（最高）- 通过管理后台配置
2. **环境变量** - `.env` 文件中的配置
3. **代码默认值**（最低）- 代码中的默认值

这意味着管理员在后台修改设置后立即生效，无需重启服务。

### 17.5 设置 API

开发者可以通过 API 管理设置（注意：所有设置 API 都在 `/admin/settings` 下）：

```bash
# 获取 LLM 配置
curl http://localhost:8000/admin/settings/llm \
  -H "Authorization: Bearer <token>"

# 更新 LLM 配置
curl -X PUT http://localhost:8000/admin/settings/llm \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"default_model": "claude-3-haiku-20240307"}'

# 测试 LLM 连接
curl -X POST http://localhost:8000/admin/settings/llm/test \
  -H "Authorization: Bearer <token>"

# 获取邮件配置
curl http://localhost:8000/admin/settings/email \
  -H "Authorization: Bearer <token>"
```

---

## 18. Chat 系统

**文件**: `app/api/chat.py`, `app/agents/chat_agent.py`, `app/models/chat.py`

### 18.1 设计思路

Chat 系统支持多轮对话，使用 Redis 缓存上下文，支持 SSE 流式输出。

### 18.2 数据模型

```python
# ChatSession - 会话表
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: str                    # UUID
    user_id: Optional[str]     # 系统用户 ID
    external_user_id: str      # 外部用户 ID（飞书 open_id 等）
    source: str                # 来源：chatbox / feishu
    title: str                 # 会话标题
    agent_id: str              # 使用的 Agent
    is_active: bool            # 是否活跃
    created_at: datetime
    updated_at: datetime

# ChatMessage - 消息表
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: str                    # UUID
    session_id: str            # 关联会话
    role: str                  # user / assistant / system
    content: str               # 消息内容
    tool_calls: Optional[dict] # 工具调用
    status: str                # pending / streaming / completed / failed
    model: Optional[str]       # 使用的模型
    tokens_used: Optional[int] # Token 消耗
    created_at: datetime
```

### 18.3 Chat Agent

ChatAgent 继承自 BaseAgent，使用 LangGraph 状态机架构：

```python
from app.agents.chat_agent import chat_agent

# 同步对话（完整响应）
result = await chat_agent.chat(
    session_id="session-123",
    message="你好",
    model="claude-3-haiku-20240307",
    temperature=0.7,
)
print(result.content)

# 流式对话（逐 token 输出）
async for chunk in chat_agent.chat_stream(
    session_id="session-123",
    message="写一首诗",
):
    print(chunk, end="")

# 也可以通过 Agent Registry 调用
from app.agents.registry import agent_registry

result = await agent_registry.run(
    "chat_agent",
    input_text="你好",
    session_id="session-123",
)
```

#### ChatAgent 类结构

```python
@register_agent
class ChatAgent(BaseAgent):
    name = "chat_agent"
    description = "通用聊天助手，支持多轮对话和工具调用"
    prompt_name = "chat_agent"
    tools = []  # 可通过 enable_tools=True 启用
    model = None  # 使用数据库配置的默认模型
    max_iterations = 5
    max_context_messages = 20  # 上下文保留消息数

    # 支持的方法
    async def chat(session_id, message, ...)      # 同步对话
    async def chat_stream(session_id, message, ...)  # 流式对话
    async def clear_context(session_id)           # 清除上下文
```

### 18.4 SSE 流式 API

```bash
# SSE 流式对话
curl -N http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 返回格式：
# data: {"type": "token", "content": "你"}
# data: {"type": "token", "content": "好"}
# data: {"type": "done", "session_id": "xxx", "message_id": "xxx"}
```

### 18.5 上下文管理

Chat Agent 使用 Redis 缓存上下文，TTL 为 24 小时：

```python
# 上下文存储在 Redis 中
# Key: chat:context:{session_id}
# Value: JSON 格式的消息列表
# TTL: 24 小时

# 手动清除上下文
await chat_agent.clear_context(session_id)
```

---

## 19. 飞书集成

**文件**: `app/adapters/feishu.py`, `app/workers/feishu_worker.py`

### 19.1 设计思路

飞书集成采用 **长连接（WebSocket）** 方式，使用官方 `lark-oapi` SDK：
- 无需公网 IP
- 实时性好
- 连接稳定

### 19.2 飞书客户端

```python
from app.adapters.feishu import FeishuClient

client = FeishuClient(app_id="cli_xxx", app_secret="xxx")

# 发送文本消息
await client.send_text(
    receive_id="ou_xxx",
    receive_id_type="open_id",
    text="你好",
)

# 回复消息
await client.reply_message(
    message_id="om_xxx",
    msg_type="text",
    content='{"text": "收到"}',
)

# 测试连接
is_ok = await client.test_connection()
```

### 19.3 飞书适配器

```python
from app.adapters.feishu import FeishuAdapter

adapter = FeishuAdapter()

# 将飞书消息转换为统一事件
event = await adapter.to_unified_event(raw_feishu_data)

# 发送响应
await adapter.send_response(event, response, content="回复内容")
```

### 19.4 统一事件模型

```python
from app.schemas.event import UnifiedEvent

event = UnifiedEvent(
    event_type="chat",
    source="feishu",
    source_id="om_xxx",           # 飞书消息 ID
    user_external_id="ou_xxx",    # 飞书 open_id
    session_id="oc_xxx",          # 飞书 chat_id
    content="你好",
)
```

### 19.5 飞书 Worker 启动

```bash
# 方式一：命令行启动
cd backend
python -m app.workers.feishu_worker --app-id cli_xxx --app-secret xxx

# 方式二：使用脚本（后台运行，需设置环境变量）
export FEISHU_APP_ID=cli_xxx
export FEISHU_APP_SECRET=xxx
./scripts/start.sh --feishu --bg

# 方式三：Docker Compose
docker-compose --profile feishu up -d feishu-worker

# 查看日志
./scripts/logs.sh feishu
```

### 19.6 飞书配置

在管理后台配置飞书：

1. 访问 http://localhost:3000/admin/settings/feishu
2. 填写 App ID 和 App Secret
3. 点击「测试连接」验证
4. 启用飞书机器人
5. 启动飞书 Worker

或通过 API 配置：

```bash
# 更新飞书配置
curl -X PUT http://localhost:8000/admin/settings/feishu \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "app_id": "cli_xxx",
    "app_secret": "xxx"
  }'

# 测试连接
curl -X POST http://localhost:8000/admin/settings/feishu/test \
  -H "Authorization: Bearer <token>"
```

### 19.7 飞书开放平台配置步骤

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 添加「机器人」能力
5. 配置事件订阅（消息接收权限）
6. 发布应用

---

*最后更新: 2026-01-30*

---

## 附录：完整 API 路由列表

### 公开接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/refresh` | 刷新 Token |

### 需认证接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/auth/me` | 获取当前用户 |
| POST | `/api/llm/chat` | LLM 对话 |
| POST | `/api/llm/stream` | LLM 流式对话 |
| GET | `/api/agents` | 列出所有 Agent |
| GET | `/api/agents/{name}` | 获取 Agent 详情 |
| POST | `/api/agents/{name}/run` | 执行 Agent |
| POST | `/api/agents/analyze/email` | 邮件分析 |
| POST | `/api/agents/classify/intent` | 意图分类 |
| POST | `/api/chat/sessions` | 创建会话 |
| GET | `/api/chat/sessions` | 获取会话列表 |
| GET | `/api/chat/sessions/{id}/messages` | 获取消息历史 |
| DELETE | `/api/chat/sessions/{id}` | 删除会话 |
| POST | `/api/chat/stream` | 流式聊天 |
| POST | `/api/workflows/approval` | 创建审批 |
| GET | `/api/workflows/{id}/status` | 查询状态 |
| POST | `/api/workflows/{id}/approve` | 审批通过 |
| POST | `/api/workflows/{id}/reject` | 审批拒绝 |

### 管理员接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/stats` | 系统统计 |
| GET | `/admin/users` | 用户列表 |
| POST | `/admin/users` | 创建用户 |
| GET | `/admin/users/{id}` | 获取用户 |
| PUT | `/admin/users/{id}` | 更新用户 |
| DELETE | `/admin/users/{id}` | 删除用户 |
| POST | `/admin/users/{id}/toggle` | 启用/禁用用户 |
| POST | `/admin/users/{id}/reset-password` | 重置密码 |
| GET | `/admin/monitor/summary` | 监控概览 |
| GET | `/admin/monitor/workflows` | 工作流列表 |
| GET | `/admin/monitor/executions` | 执行记录 |
| GET | `/admin/settings/llm` | 获取 LLM 配置 |
| PUT | `/admin/settings/llm` | 更新 LLM 配置 |
| POST | `/admin/settings/llm/test` | 测试 LLM 连接 |
| GET | `/admin/settings/email` | 获取邮件配置 |
| PUT | `/admin/settings/email` | 更新邮件配置 |
| GET | `/admin/settings/feishu` | 获取飞书配置 |
| PUT | `/admin/settings/feishu` | 更新飞书配置 |
| POST | `/admin/settings/feishu/test` | 测试飞书连接 |
| GET | `/admin/settings/feishu/status` | 飞书状态 |
| POST | `/admin/settings/feishu/start` | 启动飞书 Worker |
| POST | `/admin/settings/feishu/stop` | 停止飞书 Worker |
