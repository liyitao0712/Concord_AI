# app/api/inventories.py
# 库存管理 API
#
# 路由：
#   GET    /admin/inventories              库存列表
#   GET    /admin/inventories/summary      库存汇总（按产品聚合）

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user, require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.inventory import Inventory
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.schemas.inventory import (
    InventoryResponse,
    InventoryListResponse,
    InventorySummaryItem,
    InventorySummaryResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/inventories", tags=["库存管理"])


@router.get("", response_model=InventoryListResponse)
async def list_inventories(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    warehouse_id: Optional[str] = Query(None, description="筛选仓库 ID"),
    product_id: Optional[str] = Query(None, description="筛选产品 ID"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inventory", "read")),
):
    """获取库存列表"""
    query = select(Inventory).order_by(Inventory.updated_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, Inventory, "inventory", scope, session)

    if warehouse_id is not None:
        query = query.where(Inventory.warehouse_id == warehouse_id)
    if product_id is not None:
        query = query.where(Inventory.product_id == product_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    inventories = list(result.scalars().all())

    # 批量查询仓库和产品名称
    warehouse_ids = list({i.warehouse_id for i in inventories})
    product_ids = list({i.product_id for i in inventories})

    warehouse_map: dict[str, Warehouse] = {}
    product_map: dict[str, Product] = {}

    if warehouse_ids:
        wh_result = await session.execute(
            select(Warehouse).where(Warehouse.id.in_(warehouse_ids))
        )
        for w in wh_result.scalars().all():
            warehouse_map[w.id] = w

    if product_ids:
        pd_result = await session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        for p in pd_result.scalars().all():
            product_map[p.id] = p

    items = []
    for inv in inventories:
        wh = warehouse_map.get(inv.warehouse_id)
        product = product_map.get(inv.product_id)
        resp = InventoryResponse(
            id=inv.id,
            warehouse_id=inv.warehouse_id,
            product_id=inv.product_id,
            quantity=float(inv.quantity),
            reserved_quantity=float(inv.reserved_quantity),
            available_quantity=float(inv.quantity) - float(inv.reserved_quantity),
            unit=inv.unit,
            notes=inv.notes,
            warehouse_name=wh.name if wh else None,
            warehouse_code=wh.code if wh else None,
            product_name=product.name if product else None,
            product_model=product.model_number if product else None,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )
        items.append(resp)

    return InventoryListResponse(items=items, total=total)


@router.get("/summary", response_model=InventorySummaryResponse)
async def inventory_summary(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("inventory", "read")),
):
    """库存汇总（按产品聚合，跨仓库）"""
    # 汇总查询
    summary_query = (
        select(
            Inventory.product_id,
            func.sum(Inventory.quantity).label("total_quantity"),
            func.sum(Inventory.reserved_quantity).label("total_reserved"),
            func.count(Inventory.id).label("warehouse_count"),
        )
        .group_by(Inventory.product_id)
        .order_by(func.sum(Inventory.quantity).desc())
    )

    # 总数
    count_query = select(func.count()).select_from(
        select(Inventory.product_id).group_by(Inventory.product_id).subquery()
    )
    total = await session.scalar(count_query) or 0

    # 分页
    summary_query = summary_query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(summary_query)
    rows = result.all()

    # 查询产品名称
    product_ids = [row.product_id for row in rows]
    product_map: dict[str, Product] = {}
    if product_ids:
        pd_result = await session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        for p in pd_result.scalars().all():
            product_map[p.id] = p

    items = []
    for row in rows:
        product = product_map.get(row.product_id)
        total_qty = float(row.total_quantity or 0)
        total_rsv = float(row.total_reserved or 0)
        items.append(InventorySummaryItem(
            product_id=row.product_id,
            product_name=product.name if product else None,
            product_model=product.model_number if product else None,
            total_quantity=total_qty,
            total_reserved=total_rsv,
            total_available=total_qty - total_rsv,
            warehouse_count=row.warehouse_count,
        ))

    return InventorySummaryResponse(items=items, total=total)
