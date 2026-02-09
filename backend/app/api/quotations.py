# app/api/quotations.py
# 报价单管理 API
#
# 路由：
#   GET    /admin/quotations              列表
#   POST   /admin/quotations              创建（含明细行）
#   GET    /admin/quotations/{id}         详情（含明细行）
#   PUT    /admin/quotations/{id}         更新
#   DELETE /admin/quotations/{id}         删除
#   PUT    /admin/quotations/{id}/status  变更状态
#   PUT    /admin/quotations/{id}/lines   整体更新明细行

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.customer import Customer
from app.models.quotation import Quotation, QuotationLine
from app.models.client_rfq import ClientRFQ
from app.schemas.quotation import (
    QuotationCreate,
    QuotationUpdate,
    QuotationResponse,
    QuotationListResponse,
    QuotationDetailResponse,
    QuotationStatusUpdate,
    QuotationLineCreate,
    QuotationLineResponse,
)
from app.services.contract_number import generate_contract_number

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/quotations", tags=["报价单管理"])


@router.get("", response_model=QuotationListResponse)
async def list_quotations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（报价单编号）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    customer_id: Optional[str] = Query(None, description="筛选客户"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("quotation", "read")),
):
    """获取报价单列表"""
    query = select(Quotation).order_by(Quotation.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, Quotation, "quotation", scope, session)

    if search:
        query = query.where(Quotation.quotation_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(Quotation.status == status)
    if customer_id is not None:
        query = query.where(Quotation.customer_id == customer_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    quotations = list(result.scalars().all())

    # 批量查询客户名称和明细行数量
    quotation_ids = [q.id for q in quotations]
    customer_ids = list({q.customer_id for q in quotations if q.customer_id})

    customer_map: dict[str, str] = {}
    if customer_ids:
        c_result = await session.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        for row in c_result:
            customer_map[row.id] = row.name

    line_counts: dict[str, int] = {}
    if quotation_ids:
        lc_result = await session.execute(
            select(
                QuotationLine.quotation_id,
                func.count(QuotationLine.id).label("cnt"),
            )
            .where(QuotationLine.quotation_id.in_(quotation_ids))
            .group_by(QuotationLine.quotation_id)
        )
        for row in lc_result:
            line_counts[row.quotation_id] = row.cnt

    items = []
    for q in quotations:
        resp = QuotationResponse.model_validate(q)
        resp.customer_name = customer_map.get(q.customer_id)
        resp.line_count = line_counts.get(q.id, 0)
        items.append(resp)

    return QuotationListResponse(items=items, total=total)


@router.post("", response_model=QuotationDetailResponse, status_code=201)
async def create_quotation(
    data: QuotationCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("quotation", "create")),
):
    """创建报价单（含明细行）"""
    # 验证客户
    customer = await session.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")

    # 生成报价单编号
    quotation_no = data.quotation_no
    if not quotation_no:
        quotation_no = await generate_contract_number(session, "quotation", org_id=scope.org_id)

    quotation = Quotation(
        id=str(uuid4()),
        quotation_no=quotation_no,
        customer_id=data.customer_id,
        contact_id=data.contact_id,
        linked_client_rfq_id=data.linked_client_rfq_id,
        trade_term=data.trade_term,
        payment_method=data.payment_method,
        payment_terms=data.payment_terms,
        currency=data.currency,
        exchange_rate=data.exchange_rate,
        subtotal=data.subtotal,
        discount_amount=data.discount_amount,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        commission_rate=data.commission_rate,
        commission_amount=data.commission_amount,
        port_of_loading=data.port_of_loading,
        port_of_discharge=data.port_of_discharge,
        destination=data.destination,
        quotation_date=data.quotation_date,
        valid_until=data.valid_until,
        status=data.status,
        notes=data.notes,
        attachments=data.attachments,
        tags=data.tags,
        created_by=scope.user.id,
        # 权限字段自动填充
        org_id=scope.org_id,
        owner_id=scope.user.id,
        owner_dept_id=scope.user.department_id,
    )

    # 创建明细行
    for idx, line_data in enumerate(data.lines, start=1):
        line = QuotationLine(
            id=str(uuid4()),
            quotation_id=quotation.id,
            line_no=idx,
            product_id=line_data.product_id,
            product_name=line_data.product_name,
            specifications=line_data.specifications,
            unit=line_data.unit,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            discount_rate=line_data.discount_rate,
            discount_amount=line_data.discount_amount,
            tax_rate=line_data.tax_rate,
            tax_amount=line_data.tax_amount,
            amount=line_data.amount,
            amount_with_tax=line_data.amount_with_tax,
            hs_code=line_data.hs_code,
            notes=line_data.notes,
        )
        quotation.lines.append(line)

    session.add(quotation)
    await session.commit()
    await session.refresh(quotation, ["lines"])

    logger.info(f"[QuotationsAPI] 创建报价单: {quotation.quotation_no} by {scope.user.email}")

    resp = QuotationDetailResponse.model_validate(quotation)
    resp.customer_name = customer.name
    resp.line_count = len(quotation.lines)
    resp.lines = [QuotationLineResponse.model_validate(l) for l in quotation.lines]

    # 填充关联的客户询价单编号
    if quotation.linked_client_rfq_id:
        rfq = await session.get(ClientRFQ, quotation.linked_client_rfq_id)
        resp.linked_client_rfq_no = rfq.rfq_no if rfq else None

    return resp


@router.get("/{quotation_id}", response_model=QuotationDetailResponse)
async def get_quotation(
    quotation_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("quotation", "read")),
):
    """获取报价单详情（含明细行）"""
    query = (
        select(Quotation)
        .options(selectinload(Quotation.lines))
        .where(Quotation.id == quotation_id)
    )
    query = await apply_data_scope(query, Quotation, "quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")

    # 查询客户名称
    customer = await session.get(Customer, quotation.customer_id)

    resp = QuotationDetailResponse.model_validate(quotation)
    resp.customer_name = customer.name if customer else None
    resp.line_count = len(quotation.lines)
    resp.lines = [QuotationLineResponse.model_validate(l) for l in quotation.lines]

    # 填充关联的客户询价单编号
    if quotation.linked_client_rfq_id:
        rfq = await session.get(ClientRFQ, quotation.linked_client_rfq_id)
        resp.linked_client_rfq_no = rfq.rfq_no if rfq else None

    return resp


@router.put("/{quotation_id}", response_model=QuotationResponse)
async def update_quotation(
    quotation_id: str,
    data: QuotationUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("quotation", "update")),
):
    """更新报价单（不含明细行，明细行通过单独接口更新）"""
    query = select(Quotation).where(Quotation.id == quotation_id)
    query = await apply_data_scope(query, Quotation, "quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(quotation, key, value)

    quotation.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(quotation)

    # 查询关联信息
    customer = await session.get(Customer, quotation.customer_id)
    line_count = await session.scalar(
        select(func.count(QuotationLine.id)).where(QuotationLine.quotation_id == quotation_id)
    ) or 0

    logger.info(f"[QuotationsAPI] 更新报价单: {quotation.quotation_no} by {scope.user.email}")

    resp = QuotationResponse.model_validate(quotation)
    resp.customer_name = customer.name if customer else None
    resp.line_count = line_count
    return resp


@router.delete("/{quotation_id}")
async def delete_quotation(
    quotation_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("quotation", "delete")),
):
    """删除报价单（级联删除明细行）"""
    query = select(Quotation).where(Quotation.id == quotation_id)
    query = await apply_data_scope(query, Quotation, "quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")

    quotation_no = quotation.quotation_no
    await session.delete(quotation)
    await session.commit()

    logger.info(f"[QuotationsAPI] 删除报价单: {quotation_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{quotation_id}/status", response_model=QuotationResponse)
async def update_quotation_status(
    quotation_id: str,
    data: QuotationStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("quotation", "update")),
):
    """变更报价单状态"""
    query = select(Quotation).where(Quotation.id == quotation_id)
    query = await apply_data_scope(query, Quotation, "quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")

    old_status = quotation.status
    quotation.status = data.status
    quotation.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(quotation)

    logger.info(
        f"[QuotationsAPI] 状态变更: {quotation.quotation_no} "
        f"{old_status} → {data.status} by {scope.user.email}"
    )

    customer = await session.get(Customer, quotation.customer_id)
    line_count = await session.scalar(
        select(func.count(QuotationLine.id)).where(QuotationLine.quotation_id == quotation_id)
    ) or 0

    resp = QuotationResponse.model_validate(quotation)
    resp.customer_name = customer.name if customer else None
    resp.line_count = line_count
    return resp


@router.put("/{quotation_id}/lines", response_model=QuotationDetailResponse)
async def update_quotation_lines(
    quotation_id: str,
    lines: list[QuotationLineCreate],
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("quotation", "update")),
):
    """
    整体更新报价单明细行

    删除旧的明细行，创建新的明细行（整体替换策略）。
    """
    query = (
        select(Quotation)
        .options(selectinload(Quotation.lines))
        .where(Quotation.id == quotation_id)
    )
    query = await apply_data_scope(query, Quotation, "quotation", scope, session)
    result = await session.execute(query)
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="报价单不存在")

    # 删除旧明细行
    quotation.lines.clear()
    await session.flush()

    # 创建新明细行
    for idx, line_data in enumerate(lines, start=1):
        line = QuotationLine(
            id=str(uuid4()),
            quotation_id=quotation.id,
            line_no=idx,
            product_id=line_data.product_id,
            product_name=line_data.product_name,
            specifications=line_data.specifications,
            unit=line_data.unit,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            discount_rate=line_data.discount_rate,
            discount_amount=line_data.discount_amount,
            tax_rate=line_data.tax_rate,
            tax_amount=line_data.tax_amount,
            amount=line_data.amount,
            amount_with_tax=line_data.amount_with_tax,
            hs_code=line_data.hs_code,
            notes=line_data.notes,
        )
        quotation.lines.append(line)

    quotation.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(quotation, ["lines"])

    logger.info(
        f"[QuotationsAPI] 更新明细行: {quotation.quotation_no} "
        f"({len(quotation.lines)} 行) by {scope.user.email}"
    )

    customer = await session.get(Customer, quotation.customer_id)
    resp = QuotationDetailResponse.model_validate(quotation)
    resp.customer_name = customer.name if customer else None
    resp.line_count = len(quotation.lines)
    resp.lines = [QuotationLineResponse.model_validate(l) for l in quotation.lines]

    # 填充关联的客户询价单编号
    if quotation.linked_client_rfq_id:
        rfq = await session.get(ClientRFQ, quotation.linked_client_rfq_id)
        resp.linked_client_rfq_no = rfq.rfq_no if rfq else None

    return resp
