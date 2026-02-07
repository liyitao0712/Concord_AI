# app/api/trade_terms_ref.py
# 贸易术语 API（只读）
#
# 功能说明：
# 1. 贸易术语列表查询（分页 + 搜索 + 版本筛选）
# 2. 贸易术语详情查询
# 注：贸易术语为系统预置，不提供增删改接口
#
# 路由：
#   GET /admin/trade-terms          贸易术语列表
#   GET /admin/trade-terms/{id}     贸易术语详情

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.trade_term import TradeTerm
from app.schemas.trade_term import TradeTermResponse, TradeTermListResponse


router = APIRouter(prefix="/admin/trade-terms", tags=["贸易术语"])


@router.get("", response_model=TradeTermListResponse)
async def list_trade_terms(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索术语代码/名称"),
    version: Optional[str] = Query(None, description="筛选 Incoterms 版本"),
    is_current: Optional[bool] = Query(None, description="筛选是否当前有效"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取贸易术语列表（只读）"""
    query = select(TradeTerm).order_by(TradeTerm.sort_order, TradeTerm.code)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                TradeTerm.code.ilike(search_filter),
                TradeTerm.name_en.ilike(search_filter),
                TradeTerm.name_zh.ilike(search_filter),
                TradeTerm.description_zh.ilike(search_filter),
            )
        )

    if version:
        query = query.where(TradeTerm.version == version)

    if is_current is not None:
        query = query.where(TradeTerm.is_current == is_current)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    terms = list(result.scalars().all())

    items = [TradeTermResponse.model_validate(t) for t in terms]

    return TradeTermListResponse(items=items, total=total)


@router.get("/{term_id}", response_model=TradeTermResponse)
async def get_trade_term(
    term_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取贸易术语详情"""
    term = await session.get(TradeTerm, term_id)
    if not term:
        raise HTTPException(status_code=404, detail="贸易术语不存在")

    return TradeTermResponse.model_validate(term)
