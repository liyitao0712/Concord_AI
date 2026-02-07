# app/models/country.py
# 国家数据库模型
#
# 功能说明：
# 1. Country - 国家/地区基础数据表（只读，系统预置）
#
# 使用方法：
#   from app.models.country import Country

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Country(Base):
    """
    国家/地区基础数据表

    系统预置数据，不允许用户增删改。
    包含 ISO 3166-1 标准信息、中英文名称、国际区号和货币信息。

    字段分组：
    - 名称信息: name_zh, name_en, full_name_zh, full_name_en
    - ISO 标准: iso_code_2, iso_code_3, numeric_code
    - 通信信息: phone_code
    - 货币信息: currency_name_zh, currency_name_en, currency_code
    """

    __tablename__ = "countries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # ==================== 名称信息 ====================
    name_zh: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="中文简称，如「中国」",
    )
    name_en: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="英文简称，如「China」",
    )
    full_name_zh: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="中文全称，如「中华人民共和国」",
    )
    full_name_en: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="英文全称，如「People's Republic of China」",
    )

    # ==================== ISO 标准 ====================
    iso_code_2: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        unique=True,
        comment="ISO 3166-1 alpha-2 代码，如「CN」",
    )
    iso_code_3: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO 3166-1 alpha-3 代码，如「CHN」",
    )
    numeric_code: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO 3166-1 数字代码，如「156」",
    )

    # ==================== 通信信息 ====================
    phone_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="国际电话区号，如「+86」",
    )

    # ==================== 货币信息 ====================
    currency_name_zh: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="货币中文名，如「人民币」",
    )
    currency_name_en: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="货币英文名，如「Chinese Yuan」",
    )
    currency_code: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="货币代码 ISO 4217，如「CNY」",
    )

    # ==================== 时间戳 ====================
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("ix_countries_iso_code_2", "iso_code_2", unique=True),
        Index("ix_countries_name_zh", "name_zh"),
        Index("ix_countries_name_en", "name_en"),
    )

    def __repr__(self) -> str:
        return f"<Country {self.iso_code_2} {self.name_zh}>"
