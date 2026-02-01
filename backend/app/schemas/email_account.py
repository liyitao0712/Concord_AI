# app/schemas/email_account.py
# 邮箱账户 Schema 定义
#
# 用于 API 请求/响应的数据验证和序列化

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class EmailAccountBase(BaseModel):
    """邮箱账户基础字段"""
    name: str = Field(..., min_length=1, max_length=100, description="账户名称")
    purpose: str = Field(..., description="用途: sales/support/notification/general")
    description: Optional[str] = Field(None, description="描述")


class EmailAccountCreate(EmailAccountBase):
    """创建邮箱账户请求"""
    # SMTP 配置（必填）
    smtp_host: str = Field(..., description="SMTP 服务器地址")
    smtp_port: int = Field(465, ge=1, le=65535, description="SMTP 端口")
    smtp_user: str = Field(..., description="SMTP 用户名/邮箱")
    smtp_password: str = Field(..., min_length=1, description="SMTP 密码")
    smtp_use_tls: bool = Field(True, description="是否使用 TLS")

    # IMAP 配置（可选）
    imap_host: Optional[str] = Field(None, description="IMAP 服务器地址")
    imap_port: int = Field(993, ge=1, le=65535, description="IMAP 端口")
    imap_user: Optional[str] = Field(None, description="IMAP 用户名/邮箱")
    imap_password: Optional[str] = Field(None, description="IMAP 密码")
    imap_use_ssl: bool = Field(True, description="是否使用 SSL")

    # 状态
    is_default: bool = Field(False, description="是否设为默认邮箱")


class EmailAccountUpdate(BaseModel):
    """更新邮箱账户请求（所有字段可选）"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    purpose: Optional[str] = None
    description: Optional[str] = None

    # SMTP 配置
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = Field(None, ge=1, le=65535)
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None  # 留空表示不修改
    smtp_use_tls: Optional[bool] = None

    # IMAP 配置
    imap_host: Optional[str] = None
    imap_port: Optional[int] = Field(None, ge=1, le=65535)
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None  # 留空表示不修改
    imap_use_ssl: Optional[bool] = None

    # 状态
    is_active: Optional[bool] = None


class EmailAccountResponse(BaseModel):
    """邮箱账户响应"""
    id: int
    name: str
    purpose: str
    description: Optional[str]

    # SMTP 配置（不返回密码）
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_use_tls: bool
    smtp_configured: bool = Field(description="SMTP 是否已完整配置")

    # IMAP 配置（不返回密码）
    imap_host: Optional[str]
    imap_port: int
    imap_user: Optional[str]
    imap_use_ssl: bool
    imap_configured: bool = Field(description="IMAP 是否已完整配置")

    # 状态
    is_default: bool
    is_active: bool

    # 时间戳
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailAccountListResponse(BaseModel):
    """邮箱账户列表响应"""
    total: int
    items: List[EmailAccountResponse]


class EmailAccountTestRequest(BaseModel):
    """测试邮箱连接请求"""
    test_smtp: bool = Field(True, description="是否测试 SMTP")
    test_imap: bool = Field(True, description="是否测试 IMAP")


class EmailAccountTestResponse(BaseModel):
    """测试邮箱连接响应"""
    smtp_success: Optional[bool] = Field(None, description="SMTP 连接是否成功")
    smtp_message: Optional[str] = Field(None, description="SMTP 测试消息")
    imap_success: Optional[bool] = Field(None, description="IMAP 连接是否成功")
    imap_message: Optional[str] = Field(None, description="IMAP 测试消息")
