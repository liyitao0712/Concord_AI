# app/core/idempotency.py
# 幂等性中间件
#
# 功能说明：
# 实现三层幂等性防护，防止重复请求导致的重复操作：
# 1. 第一层：Request ID 快速去重（基于请求头）
# 2. 第二层：Redis 分布式锁（防止并发重复）
# 3. 第三层：数据库唯一约束（最终保障）
#
# 什么是幂等性？
# 幂等性是指：同一个操作执行一次和执行多次的效果是一样的
# 例如：用户点击"提交订单"按钮两次，应该只创建一个订单
#
# 使用场景：
# - 创建订单
# - 支付操作
# - 发送邮件
# - 任何不希望重复执行的操作
#
# 使用方法：
#   # 方式一：使用装饰器
#   @idempotent(key_prefix="create_order")
#   async def create_order(order_data: dict):
#       ...
#
#   # 方式二：使用中间件
#   app.add_middleware(IdempotencyMiddleware)
#
#   # 方式三：手动检查
#   if await check_idempotency("order", order_id):
#       return "已处理"
#
# 客户端配合：
# 客户端在请求头中添加 X-Request-ID 或 X-Idempotency-Key
# 例如：X-Idempotency-Key: order-123-abc

import hashlib
import functools
from typing import Optional, Callable, Any
from datetime import timedelta

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

from app.core.redis import redis_client
from app.core.logging import get_logger

# 获取当前模块的 logger
logger = get_logger(__name__)

# ==================== 配置常量 ====================

# 幂等 Key 的默认过期时间（秒）
# 设置为 5 分钟，即同一个请求在 5 分钟内不会被重复处理
DEFAULT_IDEMPOTENCY_TTL = 300

# Redis Key 前缀
IDEMPOTENCY_KEY_PREFIX = "idempotent:"

# 分布式锁前缀
LOCK_KEY_PREFIX = "lock:"

# 分布式锁默认超时时间（秒）
DEFAULT_LOCK_TIMEOUT = 30


# ==================== 第一层：Request ID 快速去重 ====================

async def get_cached_response(idempotency_key: str) -> Optional[dict]:
    """
    获取缓存的响应

    如果之前已经处理过相同的请求，直接返回缓存的结果

    Args:
        idempotency_key: 幂等 Key

    Returns:
        dict: 缓存的响应数据，如果不存在返回 None

    工作原理：
    1. 根据 idempotency_key 从 Redis 查找缓存
    2. 如果存在，返回缓存的响应状态码和数据
    3. 如果不存在，返回 None，表示这是新请求
    """
    cache_key = f"{IDEMPOTENCY_KEY_PREFIX}{idempotency_key}"

    try:
        cached = await redis_client.get(cache_key)
        if cached:
            logger.debug(f"命中幂等缓存: {idempotency_key}")
            import json
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"读取幂等缓存失败: {e}")

    return None


async def cache_response(
    idempotency_key: str,
    status_code: int,
    response_data: Any,
    ttl: int = DEFAULT_IDEMPOTENCY_TTL
) -> None:
    """
    缓存响应结果

    将请求的响应结果缓存到 Redis，用于后续的重复请求直接返回

    Args:
        idempotency_key: 幂等 Key
        status_code: HTTP 状态码
        response_data: 响应数据
        ttl: 缓存过期时间（秒）

    工作原理：
    1. 将响应数据序列化为 JSON
    2. 存储到 Redis，设置过期时间
    3. 后续相同请求会直接返回这个缓存
    """
    cache_key = f"{IDEMPOTENCY_KEY_PREFIX}{idempotency_key}"

    try:
        import json
        cache_data = json.dumps({
            "status_code": status_code,
            "data": response_data
        })
        await redis_client.set(cache_key, cache_data, ex=ttl)
        logger.debug(f"缓存幂等响应: {idempotency_key}, TTL: {ttl}s")
    except Exception as e:
        logger.warning(f"缓存幂等响应失败: {e}")


async def is_duplicate_request(idempotency_key: str) -> bool:
    """
    检查是否为重复请求

    快速判断请求是否已经处理过

    Args:
        idempotency_key: 幂等 Key

    Returns:
        bool: True 表示是重复请求，False 表示是新请求
    """
    cache_key = f"{IDEMPOTENCY_KEY_PREFIX}{idempotency_key}"
    return await redis_client.exists(cache_key)


# ==================== 第二层：Redis 分布式锁 ====================

async def acquire_lock(
    lock_key: str,
    timeout: int = DEFAULT_LOCK_TIMEOUT
) -> bool:
    """
    获取分布式锁

    使用 Redis SET NX 命令实现分布式锁
    确保同一时刻只有一个请求在处理特定操作

    Args:
        lock_key: 锁的 Key
        timeout: 锁的超时时间（秒），超时后自动释放

    Returns:
        bool: True 表示获取锁成功，False 表示获取失败（有其他请求在处理）

    工作原理：
    1. 使用 SET NX（Not Exists）命令，只有当 Key 不存在时才设置
    2. 同时设置过期时间，防止死锁
    3. 如果返回 True，表示获取锁成功
    4. 如果返回 False，表示锁已被其他请求持有

    使用示例：
        lock_key = f"lock:order:{order_id}"
        if await acquire_lock(lock_key):
            try:
                # 执行业务逻辑
                ...
            finally:
                await release_lock(lock_key)
        else:
            # 其他请求正在处理
            raise HTTPException(409, "请求正在处理中")
    """
    full_key = f"{LOCK_KEY_PREFIX}{lock_key}"

    try:
        # SET NX: 只有当 Key 不存在时才设置
        # EX: 设置过期时间
        result = await redis_client.set(full_key, "1", nx=True, ex=timeout)
        if result:
            logger.debug(f"获取锁成功: {lock_key}")
        return bool(result)
    except Exception as e:
        logger.warning(f"获取锁失败: {lock_key}, 错误: {e}")
        return False


async def release_lock(lock_key: str) -> bool:
    """
    释放分布式锁

    Args:
        lock_key: 锁的 Key

    Returns:
        bool: True 表示释放成功

    注意：
    - 只有锁的持有者才应该释放锁
    - 简单实现中直接删除 Key，生产环境可能需要更安全的实现
    """
    full_key = f"{LOCK_KEY_PREFIX}{lock_key}"

    try:
        await redis_client.delete(full_key)
        logger.debug(f"释放锁成功: {lock_key}")
        return True
    except Exception as e:
        logger.warning(f"释放锁失败: {lock_key}, 错误: {e}")
        return False


# ==================== 幂等性中间件 ====================

class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    幂等性中间件

    自动处理带有幂等 Key 的请求，实现请求去重

    工作流程：
    1. 检查请求头是否包含 X-Idempotency-Key 或 X-Request-ID
    2. 如果有，检查是否为重复请求
    3. 如果是重复请求，直接返回缓存的响应
    4. 如果不是，尝试获取分布式锁
    5. 获取锁成功后处理请求
    6. 处理完成后缓存响应并释放锁

    配置方法：
        app.add_middleware(IdempotencyMiddleware)

    客户端使用：
        # 在请求头中添加幂等 Key
        headers = {"X-Idempotency-Key": "unique-request-id-123"}
        response = requests.post(url, headers=headers, json=data)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        处理请求

        这是中间件的核心方法，每个请求都会经过这里
        """
        # 只对 POST/PUT/PATCH/DELETE 等修改操作启用幂等性检查
        # GET 请求本身就是幂等的，不需要检查
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        # 获取幂等 Key
        # 优先使用 X-Idempotency-Key，其次使用 X-Request-ID
        idempotency_key = (
            request.headers.get("X-Idempotency-Key") or
            request.headers.get("X-Request-ID")
        )

        # 如果没有提供幂等 Key，直接处理请求
        if not idempotency_key:
            return await call_next(request)

        # 生成完整的幂等 Key（包含请求路径，确保不同接口的 Key 不冲突）
        full_key = f"{request.url.path}:{idempotency_key}"

        # 第一层：检查缓存
        cached = await get_cached_response(full_key)
        if cached:
            logger.info(f"幂等请求命中缓存: {full_key}")
            return JSONResponse(
                status_code=cached["status_code"],
                content=cached["data"]
            )

        # 第二层：获取分布式锁
        if not await acquire_lock(full_key):
            # 无法获取锁，说明有相同请求正在处理
            logger.warning(f"幂等请求冲突，无法获取锁: {full_key}")
            return JSONResponse(
                status_code=409,  # Conflict
                content={"detail": "请求正在处理中，请稍后重试"}
            )

        try:
            # 处理请求
            response = await call_next(request)

            # 缓存成功响应（只缓存 2xx 状态码）
            if 200 <= response.status_code < 300:
                # 读取响应体
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                # 尝试解析为 JSON
                try:
                    import json
                    response_data = json.loads(body.decode())
                except:
                    response_data = body.decode()

                # 缓存响应
                await cache_response(full_key, response.status_code, response_data)

                # 重新构建响应（因为我们已经消费了 body_iterator）
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )

            return response

        finally:
            # 无论成功失败，都释放锁
            await release_lock(full_key)


# ==================== 幂等性装饰器 ====================

def idempotent(
    key_prefix: str,
    key_func: Optional[Callable[..., str]] = None,
    ttl: int = DEFAULT_IDEMPOTENCY_TTL,
    lock_timeout: int = DEFAULT_LOCK_TIMEOUT
):
    """
    幂等性装饰器

    用于装饰需要幂等性保障的函数

    Args:
        key_prefix: 幂等 Key 前缀，用于区分不同的业务场景
        key_func: 生成幂等 Key 的函数，接收被装饰函数的参数
                  如果不指定，会使用参数的哈希值
        ttl: 幂等 Key 的过期时间（秒）
        lock_timeout: 分布式锁的超时时间（秒）

    Returns:
        装饰后的函数

    使用示例：
        # 使用默认 Key 生成
        @idempotent(key_prefix="create_order")
        async def create_order(order_data: dict):
            ...

        # 自定义 Key 生成函数
        @idempotent(
            key_prefix="process_payment",
            key_func=lambda payment_id, **kwargs: payment_id
        )
        async def process_payment(payment_id: str, amount: float):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 生成幂等 Key
            if key_func:
                # 使用自定义函数生成 Key
                key_suffix = key_func(*args, **kwargs)
            else:
                # 使用参数哈希生成 Key
                key_suffix = _generate_key_from_args(*args, **kwargs)

            idempotency_key = f"{key_prefix}:{key_suffix}"

            # 第一层：检查缓存
            cached = await get_cached_response(idempotency_key)
            if cached:
                logger.info(f"幂等函数命中缓存: {idempotency_key}")
                return cached["data"]

            # 第二层：获取分布式锁
            if not await acquire_lock(idempotency_key, lock_timeout):
                raise HTTPException(
                    status_code=409,
                    detail="请求正在处理中，请稍后重试"
                )

            try:
                # 执行原函数
                result = await func(*args, **kwargs)

                # 缓存结果
                await cache_response(idempotency_key, 200, result, ttl)

                return result

            finally:
                # 释放锁
                await release_lock(idempotency_key)

        return wrapper
    return decorator


def _generate_key_from_args(*args, **kwargs) -> str:
    """
    根据函数参数生成唯一 Key

    将参数序列化后计算 MD5 哈希，作为幂等 Key 的一部分

    Args:
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        str: 参数的哈希值
    """
    import json

    # 将参数转换为可序列化的格式
    try:
        # 尝试直接序列化
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    except:
        # 如果失败，使用字符串表示
        data = str(args) + str(kwargs)

    # 计算 MD5 哈希
    return hashlib.md5(data.encode()).hexdigest()[:16]


# ==================== 辅助函数 ====================

async def check_idempotency(
    key_prefix: str,
    key_suffix: str,
    ttl: int = DEFAULT_IDEMPOTENCY_TTL
) -> bool:
    """
    手动检查并标记幂等性

    用于不想使用装饰器或中间件的场景，手动进行幂等性检查

    Args:
        key_prefix: Key 前缀
        key_suffix: Key 后缀（业务 ID）
        ttl: 过期时间（秒）

    Returns:
        bool: True 表示是新请求（可以处理），False 表示是重复请求（应该跳过）

    使用示例：
        async def process_order(order_id: str):
            # 检查是否已处理
            if not await check_idempotency("order", order_id):
                return {"message": "订单已处理"}

            # 处理订单
            ...

            # 处理完成后标记
            await mark_processed("order", order_id)
    """
    idempotency_key = f"{key_prefix}:{key_suffix}"

    # 使用 SET NX 原子操作检查并标记
    cache_key = f"{IDEMPOTENCY_KEY_PREFIX}{idempotency_key}"
    result = await redis_client.set(cache_key, "processing", nx=True, ex=ttl)

    if result:
        logger.debug(f"幂等性检查通过: {idempotency_key}")
        return True
    else:
        logger.debug(f"幂等性检查失败（重复）: {idempotency_key}")
        return False


async def mark_processed(
    key_prefix: str,
    key_suffix: str,
    result: Any = None,
    ttl: int = DEFAULT_IDEMPOTENCY_TTL
) -> None:
    """
    标记请求已处理

    配合 check_idempotency 使用，在处理完成后更新缓存状态

    Args:
        key_prefix: Key 前缀
        key_suffix: Key 后缀（业务 ID）
        result: 处理结果（可选）
        ttl: 过期时间（秒）
    """
    idempotency_key = f"{key_prefix}:{key_suffix}"
    await cache_response(idempotency_key, 200, result or {"status": "processed"}, ttl)
