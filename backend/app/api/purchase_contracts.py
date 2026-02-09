# app/api/purchase_contracts.py
# 采购合同管理 API
#
# 路由：
#   GET    /admin/purchase-contracts              列表
#   POST   /admin/purchase-contracts              创建（含明细行）
#   GET    /admin/purchase-contracts/{id}         详情（含明细行）
#   PUT    /admin/purchase-contracts/{id}         更新
#   DELETE /admin/purchase-contracts/{id}         删除
#   PUT    /admin/purchase-contracts/{id}/status  变更状态
#   PUT    /admin/purchase-contracts/{id}/lines   整体更新明细行

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
from app.models.supplier import Supplier
from app.models.purchase_contract import PurchaseContract, PurchaseLine
from app.schemas.purchase_contract import (
    PurchaseContractCreate,
    PurchaseContractUpdate,
    PurchaseContractResponse,
    PurchaseContractListResponse,
    PurchaseContractDetailResponse,
    PurchaseContractStatusUpdate,
    PurchaseLineCreate,
    PurchaseLineResponse,
)
from app.services.contract_number import generate_contract_number

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/purchase-contracts", tags=["采购合同"])


@router.get("", response_model=PurchaseContractListResponse)
async def list_purchase_contracts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（合同编号）"),
    status: Optional[str] = Query(None, description="筛选状态"),
    supplier_id: Optional[str] = Query(None, description="筛选供应商"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("purchase_contract", "read")),
):
    """获取采购合同列表"""
    query = select(PurchaseContract).order_by(PurchaseContract.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, PurchaseContract, "purchase_contract", scope, session)

    if search:
        query = query.where(PurchaseContract.contract_no.ilike(f"%{search}%"))
    if status is not None:
        query = query.where(PurchaseContract.status == status)
    if supplier_id is not None:
        query = query.where(PurchaseContract.supplier_id == supplier_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    contracts = list(result.scalars().all())

    # 批量查询供应商名称和明细行数量
    contract_ids = [c.id for c in contracts]
    supplier_ids = list({c.supplier_id for c in contracts})

    supplier_map: dict[str, str] = {}
    if supplier_ids:
        s_result = await session.execute(
            select(Supplier.id, Supplier.name).where(Supplier.id.in_(supplier_ids))
        )
        for row in s_result:
            supplier_map[row.id] = row.name

    line_counts: dict[str, int] = {}
    if contract_ids:
        lc_result = await session.execute(
            select(
                PurchaseLine.purchase_contract_id,
                func.count(PurchaseLine.id).label("cnt"),
            )
            .where(PurchaseLine.purchase_contract_id.in_(contract_ids))
            .group_by(PurchaseLine.purchase_contract_id)
        )
        for row in lc_result:
            line_counts[row.purchase_contract_id] = row.cnt

    items = []
    for c in contracts:
        resp = PurchaseContractResponse.model_validate(c)
        resp.supplier_name = supplier_map.get(c.supplier_id)
        resp.line_count = line_counts.get(c.id, 0)
        items.append(resp)

    return PurchaseContractListResponse(items=items, total=total)


@router.post("", response_model=PurchaseContractDetailResponse, status_code=201)
async def create_purchase_contract(
    data: PurchaseContractCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("purchase_contract", "create")),
):
    """创建采购合同（含明细行）"""
    # 验证供应商
    supplier = await session.get(Supplier, data.supplier_id)
    if not supplier:
        raise HTTPException(status_code=400, detail="供应商不存在")

    # 生成合同编号
    contract_no = data.contract_no
    if not contract_no:
        contract_no = await generate_contract_number(session, "purchase_contract", org_id=scope.org_id)

    contract = PurchaseContract(
        id=str(uuid4()),
        contract_no=contract_no,
        supplier_id=data.supplier_id,
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
        contract_date=data.contract_date,
        delivery_date=data.delivery_date,
        expected_arrival_date=data.expected_arrival_date,
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
        line = PurchaseLine(
            id=str(uuid4()),
            purchase_contract_id=contract.id,
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
        contract.lines.append(line)

    session.add(contract)
    await session.commit()
    await session.refresh(contract, ["lines"])

    logger.info(f"[PurchaseContractsAPI] 创建采购合同: {contract.contract_no} by {scope.user.email}")

    resp = PurchaseContractDetailResponse.model_validate(contract)
    resp.supplier_name = supplier.name
    resp.line_count = len(contract.lines)
    resp.lines = [PurchaseLineResponse.model_validate(l) for l in contract.lines]
    return resp


@router.get("/{contract_id}", response_model=PurchaseContractDetailResponse)
async def get_purchase_contract(
    contract_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("purchase_contract", "read")),
):
    """获取采购合同详情（含明细行）"""
    query = (
        select(PurchaseContract)
        .options(selectinload(PurchaseContract.lines))
        .where(PurchaseContract.id == contract_id)
    )
    query = await apply_data_scope(query, PurchaseContract, "purchase_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="采购合同不存在")

    # 查询供应商名称
    supplier = await session.get(Supplier, contract.supplier_id)

    resp = PurchaseContractDetailResponse.model_validate(contract)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = len(contract.lines)
    resp.lines = [PurchaseLineResponse.model_validate(l) for l in contract.lines]
    return resp


@router.put("/{contract_id}", response_model=PurchaseContractResponse)
async def update_purchase_contract(
    contract_id: str,
    data: PurchaseContractUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("purchase_contract", "update")),
):
    """更新采购合同（不含明细行，明细行通过单独接口更新）"""
    query = select(PurchaseContract).where(PurchaseContract.id == contract_id)
    query = await apply_data_scope(query, PurchaseContract, "purchase_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="采购合同不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contract, key, value)

    contract.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract)

    # 查询关联信息
    supplier = await session.get(Supplier, contract.supplier_id)
    line_count = await session.scalar(
        select(func.count(PurchaseLine.id)).where(PurchaseLine.purchase_contract_id == contract_id)
    ) or 0

    logger.info(f"[PurchaseContractsAPI] 更新采购合同: {contract.contract_no} by {scope.user.email}")

    resp = PurchaseContractResponse.model_validate(contract)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = line_count
    return resp


@router.delete("/{contract_id}")
async def delete_purchase_contract(
    contract_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("purchase_contract", "delete")),
):
    """删除采购合同（级联删除明细行）"""
    query = select(PurchaseContract).where(PurchaseContract.id == contract_id)
    query = await apply_data_scope(query, PurchaseContract, "purchase_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="采购合同不存在")

    contract_no = contract.contract_no
    await session.delete(contract)
    await session.commit()

    logger.info(f"[PurchaseContractsAPI] 删除采购合同: {contract_no} by {scope.user.email}")
    return {"message": "删除成功"}


@router.put("/{contract_id}/status", response_model=PurchaseContractResponse)
async def update_purchase_contract_status(
    contract_id: str,
    data: PurchaseContractStatusUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("purchase_contract", "update")),
):
    """变更采购合同状态"""
    query = select(PurchaseContract).where(PurchaseContract.id == contract_id)
    query = await apply_data_scope(query, PurchaseContract, "purchase_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="采购合同不存在")

    old_status = contract.status
    contract.status = data.status
    contract.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract)

    logger.info(
        f"[PurchaseContractsAPI] 状态变更: {contract.contract_no} "
        f"{old_status} → {data.status} by {scope.user.email}"
    )

    supplier = await session.get(Supplier, contract.supplier_id)
    line_count = await session.scalar(
        select(func.count(PurchaseLine.id)).where(PurchaseLine.purchase_contract_id == contract_id)
    ) or 0

    resp = PurchaseContractResponse.model_validate(contract)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = line_count
    return resp


@router.put("/{contract_id}/lines", response_model=PurchaseContractDetailResponse)
async def update_purchase_contract_lines(
    contract_id: str,
    lines: list[PurchaseLineCreate],
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("purchase_contract", "update")),
):
    """
    整体更新采购合同明细行

    删除旧的明细行，创建新的明细行（整体替换策略）。
    """
    query = (
        select(PurchaseContract)
        .options(selectinload(PurchaseContract.lines))
        .where(PurchaseContract.id == contract_id)
    )
    query = await apply_data_scope(query, PurchaseContract, "purchase_contract", scope, session)
    result = await session.execute(query)
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="采购合同不存在")

    # 删除旧明细行
    contract.lines.clear()
    await session.flush()

    # 创建新明细行
    for idx, line_data in enumerate(lines, start=1):
        line = PurchaseLine(
            id=str(uuid4()),
            purchase_contract_id=contract.id,
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
        contract.lines.append(line)

    contract.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract, ["lines"])

    logger.info(
        f"[PurchaseContractsAPI] 更新明细行: {contract.contract_no} "
        f"({len(contract.lines)} 行) by {scope.user.email}"
    )

    supplier = await session.get(Supplier, contract.supplier_id)
    resp = PurchaseContractDetailResponse.model_validate(contract)
    resp.supplier_name = supplier.name if supplier else None
    resp.line_count = len(contract.lines)
    resp.lines = [PurchaseLineResponse.model_validate(l) for l in contract.lines]
    return resp
