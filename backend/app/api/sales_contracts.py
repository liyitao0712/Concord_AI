# app/api/sales_contracts.py
# 销售合同管理 API
#
# 路由：
#   GET    /admin/sales-contracts              列表
#   POST   /admin/sales-contracts              创建（含明细行）
#   GET    /admin/sales-contracts/{id}         详情（含明细行）
#   PUT    /admin/sales-contracts/{id}         更新
#   DELETE /admin/sales-contracts/{id}         删除
#   PUT    /admin/sales-contracts/{id}/status  变更状态
#   PUT    /admin/sales-contracts/{id}/lines   整体更新明细行
#   POST   /admin/sales-contracts/{id}/link-purchase  绑定采购合同（零库存模式）

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
from app.models.purchase_contract import PurchaseContract
from app.models.sales_contract import SalesContract, SalesLine
from app.schemas.sales_contract import (
    SalesContractCreate,
    SalesContractUpdate,
    SalesContractResponse,
    SalesContractListResponse,
    SalesContractDetailResponse,
    SalesContractStatusUpdate,
    SalesLineCreate,
    SalesLineResponse,
    LinkPurchaseRequest,
)
from app.services.contract_number import generate_contract_number

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/sales-contracts", tags=["销售合同"])


@router.get("", response_model=SalesContractListResponse)
async def list_sales_contracts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（合同编号）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    customer_id: Optional[str] = Query(None, description="筛选客户"),
    is_zero_stock: Optional[bool] = Query(None, description="筛选零库存模式"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "read")),
):
    """获取销售合同列表"""
    query = select(SalesContract).order_by(SalesContract.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, SalesContract, "sales_contract", scope, session)

    if search:
        query = query.where(SalesContract.contract_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(SalesContract.status == status)
    if customer_id is not None:
        query = query.where(SalesContract.customer_id == customer_id)
    if is_zero_stock is not None:
        query = query.where(SalesContract.is_zero_stock == is_zero_stock)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    contracts = list(result.scalars().all())

    # 批量查询客户名称和明细行数量
    contract_ids = [c.id for c in contracts]
    customer_ids = list({c.customer_id for c in contracts})

    customer_map: dict[str, str] = {}
    if customer_ids:
        c_result = await session.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        for row in c_result:
            customer_map[row.id] = row.name

    line_counts: dict[str, int] = {}
    if contract_ids:
        lc_result = await session.execute(
            select(
                SalesLine.sales_contract_id,
                func.count(SalesLine.id).label("cnt"),
            )
            .where(SalesLine.sales_contract_id.in_(contract_ids))
            .group_by(SalesLine.sales_contract_id)
        )
        for row in lc_result:
            line_counts[row.sales_contract_id] = row.cnt

    items = []
    for c in contracts:
        resp = SalesContractResponse.model_validate(c)
        resp.customer_name = customer_map.get(c.customer_id)
        resp.line_count = line_counts.get(c.id, 0)
        items.append(resp)

    return SalesContractListResponse(items=items, total=total)


@router.post("", response_model=SalesContractDetailResponse, status_code=201)
async def create_sales_contract(
    data: SalesContractCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "create")),
):
    """创建销售合同（含明细行）"""
    # 验证客户
    customer = await session.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(status_code=400, detail="客户不存在")

    # 生成合同编号
    contract_no = data.contract_no
    if not contract_no:
        contract_no = await generate_contract_number(session, "sales_contract", org_id=scope.org_id)

    contract = SalesContract(
        id=str(uuid4()),
        contract_no=contract_no,
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
        commission_rate=data.commission_rate,
        commission_amount=data.commission_amount,
        port_of_loading=data.port_of_loading,
        port_of_discharge=data.port_of_discharge,
        destination=data.destination,
        shipping_marks=data.shipping_marks,
        contract_date=data.contract_date,
        delivery_date=data.delivery_date,
        shipping_date=data.shipping_date,
        expiry_date=data.expiry_date,
        status=data.status,
        is_zero_stock=data.is_zero_stock,
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
        line = SalesLine(
            id=str(uuid4()),
            sales_contract_id=contract.id,
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
            tax_rebate_rate=line_data.tax_rebate_rate,
            amount=line_data.amount,
            amount_with_tax=line_data.amount_with_tax,
            hs_code=line_data.hs_code,
            notes=line_data.notes,
        )
        contract.lines.append(line)

    session.add(contract)
    await session.commit()
    await session.refresh(contract, ["lines"])

    logger.info(f"[SalesContractsAPI] 创建销售合同: {contract.contract_no} by {scope.user.email}")

    resp = SalesContractDetailResponse.model_validate(contract)
    resp.customer_name = customer.name
    resp.line_count = len(contract.lines)
    resp.lines = [SalesLineResponse.model_validate(l) for l in contract.lines]
    return resp


@router.get("/{contract_id}", response_model=SalesContractDetailResponse)
async def get_sales_contract(
    contract_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "read")),
):
    """获取销售合同详情（含明细行）"""
    query = (
        select(SalesContract)
        .options(selectinload(SalesContract.lines))
        .where(SalesContract.id == contract_id)
    )
    query = await apply_data_scope(query, SalesContract, "sales_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="销售合同不存在")

    customer = await session.get(Customer, contract.customer_id)

    resp = SalesContractDetailResponse.model_validate(contract)
    resp.customer_name = customer.name if customer else None
    resp.line_count = len(contract.lines)
    resp.lines = [SalesLineResponse.model_validate(l) for l in contract.lines]

    # 如果有关联采购合同，查出编号
    if contract.linked_purchase_contract_id:
        pc = await session.get(PurchaseContract, contract.linked_purchase_contract_id)
        resp.linked_purchase_contract_no = pc.contract_no if pc else None

    return resp


@router.put("/{contract_id}", response_model=SalesContractResponse)
async def update_sales_contract(
    contract_id: str,
    data: SalesContractUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "update")),
):
    """更新销售合同"""
    query = select(SalesContract).where(SalesContract.id == contract_id)
    query = await apply_data_scope(query, SalesContract, "sales_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="销售合同不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contract, key, value)

    contract.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract)

    customer = await session.get(Customer, contract.customer_id)
    line_count = await session.scalar(
        select(func.count(SalesLine.id)).where(SalesLine.sales_contract_id == contract_id)
    ) or 0

    logger.info(f"[SalesContractsAPI] 更新销售合同: {contract.contract_no} by {scope.user.email}")

    resp = SalesContractResponse.model_validate(contract)
    resp.customer_name = customer.name if customer else None
    resp.line_count = line_count
    return resp


@router.delete("/{contract_id}")
async def delete_sales_contract(
    contract_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "delete")),
):
    """删除销售合同"""
    query = select(SalesContract).where(SalesContract.id == contract_id)
    query = await apply_data_scope(query, SalesContract, "sales_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="销售合同不存在")

    contract_no = contract.contract_no
    await session.delete(contract)
    await session.commit()

    logger.info(f"[SalesContractsAPI] 删除销售合同: {contract_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{contract_id}/status", response_model=SalesContractResponse)
async def update_sales_contract_status(
    contract_id: str,
    data: SalesContractStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "update")),
):
    """变更销售合同状态"""
    query = select(SalesContract).where(SalesContract.id == contract_id)
    query = await apply_data_scope(query, SalesContract, "sales_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="销售合同不存在")

    old_status = contract.status
    contract.status = data.status
    contract.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract)

    logger.info(
        f"[SalesContractsAPI] 状态变更: {contract.contract_no} "
        f"{old_status} → {data.status} by {scope.user.email}"
    )

    customer = await session.get(Customer, contract.customer_id)
    line_count = await session.scalar(
        select(func.count(SalesLine.id)).where(SalesLine.sales_contract_id == contract_id)
    ) or 0

    resp = SalesContractResponse.model_validate(contract)
    resp.customer_name = customer.name if customer else None
    resp.line_count = line_count
    return resp


@router.put("/{contract_id}/lines", response_model=SalesContractDetailResponse)
async def update_sales_contract_lines(
    contract_id: str,
    lines: list[SalesLineCreate],
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "update")),
):
    """整体更新销售合同明细行"""
    query = (
        select(SalesContract)
        .options(selectinload(SalesContract.lines))
        .where(SalesContract.id == contract_id)
    )
    query = await apply_data_scope(query, SalesContract, "sales_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="销售合同不存在")

    contract.lines.clear()
    await session.flush()

    for idx, line_data in enumerate(lines, start=1):
        line = SalesLine(
            id=str(uuid4()),
            sales_contract_id=contract.id,
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
            tax_rebate_rate=line_data.tax_rebate_rate,
            amount=line_data.amount,
            amount_with_tax=line_data.amount_with_tax,
            hs_code=line_data.hs_code,
            notes=line_data.notes,
        )
        contract.lines.append(line)

    contract.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract, ["lines"])

    logger.info(
        f"[SalesContractsAPI] 更新明细行: {contract.contract_no} "
        f"({len(contract.lines)} 行) by {scope.user.email}"
    )

    customer = await session.get(Customer, contract.customer_id)
    resp = SalesContractDetailResponse.model_validate(contract)
    resp.customer_name = customer.name if customer else None
    resp.line_count = len(contract.lines)
    resp.lines = [SalesLineResponse.model_validate(l) for l in contract.lines]
    return resp


@router.post("/{contract_id}/link-purchase", response_model=SalesContractResponse)
async def link_purchase_contract(
    contract_id: str,
    data: LinkPurchaseRequest,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("sales_contract", "update")),
):
    """绑定采购合同（零库存模式）"""
    query = select(SalesContract).where(SalesContract.id == contract_id)
    query = await apply_data_scope(query, SalesContract, "sales_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="销售合同不存在")

    if not contract.is_zero_stock:
        raise HTTPException(status_code=400, detail="仅零库存模式合同可绑定采购合同")

    # 验证采购合同
    pc = await session.get(PurchaseContract, data.purchase_contract_id)
    if not pc:
        raise HTTPException(status_code=400, detail="采购合同不存在")

    # 检查采购合同是否已被其他销售合同关联
    existing = await session.scalar(
        select(func.count()).where(
            SalesContract.linked_purchase_contract_id == data.purchase_contract_id,
            SalesContract.id != contract_id,
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="该采购合同已被其他销售合同关联")

    contract.linked_purchase_contract_id = data.purchase_contract_id
    contract.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract)

    logger.info(
        f"[SalesContractsAPI] 绑定采购合同: {contract.contract_no} → {pc.contract_no} by {scope.user.email}"
    )

    customer = await session.get(Customer, contract.customer_id)
    line_count = await session.scalar(
        select(func.count(SalesLine.id)).where(SalesLine.sales_contract_id == contract_id)
    ) or 0

    resp = SalesContractResponse.model_validate(contract)
    resp.customer_name = customer.name if customer else None
    resp.line_count = line_count
    return resp
