# app/models/trade_term.py
# 贸易术语（Incoterms）模型
#
# 功能说明：
# 1. TradeTerm - 国际贸易术语表（只读，系统预置）
#
# 使用方法：
#   from app.models.trade_term import TradeTerm

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TradeTerm(Base):
    """
    国际贸易术语表（Incoterms）

    系统预置数据，不允许用户增删改。
    包含 Incoterms 2020 及历史版本的常用术语。

    字段分组：
    - 基本信息: code, name_en, name_zh, version
    - 运输分类: transport_mode
    - 详细描述: description_zh, description_en, risk_transfer
    - 状态: is_current, sort_order
    """

    __tablename__ = "trade_terms"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 基本信息 ====================
    code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
        comment="术语代码，如「FOB」",
    )
    name_en: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="英文全称，如「Free On Board」",
    )
    name_zh: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="中文名称，如「船上交货」",
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Incoterms 版本，如「2020」「2010」「2000」",
    )

    # ==================== 运输分类 ====================
    transport_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="适用运输方式: any=任何运输方式, sea=仅海运和内河运输",
    )

    # ==================== 详细描述 ====================
    description_zh: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="中文说明（术语含义简述）",
    )
    description_en: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="英文说明",
    )
    risk_transfer: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="风险转移点描述",
    )

    # ==================== 状态 ====================
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否为当前有效版本（2020=True, 历史=False）",
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
        Index("ix_trade_terms_code", "code", unique=True),
        Index("ix_trade_terms_version", "version"),
    )

    def __repr__(self) -> str:
        return f"<TradeTerm {self.code} {self.name_zh}>"
