# app/api/payment_methods_ref.py
# 付款方式 API（只读）
#
# 功能说明：
# 1. 付款方式列表查询（分页 + 搜索 + 分类筛选）
# 2. 付款方式详情查询
# 注：付款方式为系统预置，不提供增删改接口
#
# 路由：
#   GET /admin/payment-methods          付款方式列表
#   GET /admin/payment-methods/{id}     付款方式详情

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.models.payment_method import PaymentMethod
from app.schemas.payment_method import PaymentMethodResponse, PaymentMethodListResponse


router = APIRouter(prefix="/admin/payment-methods", tags=["付款方式"])


@router.get("", response_model=PaymentMethodListResponse)
async def list_payment_methods(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索代码/名称"),
    category: Optional[str] = Query(None, description="筛选分类: remittance/credit/collection/other"),
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取付款方式列表（只读）"""
    query = select(PaymentMethod).order_by(PaymentMethod.sort_order, PaymentMethod.code)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                PaymentMethod.code.ilike(search_filter),
                PaymentMethod.name_en.ilike(search_filter),
                PaymentMethod.name_zh.ilike(search_filter),
                PaymentMethod.description_zh.ilike(search_filter),
            )
        )

    if category:
        query = query.where(PaymentMethod.category == category)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    methods = list(result.scalars().all())

    items = [PaymentMethodResponse.model_validate(m) for m in methods]

    return PaymentMethodListResponse(items=items, total=total)


@router.get("/{method_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    method_id: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    """获取付款方式详情"""
    method = await session.get(PaymentMethod, method_id)
    if not method:
        raise HTTPException(status_code=404, detail="付款方式不存在")

    return PaymentMethodResponse.model_validate(method)
