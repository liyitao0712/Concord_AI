# app/api/client_rfqs.py
# 客户询价单管理 API
#
# 路由：
#   GET    /admin/client-rfqs              列表
#   POST   /admin/client-rfqs              创建（含明细行）
#   GET    /admin/client-rfqs/{id}         详情（含明细行）
#   PUT    /admin/client-rfqs/{id}         更新
#   DELETE /admin/client-rfqs/{id}         删除
#   PUT    /admin/client-rfqs/{id}/status  变更状态
#   PUT    /admin/client-rfqs/{id}/lines   整体更新明细行

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.customer import Customer
from app.models.client_rfq import ClientRFQ, ClientRFQLine
from app.schemas.client_rfq import (
    ClientRFQCreate,
    ClientRFQUpdate,
    ClientRFQResponse,
    ClientRFQListResponse,
    ClientRFQDetailResponse,
    ClientRFQStatusUpdate,
    ClientRFQLineCreate,
    ClientRFQLineResponse,
)
from app.services.contract_number import generate_contract_number

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/client-rfqs", tags=["客户询价管理"])


@router.get("", response_model=ClientRFQListResponse)
async def list_client_rfqs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（询价单编号）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    customer_id: Optional[str] = Query(None, description="筛选客户"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("client_rfq", "read")),
):
    """获取客户询价单列表"""
    query = select(ClientRFQ).order_by(ClientRFQ.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, ClientRFQ, "client_rfq", scope, session)

    if search:
        query = query.where(ClientRFQ.rfq_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(ClientRFQ.status == status)
    if customer_id is not None:
        query = query.where(ClientRFQ.customer_id == customer_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rfqs = list(result.scalars().all())

    # 批量查询客户名称和明细行数量
    rfq_ids = [r.id for r in rfqs]
    customer_ids = list({r.customer_id for r in rfqs})

    customer_map: dict[str, str] = {}
    if customer_ids:
        c_result = await session.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        for row in c_result:
            customer_map[row.id] = row.name

    line_counts: dict[str, int] = {}
    if rfq_ids:
        lc_result = await session.execute(
            select(
                ClientRFQLine.client_rfq_id,
                func.count(ClientRFQLine.id).label("cnt"),
            )
            .where(ClientRFQLine.client_rfq_id.in_(rfq_ids))
            .group_by(ClientRFQLine.client_rfq_id)
        )
        for row in lc_result:
            line_counts[row.client_rfq_id] = row.cnt

    items = []
    for r in rfqs:
        resp = ClientRFQResponse.model_validate(r)
        resp.customer_name = customer_map.get(r.customer_id)
        resp.line_count = line_counts.get(r.id, 0)
        items.append(resp)

    return ClientRFQListResponse(items=items, total=total)


@router.post("", response_model=ClientRFQDetailResponse, status_code=201)
async def create_client_rfq(
    data: ClientRFQCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("client_rfq", "create")),
):
    """创建客户询价单（含明细行）"""
    # 验证客户
    customer = await session.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")

    # 生成询价单编号
    rfq_no = data.rfq_no
    if not rfq_no:
        rfq_no = await generate_contract_number(session, "client_rfq", org_id=scope.org_id)

    rfq = ClientRFQ(
        id=str(uuid4()),
        rfq_no=rfq_no,
        customer_id=data.customer_id,
        contact_id=data.contact_id,
        trade_term=data.trade_term,
        payment_method=data.payment_method,
        payment_terms=data.payment_terms,
        currency=data.currency,
        exchange_rate=data.exchange_rate,
        subtotal=data.subtotal,
        discount_amount=data.discount_amount,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        port_of_loading=data.port_of_loading,
        port_of_discharge=data.port_of_discharge,
        destination=data.destination,
        rfq_date=data.rfq_date,
        deadline=data.deadline,
        expiry_date=data.expiry_date,
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
        line = ClientRFQLine(
            id=str(uuid4()),
            client_rfq_id=rfq.id,
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
        rfq.lines.append(line)

    session.add(rfq)
    await session.commit()
    await session.refresh(rfq, ["lines"])

    logger.info(f"[ClientRFQsAPI] 创建客户询价单: {rfq.rfq_no} by {scope.user.email}")

    resp = ClientRFQDetailResponse.model_validate(rfq)
    resp.customer_name = customer.name
    resp.line_count = len(rfq.lines)
    resp.lines = [ClientRFQLineResponse.model_validate(l) for l in rfq.lines]
    return resp


@router.get("/{rfq_id}", response_model=ClientRFQDetailResponse)
async def get_client_rfq(
    rfq_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("client_rfq", "read")),
):
    """获取客户询价单详情（含明细行）"""
    query = (
        select(ClientRFQ)
        .options(selectinload(ClientRFQ.lines))
        .where(ClientRFQ.id == rfq_id)
    )
    query = await apply_data_scope(query, ClientRFQ, "client_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="客户询价单不存在")

    # 查询客户名称
    customer = await session.get(Customer, rfq.customer_id)

    resp = ClientRFQDetailResponse.model_validate(rfq)
    resp.customer_name = customer.name if customer else None
    resp.line_count = len(rfq.lines)
    resp.lines = [ClientRFQLineResponse.model_validate(l) for l in rfq.lines]
    return resp


@router.put("/{rfq_id}", response_model=ClientRFQResponse)
async def update_client_rfq(
    rfq_id: str,
    data: ClientRFQUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("client_rfq", "update")),
):
    """更新客户询价单（不含明细行，明细行通过单独接口更新）"""
    query = select(ClientRFQ).where(ClientRFQ.id == rfq_id)
    query = await apply_data_scope(query, ClientRFQ, "client_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="客户询价单不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rfq, key, value)

    rfq.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfq)

    # 查询关联信息
    customer = await session.get(Customer, rfq.customer_id)
    line_count = await session.scalar(
        select(func.count(ClientRFQLine.id)).where(ClientRFQLine.client_rfq_id == rfq_id)
    ) or 0

    logger.info(f"[ClientRFQsAPI] 更新客户询价单: {rfq.rfq_no} by {scope.user.email}")

    resp = ClientRFQResponse.model_validate(rfq)
    resp.customer_name = customer.name if customer else None
    resp.line_count = line_count
    return resp


@router.delete("/{rfq_id}")
async def delete_client_rfq(
    rfq_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("client_rfq", "delete")),
):
    """删除客户询价单（级联删除明细行）"""
    query = select(ClientRFQ).where(ClientRFQ.id == rfq_id)
    query = await apply_data_scope(query, ClientRFQ, "client_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="客户询价单不存在")

    rfq_no = rfq.rfq_no
    await session.delete(rfq)
    await session.commit()

    logger.info(f"[ClientRFQsAPI] 删除客户询价单: {rfq_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{rfq_id}/status", response_model=ClientRFQResponse)
async def update_client_rfq_status(
    rfq_id: str,
    data: ClientRFQStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("client_rfq", "update")),
):
    """变更客户询价单状态"""
    query = select(ClientRFQ).where(ClientRFQ.id == rfq_id)
    query = await apply_data_scope(query, ClientRFQ, "client_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="客户询价单不存在")

    old_status = rfq.status
    rfq.status = data.status
    rfq.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfq)

    logger.info(
        f"[ClientRFQsAPI] 状态变更: {rfq.rfq_no} "
        f"{old_status} → {data.status} by {scope.user.email}"
    )

    customer = await session.get(Customer, rfq.customer_id)
    line_count = await session.scalar(
        select(func.count(ClientRFQLine.id)).where(ClientRFQLine.client_rfq_id == rfq_id)
    ) or 0

    resp = ClientRFQResponse.model_validate(rfq)
    resp.customer_name = customer.name if customer else None
    resp.line_count = line_count
    return resp


@router.put("/{rfq_id}/lines", response_model=ClientRFQDetailResponse)
async def update_client_rfq_lines(
    rfq_id: str,
    lines: list[ClientRFQLineCreate],
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("client_rfq", "update")),
):
    """
    整体更新客户询价单明细行

    删除旧的明细行，创建新的明细行（整体替换策略）。
    """
    query = (
        select(ClientRFQ)
        .options(selectinload(ClientRFQ.lines))
        .where(ClientRFQ.id == rfq_id)
    )
    query = await apply_data_scope(query, ClientRFQ, "client_rfq", scope, session)
    result = await session.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="客户询价单不存在")

    # 删除旧明细行
    rfq.lines.clear()
    await session.flush()

    # 创建新明细行
    for idx, line_data in enumerate(lines, start=1):
        line = ClientRFQLine(
            id=str(uuid4()),
            client_rfq_id=rfq.id,
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
        rfq.lines.append(line)

    rfq.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(rfq, ["lines"])

    logger.info(
        f"[ClientRFQsAPI] 更新明细行: {rfq.rfq_no} "
        f"({len(rfq.lines)} 行) by {scope.user.email}"
    )

    customer = await session.get(Customer, rfq.customer_id)
    resp = ClientRFQDetailResponse.model_validate(rfq)
    resp.customer_name = customer.name if customer else None
    resp.line_count = len(rfq.lines)
    resp.lines = [ClientRFQLineResponse.model_validate(l) for l in rfq.lines]
    return resp
