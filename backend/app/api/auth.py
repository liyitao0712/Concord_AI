# app/api/auth.py
# 认证 API 路由
#
# 功能说明：
# 1. 用户注册
# 2. 用户登录
# 3. Token 刷新
# 4. 获取当前用户信息
#
# API 列表：
# ┌─────────────────────────────────────────────────────────────┐
# │  方法  │  路径                    │  说明                   │
# ├────────┼─────────────────────────┼────────────────────────┤
# │  POST  │  /api/auth/register     │  用户注册               │
# │  POST  │  /api/auth/login        │  用户登录               │
# │  POST  │  /api/auth/refresh      │  刷新 Token            │
# │  GET   │  /api/auth/me           │  获取当前用户信息       │
# └─────────────────────────────────────────────────────────────┘

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    TokenRefresh,
    MessageResponse,
)


# 获取当前模块的 logger
logger = get_logger(__name__)

# 创建路由器
# prefix: 所有路由都会添加 /api/auth 前缀
# tags: 在 API 文档中分组显示
router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ==================== 用户注册 ====================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register",
    description="Create new user account, email must be unique"
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    用户注册接口

    创建新用户账号，需要提供：
    - 邮箱（必须唯一）
    - 密码（至少 6 位）
    - 名称

    Args:
        user_data: 用户注册数据
        db: 数据库会话（自动注入）

    Returns:
        UserResponse: 创建成功的用户信息

    Raises:
        HTTPException: 邮箱已存在时返回 400 错误

    请求示例：
        POST /api/auth/register
        {
            "email": "user@example.com",
            "password": "123456",
            "name": "张三"
        }

    响应示例：
        {
            "id": "uuid",
            "email": "user@example.com",
            "name": "张三",
            "role": "user",
            "is_active": true,
            "created_at": "2026-01-30T12:00:00"
        }
    """
    logger.info(f"用户注册请求: {user_data.email}")

    # 检查邮箱是否已存在
    # select(User).where(User.email == ...) 生成 SQL:
    # SELECT * FROM users WHERE email = '...'
    existing_user = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if existing_user.scalar_one_or_none():
        logger.warning(f"注册失败，邮箱已存在: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 创建新用户
    # 注意：密码需要哈希处理，不存储明文
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        name=user_data.name,
    )

    # 添加到数据库并提交
    db.add(user)
    await db.commit()
    # 刷新对象，获取数据库生成的字段（如 id、created_at）
    await db.refresh(user)

    logger.info(f"用户注册成功: {user.email}, ID: {user.id}")
    return user


# ==================== 用户登录 ====================

@router.post(
    "/login",
    response_model=Token,
    summary="Login",
    description="Login with email and password, returns JWT Token"
)
async def login(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    用户登录接口

    验证邮箱和密码，返回 JWT Token

    Args:
        user_data: 登录数据（邮箱和密码）
        db: 数据库会话

    Returns:
        Token: 包含 access_token 和 refresh_token

    Raises:
        HTTPException: 邮箱或密码错误时返回 401 错误

    请求示例：
        POST /api/auth/login
        {
            "email": "user@example.com",
            "password": "123456"
        }

    响应示例：
        {
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "token_type": "bearer"
        }

    使用说明：
        登录成功后，在后续请求的 Header 中添加：
        Authorization: Bearer <access_token>
    """
    logger.info(f"用户登录请求: {user_data.email}")

    # 查询用户
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    user = result.scalar_one_or_none()

    # 验证用户存在且密码正确
    # 注意：无论是用户不存在还是密码错误，都返回相同的错误信息
    # 这是为了防止攻击者通过错误信息判断邮箱是否存在
    if not user or not verify_password(user_data.password, user.password_hash):
        logger.warning(f"登录失败，邮箱或密码错误: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查用户是否被禁用
    if not user.is_active:
        logger.warning(f"登录失败，用户已禁用: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    # 生成 Token
    # sub（subject）是 JWT 标准字段，存储用户标识
    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    logger.info(f"用户登录成功: {user.email}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


# ==================== 刷新 Token ====================

@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh Token",
    description="Get new access_token using refresh_token"
)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
) -> Token:
    """
    刷新 Token 接口

    当 access_token 过期时，使用 refresh_token 获取新的 token
    这样用户不需要重新登录

    Args:
        token_data: 包含 refresh_token
        db: 数据库会话

    Returns:
        Token: 新的 access_token 和 refresh_token

    Raises:
        HTTPException: refresh_token 无效或过期时返回 401 错误

    请求示例：
        POST /api/auth/refresh
        {
            "refresh_token": "eyJ..."
        }

    响应示例：
        {
            "access_token": "eyJ...",  // 新的 access_token
            "refresh_token": "eyJ...", // 新的 refresh_token
            "token_type": "bearer"
        }
    """
    logger.info("Token 刷新请求")

    # 解码并验证 refresh_token
    payload = decode_token(token_data.refresh_token)
    if payload is None:
        logger.warning("Token 刷新失败：无效的 refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查是否是 refresh token
    if payload.get("type") != "refresh":
        logger.warning("Token 刷新失败：Token 类型错误")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户 ID
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Token 刷新失败：Token 中没有用户 ID")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证用户是否存在且激活
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        logger.warning(f"Token 刷新失败：用户不存在或已禁用: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成新的 Token
    new_access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    logger.info(f"Token 刷新成功: {user.email}")

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


# ==================== 获取当前用户 ====================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Get current logged-in user details, requires authentication"
)
async def get_me(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """
    获取当前用户信息接口

    返回当前登录用户的详细信息
    需要在请求头中携带有效的 access_token

    Args:
        current_user: 当前用户（由 get_current_user 依赖注入）

    Returns:
        UserResponse: 当前用户信息

    请求示例：
        GET /api/auth/me
        Headers:
            Authorization: Bearer <access_token>

    响应示例：
        {
            "id": "uuid",
            "email": "user@example.com",
            "name": "张三",
            "role": "user",
            "is_active": true,
            "created_at": "2026-01-30T12:00:00"
        }
    """
    logger.debug(f"获取当前用户信息: {current_user.email}")
    return current_user
