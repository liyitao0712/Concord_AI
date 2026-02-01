# app/models/user.py
# 用户数据模型
#
# 功能说明：
# 1. 定义 users 表的结构
# 2. 存储用户基本信息和认证信息
# 3. 提供用户相关的数据库操作
#
# 表结构：
# ┌─────────────────────────────────────────────────┐
# │                    users 表                      │
# ├─────────────────────────────────────────────────┤
# │ id            │ UUID      │ 主键，用户唯一标识   │
# │ email         │ VARCHAR   │ 邮箱（唯一，用于登录）│
# │ password_hash │ VARCHAR   │ 密码哈希值           │
# │ name          │ VARCHAR   │ 用户名称             │
# │ role          │ VARCHAR   │ 角色（admin/user）   │
# │ is_active     │ BOOLEAN   │ 是否激活             │
# │ created_at    │ TIMESTAMP │ 创建时间             │
# │ updated_at    │ TIMESTAMP │ 更新时间             │
# └─────────────────────────────────────────────────┘

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """
    用户模型

    用于存储系统用户信息，包括认证信息和基本资料

    属性说明：
        id: 用户唯一标识，使用 UUID 格式
        email: 邮箱地址，用于登录，必须唯一
        password_hash: 密码的哈希值（不存储明文密码！）
        name: 用户显示名称
        role: 用户角色，控制权限
            - admin: 管理员，可以管理用户和系统设置
            - user: 普通用户，可以使用基本功能
        is_active: 账户是否激活
            - True: 正常使用
            - False: 已禁用，无法登录
        created_at: 账户创建时间（自动设置）
        updated_at: 最后更新时间（自动更新）

    使用示例：
        # 创建新用户
        user = User(
            email="user@example.com",
            password_hash=hash_password("123456"),
            name="张三"
        )
        session.add(user)
        await session.commit()

        # 查询用户
        user = await session.get(User, user_id)
    """

    # 表名（对应数据库中的表）
    __tablename__ = "users"

    # ==================== 主键 ====================
    # 使用 UUID 作为主键，比自增 ID 更安全（不暴露用户数量）
    # default 参数：创建新记录时自动生成 UUID
    id: Mapped[str] = mapped_column(
        String(36),           # UUID 长度为 36 字符
        primary_key=True,     # 设置为主键
        default=lambda: str(uuid4())  # 自动生成 UUID
    )

    # ==================== 认证信息 ====================
    # 邮箱：用户登录的唯一凭证
    # unique=True 确保不会有重复邮箱
    # index=True 创建索引，加快按邮箱查询的速度
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="用户邮箱，用于登录"
    )

    # 密码哈希：存储加密后的密码
    # 注意：永远不要存储明文密码！
    # 使用 bcrypt 等算法进行哈希
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="密码哈希值"
    )

    # ==================== 用户信息 ====================
    # 用户名称：显示用途
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="用户名称"
    )

    # 用户角色：控制权限
    # 默认为普通用户
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
        comment="用户角色：admin/user"
    )

    # ==================== 状态标志 ====================
    # 是否激活：用于禁用账户而不删除
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否激活"
    )

    # ==================== 时间戳 ====================
    # 创建时间：记录账户创建的时间
    # server_default=func.now() 让数据库自动设置当前时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    # 更新时间：记录最后修改的时间
    # onupdate=func.now() 每次更新记录时自动更新这个字段
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        onupdate=func.now(),
        nullable=True,
        comment="更新时间"
    )

    def __repr__(self) -> str:
        """
        返回用户对象的字符串表示

        用于调试时打印用户信息

        Returns:
            str: 格式化的用户信息
        """
        return f"<User(id={self.id}, email={self.email}, name={self.name}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """
        判断用户是否为管理员

        Returns:
            bool: 是管理员返回 True，否则返回 False
        """
        return self.role == "admin"
