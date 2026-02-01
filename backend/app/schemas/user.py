# app/schemas/user.py
# 用户数据验证模式
#
# 功能说明：
# 1. 定义 API 请求和响应的数据格式
# 2. 自动验证输入数据
# 3. 自动生成 API 文档
#
# Schema 和 Model 的区别：
# - Model（models/user.py）：定义数据库表结构，用于存储数据
# - Schema（这个文件）：定义 API 数据格式，用于验证输入输出
#
# 命名规范：
# - XxxCreate: 创建数据时使用（不包含 id）
# - XxxUpdate: 更新数据时使用（所有字段可选）
# - XxxResponse: 返回数据时使用（隐藏敏感字段）
# - XxxInDB: 数据库完整数据（内部使用）

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ==================== 用户注册相关 ====================

class UserCreate(BaseModel):
    """
    用户注册请求模式

    用于 POST /api/auth/register 接口
    验证用户注册时提交的数据

    属性：
        email: 邮箱地址，必须是有效的邮箱格式
        password: 密码，最少 6 位
        name: 用户名称，2-50 个字符
    """

    email: EmailStr = Field(
        ...,  # ... 表示必填
        description="Email address",
        example="user@example.com"
    )

    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Password, at least 6 characters",
        example="123456"
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="User name",
        example="John"
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """
        验证密码强度

        可以在这里添加更复杂的密码规则，比如：
        - 必须包含数字
        - 必须包含大小写字母
        - 必须包含特殊字符

        Args:
            v: 输入的密码

        Returns:
            str: 验证通过的密码

        Raises:
            ValueError: 密码不符合要求时抛出
        """
        # 目前只检查长度，可以根据需要添加更多规则
        if len(v) < 6:
            raise ValueError("密码至少需要 6 个字符")
        return v


# ==================== 用户登录相关 ====================

class UserLogin(BaseModel):
    """
    用户登录请求模式

    用于 POST /api/auth/login 接口

    属性：
        email: 邮箱地址
        password: 密码
    """

    email: EmailStr = Field(
        ...,
        description="Email address",
        example="user@example.com"
    )

    password: str = Field(
        ...,
        description="Password",
        example="123456"
    )


class Token(BaseModel):
    """
    Token 响应模式

    登录成功后返回的数据格式

    属性：
        access_token: 访问令牌，用于访问 API
        refresh_token: 刷新令牌，用于获取新的 access_token
        token_type: 令牌类型，固定为 "bearer"

    使用说明：
        客户端收到 Token 后，在后续请求的 Header 中添加：
        Authorization: Bearer <access_token>
    """

    access_token: str = Field(
        ...,
        description="Access token"
    )

    refresh_token: str = Field(
        ...,
        description="Refresh token"
    )

    token_type: str = Field(
        default="bearer",
        description="Token type"
    )


class TokenRefresh(BaseModel):
    """
    Token 刷新请求模式

    用于 POST /api/auth/refresh 接口
    当 access_token 过期时，使用 refresh_token 获取新的 token

    属性：
        refresh_token: 刷新令牌
    """

    refresh_token: str = Field(
        ...,
        description="Refresh token"
    )


# ==================== 用户信息相关 ====================

class UserResponse(BaseModel):
    """
    用户信息响应模式

    返回给客户端的用户数据，隐藏敏感字段（如密码哈希）

    属性：
        id: 用户 ID
        email: 邮箱
        name: 名称
        role: 角色
        is_active: 是否激活
        created_at: 创建时间
    """

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email")
    name: str = Field(..., description="Name")
    role: str = Field(..., description="Role")
    is_active: bool = Field(..., description="Is active")
    created_at: datetime = Field(..., description="Created at")

    class Config:
        """Pydantic 配置"""
        # 允许从 ORM 对象（如 SQLAlchemy Model）创建
        from_attributes = True


class UserUpdate(BaseModel):
    """
    用户更新请求模式

    用于 PUT /api/users/{id} 接口
    所有字段都是可选的，只更新提供的字段

    属性：
        name: 用户名称（可选）
        password: 新密码（可选）
    """

    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="User name"
    )

    password: Optional[str] = Field(
        None,
        min_length=6,
        max_length=128,
        description="New password"
    )


class UserInDB(UserResponse):
    """
    数据库中的完整用户数据

    继承 UserResponse，添加敏感字段
    仅在内部使用，不应返回给客户端

    属性：
        password_hash: 密码哈希值
        updated_at: 更新时间
    """

    password_hash: str = Field(..., description="Password hash")
    updated_at: Optional[datetime] = Field(None, description="Updated at")


# ==================== 通用响应模式 ====================

class MessageResponse(BaseModel):
    """
    简单消息响应模式

    用于返回操作结果的简单消息

    属性：
        message: 消息内容
    """

    message: str = Field(..., description="Message content")
