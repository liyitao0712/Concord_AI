# app/core/security.py
# 安全认证模块
#
# 功能说明：
# 1. 密码加密和验证（使用 bcrypt）
# 2. JWT Token 生成和验证
# 3. 提供 FastAPI 依赖注入函数获取当前用户
#
# JWT 认证流程：
# ┌─────────────────────────────────────────────────────────────┐
# │                      JWT 认证流程                            │
# ├─────────────────────────────────────────────────────────────┤
# │  1. 用户登录                                                 │
# │     POST /api/auth/login {email, password}                  │
# │              ↓                                               │
# │  2. 验证密码                                                 │
# │     verify_password(password, user.password_hash)           │
# │              ↓                                               │
# │  3. 生成 Token                                               │
# │     access_token  = create_access_token()   (15分钟)        │
# │     refresh_token = create_refresh_token()  (7天)           │
# │              ↓                                               │
# │  4. 返回给客户端                                             │
# │     {access_token, refresh_token, token_type: "bearer"}     │
# │              ↓                                               │
# │  5. 客户端请求时携带 Token                                   │
# │     Authorization: Bearer <access_token>                    │
# │              ↓                                               │
# │  6. 服务端验证 Token                                         │
# │     get_current_user() -> User                              │
# └─────────────────────────────────────────────────────────────┘

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger

# 获取当前模块的 logger
logger = get_logger(__name__)


# ==================== 密码加密配置 ====================

# 创建密码上下文，使用 bcrypt 算法
# bcrypt 是目前最安全的密码哈希算法之一：
# - 自带盐值（salt），防止彩虹表攻击
# - 可调节计算强度（通过 rounds 参数）
# - 单向不可逆
pwd_context = CryptContext(
    schemes=["bcrypt"],  # 使用 bcrypt 算法
    deprecated="auto"     # 自动处理旧算法迁移
)


# ==================== OAuth2 配置 ====================

# OAuth2PasswordBearer 告诉 FastAPI：
# - Token 应该从请求头 Authorization: Bearer <token> 中获取
# - tokenUrl 是获取 token 的接口地址（用于 Swagger 文档）
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",  # 登录接口地址
    auto_error=True               # Token 无效时自动返回 401 错误
)


# ==================== 密码处理函数 ====================

def hash_password(password: str) -> str:
    """
    对密码进行哈希加密

    使用 bcrypt 算法将明文密码转换为哈希值
    每次调用即使相同的密码也会生成不同的哈希值（因为盐值不同）

    Args:
        password: 明文密码

    Returns:
        str: 密码的哈希值

    示例：
        hash1 = hash_password("123456")
        # 结果类似：$2b$12$xxx...（60个字符）
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否正确

    将用户输入的明文密码与数据库存储的哈希值进行比对

    Args:
        plain_password: 用户输入的明文密码
        hashed_password: 数据库存储的哈希值

    Returns:
        bool: 密码正确返回 True，否则返回 False

    示例：
        is_valid = verify_password("123456", user.password_hash)
        if is_valid:
            print("密码正确")
    """
    return pwd_context.verify(plain_password, hashed_password)


# ==================== JWT Token 函数 ====================

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 Access Token

    Access Token 用于访问受保护的 API
    有效期较短（默认 15 分钟），提高安全性

    Args:
        data: 要编码到 Token 中的数据，通常包含用户 ID
              例如：{"sub": "user_id"}
        expires_delta: 可选的过期时间，默认使用配置值

    Returns:
        str: JWT Token 字符串

    Token 结构：
        header.payload.signature

        header: {"alg": "HS256", "typ": "JWT"}
        payload: {"sub": "user_id", "exp": 过期时间戳, "type": "access"}
        signature: 使用密钥签名
    """
    # 复制数据，避免修改原始字典
    to_encode = data.copy()

    # 计算过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # 添加过期时间和 Token 类型到 payload
    to_encode.update({
        "exp": expire,      # 过期时间
        "type": "access"    # Token 类型（区分 access 和 refresh）
    })

    # 使用密钥和算法生成 JWT
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    logger.debug(f"创建 Access Token，过期时间: {expire}")
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建 Refresh Token

    Refresh Token 用于刷新 Access Token
    有效期较长（默认 7 天），存储在客户端

    当 Access Token 过期时，客户端可以用 Refresh Token
    获取新的 Access Token，而不需要重新登录

    Args:
        data: 要编码到 Token 中的数据
        expires_delta: 可选的过期时间

    Returns:
        str: JWT Token 字符串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "refresh"  # 标记为 refresh token
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    logger.debug(f"创建 Refresh Token，过期时间: {expire}")
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    解码并验证 JWT Token

    检查 Token 是否有效（签名正确、未过期）

    Args:
        token: JWT Token 字符串

    Returns:
        dict: 解码后的 payload 数据，验证失败返回 None

    可能的失败原因：
        - Token 格式错误
        - 签名验证失败（被篡改）
        - Token 已过期
    """
    try:
        # 解码 Token，会自动验证签名和过期时间
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        # Token 验证失败
        logger.warning(f"Token 验证失败: {e}")
        return None


# ==================== FastAPI 依赖注入函数 ====================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户（FastAPI 依赖注入）

    这个函数作为依赖项注入到需要认证的路由中
    自动从请求头提取 Token 并验证，返回用户对象

    Args:
        token: 从请求头自动提取的 Token（由 oauth2_scheme 处理）
        db: 数据库会话（由 get_db 提供）

    Returns:
        User: 当前登录的用户对象

    Raises:
        HTTPException: Token 无效或用户不存在时返回 401 错误

    使用示例：
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    # 定义认证失败时的异常
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},  # 告诉客户端使用 Bearer 认证
    )

    # 解码 Token
    payload = decode_token(token)
    if payload is None:
        logger.warning("Token 解码失败")
        raise credentials_exception

    # 检查是否是 Access Token（不是 Refresh Token）
    if payload.get("type") != "access":
        logger.warning("尝试使用非 Access Token 访问接口")
        raise credentials_exception

    # 从 payload 获取用户 ID
    # "sub"（subject）是 JWT 标准字段，存储用户标识
    user_id: str = payload.get("sub")
    if user_id is None:
        logger.warning("Token 中没有用户 ID")
        raise credentials_exception

    # 从数据库查询用户
    # 导入放在这里避免循环导入
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning(f"用户不存在: {user_id}")
        raise credentials_exception

    # 检查用户是否被禁用
    if not user.is_active:
        logger.warning(f"用户已被禁用: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    logger.debug(f"用户认证成功: {user.email}")
    return user


async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    获取当前活跃用户

    在 get_current_user 基础上额外检查用户是否激活
    （实际上 get_current_user 已经检查了，这里是为了语义清晰）

    Args:
        current_user: 当前用户（由 get_current_user 提供）

    Returns:
        User: 当前活跃的用户对象
    """
    return current_user


async def get_current_admin_user(
    current_user = Depends(get_current_user)
):
    """
    获取当前管理员用户

    用于需要管理员权限的接口

    Args:
        current_user: 当前用户

    Returns:
        User: 当前用户（如果是管理员）

    Raises:
        HTTPException: 如果不是管理员，返回 403 错误

    使用示例：
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: str,
            admin: User = Depends(get_current_admin_user)
        ):
            # 只有管理员能执行这个操作
            pass
    """
    if not current_user.is_admin:
        logger.warning(f"非管理员尝试访问管理接口: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user
