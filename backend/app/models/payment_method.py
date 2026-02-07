# app/models/payment_method.py
# 付款方式模型
#
# 功能说明：
# 1. PaymentMethod - 付款方式表（只读，系统预置）
#
# 使用方法：
#   from app.models.payment_method import PaymentMethod

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaymentMethod(Base):
    """
    付款方式表

    系统预置数据，不允许用户增删改。
    包含国际贸易常用付款方式（汇款、信用证、托收、其他）。

    字段分组：
    - 基本信息: code, name_en, name_zh, category
    - 详细描述: description_zh, description_en
    - 状态: is_common, sort_order
    """

    __tablename__ = "payment_methods"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 基本信息 ====================
    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        comment="付款方式代码，如「T/T」",
    )
    name_en: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="英文全称，如「Telegraphic Transfer」",
    )
    name_zh: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="中文名称，如「电汇」",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="分类: remittance=汇款类, credit=信用证类, collection=托收类, other=其他",
    )

    # ==================== 详细描述 ====================
    description_zh: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="中文说明",
    )
    description_en: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="英文说明",
    )

    # ==================== 状态 ====================
    is_common: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否常用（前端优先排序）",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="排序序号",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    __table_args__ = (
        Index("ix_payment_methods_code", "code", unique=True),
        Index("ix_payment_methods_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<PaymentMethod {self.code} {self.name_zh}>"
