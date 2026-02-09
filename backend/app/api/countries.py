# app/api/countries.py
# 国家数据库 API（只读）
#
# 功能说明：
# 1. 国家列表查询（分页 + 搜索）
# 2. 国家详情查询
# 注：国家数据为系统预置，不提供增删改接口
#
# 路由：
#   GET /admin/countries         国家列表（分页 + 搜索）
#   GET /admin/countries/{id}    国家详情

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission, DataScope
from app.models.country import Country
from app.models.customer import Customer
from app.schemas.country import CountryResponse, CountryListResponse


router = APIRouter(prefix="/admin/countries", tags=["国家数据库"])


@router.get("", response_model=CountryListResponse)
async def list_countries(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=300, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索国家名称/ISO代码/区号"),
    sort_by: Optional[str] = Query(None, description="排序方式：usage=按客户使用次数降序"),
    session: AsyncSession = Depends(get_db),
    _: DataScope = Depends(require_permission("setting", "read")),
):
    """获取国家列表（只读）"""
    query = select(Country)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Country.name_zh.ilike(search_filter),
                Country.name_en.ilike(search_filter),
                Country.full_name_zh.ilike(search_filter),
                Country.full_name_en.ilike(search_filter),
                Country.iso_code_2.ilike(search_filter),
                Country.iso_code_3.ilike(search_filter),
                Country.phone_code.ilike(search_filter),
                Country.currency_code.ilike(search_filter),
                Country.currency_name_zh.ilike(search_filter),
                Country.currency_name_en.ilike(search_filter),
            )
        )

    # 排序：按客户使用次数或默认 ISO 码
    if sort_by == "usage":
        usage_sub = (
            select(
                Customer.country,
                func.count().label("cnt"),
            )
            .where(Customer.country.isnot(None), Customer.country != "")
            .group_by(Customer.country)
            .subquery()
        )
        query = query.outerjoin(usage_sub, Country.name_zh == usage_sub.c.country)
        query = query.order_by(usage_sub.c.cnt.desc().nullslast(), Country.iso_code_2)
    else:
        query = query.order_by(Country.iso_code_2)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    countries = list(result.scalars().all())

    items = [CountryResponse.model_validate(c) for c in countries]

    return CountryListResponse(items=items, total=total)


@router.get("/{country_id}", response_model=CountryResponse)
async def get_country(
    country_id: str,
    session: AsyncSession = Depends(get_db),
    _: DataScope = Depends(require_permission("setting", "read")),
):
    """获取国家详情"""
    country = await session.get(Country, country_id)
    if not country:
        raise HTTPException(status_code=404, detail="国家不存在")

    return CountryResponse.model_validate(country)
