# app/api/warehouses.py
# 仓库管理 API
#
# 路由：
#   GET    /admin/warehouses              仓库列表
#   POST   /admin/warehouses              创建仓库
#   GET    /admin/warehouses/{id}         仓库详情
#   PUT    /admin/warehouses/{id}         更新仓库
#   DELETE /admin/warehouses/{id}         删除仓库

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import get_current_admin_user, require_permission, apply_data_scope, DataScope
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    WarehouseListResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/warehouses", tags=["仓库管理"])


@router.get("", response_model=WarehouseListResponse)
async def list_warehouses(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索（编码/名称）"),
    warehouse_type: Optional[str] = Query(None, description="筛选类型"),
    is_active: Optional[bool] = Query(None, description="筛选状态"),
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("warehouse", "read")),
):
    """获取仓库列表"""
    query = select(Warehouse).order_by(Warehouse.created_at.desc())

    # 数据权限过滤
    query = await apply_data_scope(query, Warehouse, "warehouse", scope, session)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            or_(
                Warehouse.code.ilike(search_filter),
                Warehouse.name.ilike(search_filter),
            )
        )
    if warehouse_type is not None:
        query = query.where(Warehouse.warehouse_type == warehouse_type)
    if is_active is not None:
        query = query.where(Warehouse.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    warehouses = list(result.scalars().all())

    return WarehouseListResponse(
        items=[WarehouseResponse.model_validate(w) for w in warehouses],
        total=total,
    )


@router.post("", response_model=WarehouseResponse, status_code=201)
async def create_warehouse(
    data: WarehouseCreate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("warehouse", "create")),
):
    """创建仓库"""
    # 检查编码唯一性
    existing = await session.scalar(
        select(func.count()).where(Warehouse.code == data.code)
    )
    if existing:
        raise HTTPException(status_code=400, detail="仓库编码已存在")

    warehouse = Warehouse(
        id=str(uuid4()),
        code=data.code,
        name=data.name,
        address=data.address,
        contact_person=data.contact_person,
        contact_phone=data.contact_phone,
        warehouse_type=data.warehouse_type,
        is_active=data.is_active,
        notes=data.notes,
        org_id=scope.org_id,
    )

    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)

    logger.info(f"[WarehousesAPI] 创建仓库: {warehouse.code} {warehouse.name} by {scope.user.email}")
    return WarehouseResponse.model_validate(warehouse)


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("warehouse", "read")),
):
    """获取仓库详情"""
    query = select(Warehouse).where(Warehouse.id == warehouse_id)
    query = await apply_data_scope(query, Warehouse, "warehouse", scope, session)
    result = await session.execute(query)
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="仓库不存在")
    return WarehouseResponse.model_validate(warehouse)


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: str,
    data: WarehouseUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("warehouse", "update")),
):
    """更新仓库"""
    query = select(Warehouse).where(Warehouse.id == warehouse_id)
    query = await apply_data_scope(query, Warehouse, "warehouse", scope, session)
    result = await session.execute(query)
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="仓库不存在")

    update_data = data.model_dump(exclude_unset=True)

    # 检查编码唯一性
    if "code" in update_data and update_data["code"] != warehouse.code:
        existing = await session.scalar(
            select(func.count()).where(Warehouse.code == update_data["code"])
        )
        if existing:
            raise HTTPException(status_code=400, detail="仓库编码已存在")

    for key, value in update_data.items():
        setattr(warehouse, key, value)

    warehouse.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(warehouse)

    logger.info(f"[WarehousesAPI] 更新仓库: {warehouse.code} by {scope.user.email}")
    return WarehouseResponse.model_validate(warehouse)


@router.delete("/{warehouse_id}")
async def delete_warehouse(
    warehouse_id: str,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("warehouse", "delete")),
):
    """删除仓库（级联删除库存记录）"""
    query = select(Warehouse).where(Warehouse.id == warehouse_id)
    query = await apply_data_scope(query, Warehouse, "warehouse", scope, session)
    result = await session.execute(query)
    warehouse = result.scalar_one_or_none()
    if not warehouse:
        raise HTTPException(status_code=404, detail="仓库不存在")

    warehouse_name = f"{warehouse.code} {warehouse.name}"
    await session.delete(warehouse)
    await session.commit()

    logger.info(f"[WarehousesAPI] 删除仓库: {warehouse_name} by {scope.user.email}")
    return {"message": "删除成功"}
