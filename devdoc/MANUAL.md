# Concord AI - 代码手册

> 详细讲解核心代码的设计思路和使用方法

---

## 目录

1. [项目结构](#1-项目结构)
2. [配置管理](#2-配置管理)
3. [数据库层](#3-数据库层)
4. [Redis 缓存层](#4-redis-缓存层)
5. [API 层](#5-api-层)
6. [依赖注入](#6-依赖注入)

---

## 1. 项目结构

```
backend/app/
├── main.py           # FastAPI 入口，应用生命周期管理
├── api/              # API 路由层
│   └── health.py     # 健康检查接口
├── core/             # 核心基础设施
│   ├── config.py     # 配置管理
│   ├── database.py   # 数据库连接
│   └── redis.py      # Redis 连接
├── models/           # SQLAlchemy 数据模型（待开发）
├── schemas/          # Pydantic 请求/响应模式（待开发）
├── services/         # 业务逻辑层（待开发）
└── agents/           # AI Agent（待开发）
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

## 3. 数据库层

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

## 4. Redis 缓存层

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

## 5. API 层

**文件**: `app/api/health.py`

### 设计思路

- 每个模块一个路由文件
- 使用 `APIRouter` 分组管理
- 在 `main.py` 中注册路由

### 代码讲解

```python
from fastapi import APIRouter

router = APIRouter(tags=["Health"])  # 分组标签

@router.get("/health")
async def health_check():
    """基础健康检查"""
    return {"status": "ok"}

@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """详细健康检查，包含数据库和 Redis 状态"""
    health = {"status": "ok", "services": {}}

    # 检查 PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        health["services"]["database"] = "connected"
    except Exception as e:
        health["services"]["database"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # 检查 Redis
    try:
        await redis_client.client.ping()
        health["services"]["redis"] = "connected"
    except Exception as e:
        health["services"]["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"

    return health
```

### 注册路由

在 `main.py` 中：

```python
from app.api import health

app.include_router(health.router)
```

---

## 6. 依赖注入

FastAPI 的依赖注入系统是核心特性，本项目中的使用：

### 数据库 Session

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

使用：`db: AsyncSession = Depends(get_db)`

### Redis 客户端

```python
async def get_redis() -> redis.Redis:
    return redis_client.client
```

使用：`redis = Depends(get_redis)`

### 未来：认证依赖

```python
# M2 认证模块将实现
async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = verify_token(token)
    return user
```

使用：`user: User = Depends(get_current_user)`

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

*最后更新: 2026-01-29*
