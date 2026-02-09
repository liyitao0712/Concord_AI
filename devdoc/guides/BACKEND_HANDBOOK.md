# Concord AI - 后端开发手册

> 后端核心代码的设计思路和使用方法
> 拆分自: MANUAL.md §1-6, §9-13, §18-19

---

## 目录

1. [项目结构](#1-项目结构)
2. [配置管理](#2-配置管理)
3. [日志系统](#3-日志系统)
4. [数据库层](#4-数据库层)
5. [Redis 缓存层](#5-redis-缓存层)
6. [认证系统](#6-认证系统)
7. [API 层](#7-api-层)
8. [依赖注入](#8-依赖注入)
9. [存储层 (OSS)](#9-存储层-oss)
10. [幂等性中间件](#10-幂等性中间件)
11. [管理员后台 API](#11-管理员后台-api)
12. [Chat 系统](#12-chat-系统)
13. [飞书集成](#13-飞书集成)

**相关文档**：
- LLM 服务 / Prompt 模板 → [LLM 管理手册](LLM_GUIDE.md)
- Agent 架构 → [Agent 文档](../agents/README.md)
- Celery 任务队列 → [Celery 指南](CELERY_GUIDE.md)
- Temporal 工作流 → [Temporal 指南](TEMPORAL_GUIDE.md)
- 运维脚本 / 系统设置 → [运维手册](OPS_SCRIPTS.md)

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
| 连接管理 | 已实现 | connect/disconnect |
| 基础操作 | 已实现 | get/set/delete/exists |
| 过期控制 | 已实现 | expire/ttl |
| 健康检查 | 已实现 | ping |
| 缓存装饰器 | 待开发 | 自动缓存函数结果 |
| Session 存储 | 待开发 | 用户会话管理 |
| 分布式锁 | 待开发 | 防止并发冲突 |
| 消息队列 | 待开发 | 简单的 pub/sub |

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

## 7. API 层

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

## 8. 依赖注入

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

## 9. 存储层 (OSS)

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

## 10. 幂等性中间件

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

## 11. 管理员后台 API

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

## 12. Chat 系统

**文件**: `app/api/chat.py`, `app/agents/chat_agent.py`, `app/models/chat.py`

### 12.1 设计思路

Chat 系统支持多轮对话，使用 Redis 缓存上下文，支持 SSE 流式输出。

### 12.2 数据模型

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

### 12.3 Chat Agent

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

### 12.4 SSE 流式 API

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

### 12.5 上下文管理

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

## 13. 飞书集成

**文件**: `app/adapters/feishu.py`, `app/workers/feishu_worker.py`

### 13.1 设计思路

飞书集成采用 **长连接（WebSocket）** 方式，使用官方 `lark-oapi` SDK：
- 无需公网 IP
- 实时性好
- 连接稳定

### 13.2 飞书客户端

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

### 13.3 飞书适配器

```python
from app.adapters.feishu import FeishuAdapter

adapter = FeishuAdapter()

# 将飞书消息转换为统一事件
event = await adapter.to_unified_event(raw_feishu_data)

# 发送响应
await adapter.send_response(event, response, content="回复内容")
```

### 13.4 统一事件模型

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

### 13.5 飞书 Worker 启动

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

### 13.6 飞书配置

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

### 13.7 飞书开放平台配置步骤

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 添加「机器人」能力
5. 配置事件订阅（消息接收权限）
6. 发布应用

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

---

*拆分自 MANUAL.md | 最后更新: 2026-02-01*
