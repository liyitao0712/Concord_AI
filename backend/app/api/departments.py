# app/api/departments.py
# 部门管理 API
#
# 功能说明：
# 部门的增删改查，支持树形结构。
#
# API 列表：
# GET    /admin/departments             - 获取部门列表（扁平）
# GET    /admin/departments/tree        - 获取部门树
# POST   /admin/departments             - 创建部门
# PUT    /admin/departments/{id}        - 更新部门
# DELETE /admin/departments/{id}        - 删除部门
# PUT    /admin/departments/sort        - 批量更新排序

from datetime import datetime
from typing import Optional, List, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission, DataScope
from app.core.logging import get_logger
from app.models.department import Department

# 获取当前模块的 logger
logger = get_logger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/admin/departments",
    tags=["部门管理"],
)


# ==================== Pydantic Schema ====================

class DepartmentItem(BaseModel):
    """部门列表项"""
    id: str = Field(..., description="部门 ID")
    org_id: str = Field(..., description="组织 ID")
    parent_id: Optional[str] = Field(None, description="上级部门 ID")
    name: str = Field(..., description="部门名称")
    code: Optional[str] = Field(None, description="部门编码")
    sort_order: int = Field(0, description="排序")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    model_config = {"from_attributes": True}


class CreateDepartmentRequest(BaseModel):
    """创建部门请求"""
    name: str = Field(..., min_length=1, description="部门名称")
    code: Optional[str] = Field(None, description="部门编码")
    parent_id: Optional[str] = Field(None, description="上级部门 ID")
    sort_order: int = Field(0, description="排序")


class UpdateDepartmentRequest(BaseModel):
    """更新部门请求"""
    name: Optional[str] = Field(None, description="部门名称")
    code: Optional[str] = Field(None, description="部门编码")
    parent_id: Optional[str] = Field(None, description="上级部门 ID")
    sort_order: Optional[int] = Field(None, description="排序")
    is_active: Optional[bool] = Field(None, description="是否启用")


class SortItem(BaseModel):
    """排序项"""
    id: str = Field(..., description="部门 ID")
    sort_order: int = Field(..., description="排序值")
    parent_id: Optional[str] = Field(None, description="上级部门 ID")


class DepartmentListResponse(BaseModel):
    """部门列表响应"""
    total: int = Field(..., description="总数")
    items: List[DepartmentItem] = Field(..., description="部门列表")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="消息")


# ==================== 辅助函数 ====================

def _get_org_id(scope: DataScope, org_id_param: Optional[str] = None) -> str:
    """
    获取组织 ID：超管可通过参数指定，非超管使用自身 org_id。
    """
    if scope.is_super_admin and org_id_param:
        return org_id_param
    if scope.org_id:
        return scope.org_id
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="无法确定组织 ID"
    )


def _build_tree(departments: list, parent_id: Optional[str] = None) -> list:
    """递归构建部门树"""
    nodes = []
    for dept in departments:
        if dept.parent_id == parent_id:
            node = {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "parent_id": dept.parent_id,
                "sort_order": dept.sort_order,
                "is_active": dept.is_active,
                "children": _build_tree(departments, dept.id),
            }
            nodes.append(node)
    nodes.sort(key=lambda x: x["sort_order"])
    return nodes


# ==================== API 路由 ====================

@router.get(
    "",
    response_model=DepartmentListResponse,
    summary="获取部门列表（扁平）",
    description="获取当前组织的所有部门（扁平列表）"
)
async def list_departments(
    org_id: Optional[str] = Query(None, description="组织 ID（超管可指定）"),
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read"))
):
    """获取部门列表（扁平）"""
    target_org_id = _get_org_id(scope, org_id)
    logger.info(f"用户 {scope.user.email} 获取部门列表，组织: {target_org_id}")

    query = select(Department).where(
        Department.org_id == target_org_id
    ).order_by(Department.sort_order, Department.created_at)

    result = await db.execute(query)
    departments = result.scalars().all()

    return DepartmentListResponse(
        total=len(departments),
        items=[DepartmentItem.model_validate(d) for d in departments],
    )


@router.get(
    "/tree",
    summary="获取部门树",
    description="获取当前组织的部门树形结构"
)
async def get_department_tree(
    org_id: Optional[str] = Query(None, description="组织 ID（超管可指定）"),
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read"))
):
    """获取部门树"""
    target_org_id = _get_org_id(scope, org_id)
    logger.info(f"用户 {scope.user.email} 获取部门树，组织: {target_org_id}")

    query = select(Department).where(
        Department.org_id == target_org_id
    )

    result = await db.execute(query)
    departments = result.scalars().all()

    tree = _build_tree(departments, None)
    return tree


@router.post(
    "",
    response_model=DepartmentItem,
    status_code=status.HTTP_201_CREATED,
    summary="创建部门",
    description="创建新部门"
)
async def create_department(
    request: CreateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "create"))
):
    """创建部门"""
    target_org_id = _get_org_id(scope)
    logger.info(f"用户 {scope.user.email} 创建部门: {request.name}")

    # 如果指定了上级部门，检查是否存在且属于同一组织
    if request.parent_id:
        parent_result = await db.execute(
            select(Department).where(
                Department.id == request.parent_id,
                Department.org_id == target_org_id,
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上级部门不存在或不属于当前组织"
            )

    dept = Department(
        org_id=target_org_id,
        name=request.name,
        code=request.code,
        parent_id=request.parent_id,
        sort_order=request.sort_order,
        is_active=True,
    )

    db.add(dept)
    await db.commit()
    await db.refresh(dept)

    logger.info(f"部门创建成功: {dept.name}")
    return DepartmentItem.model_validate(dept)


@router.put(
    "/sort",
    response_model=MessageResponse,
    summary="批量更新排序",
    description="批量更新部门排序和父级"
)
async def sort_departments(
    items: List[SortItem],
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "update"))
):
    """批量更新排序"""
    target_org_id = _get_org_id(scope)
    logger.info(f"用户 {scope.user.email} 批量更新部门排序，数量: {len(items)}")

    for item in items:
        result = await db.execute(
            select(Department).where(
                Department.id == item.id,
                Department.org_id == target_org_id,
            )
        )
        dept = result.scalar_one_or_none()
        if dept:
            dept.sort_order = item.sort_order
            if item.parent_id is not None:
                dept.parent_id = item.parent_id

    await db.commit()
    return MessageResponse(message="排序更新成功")


@router.put(
    "/{dept_id}",
    response_model=DepartmentItem,
    summary="更新部门",
    description="更新部门信息"
)
async def update_department(
    dept_id: str,
    request: UpdateDepartmentRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "update"))
):
    """更新部门"""
    target_org_id = _get_org_id(scope)
    logger.info(f"用户 {scope.user.email} 更新部门: {dept_id}")

    result = await db.execute(
        select(Department).where(
            Department.id == dept_id,
            Department.org_id == target_org_id,
        )
    )
    dept = result.scalar_one_or_none()

    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="部门不存在"
        )

    if request.name is not None:
        dept.name = request.name
    if request.code is not None:
        dept.code = request.code
    if request.sort_order is not None:
        dept.sort_order = request.sort_order
    if request.is_active is not None:
        dept.is_active = request.is_active

    # 更新上级部门（需要防止循环引用）
    if request.parent_id is not None:
        if request.parent_id == dept_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能将部门设置为自己的上级"
            )
        if request.parent_id:
            parent_result = await db.execute(
                select(Department).where(
                    Department.id == request.parent_id,
                    Department.org_id == target_org_id,
                )
            )
            if not parent_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="上级部门不存在或不属于当前组织"
                )
        dept.parent_id = request.parent_id if request.parent_id else None

    await db.commit()
    await db.refresh(dept)

    logger.info(f"部门更新成功: {dept.name}")
    return DepartmentItem.model_validate(dept)


@router.delete(
    "/{dept_id}",
    response_model=MessageResponse,
    summary="删除部门",
    description="删除部门（如有子部门则不允许删除）"
)
async def delete_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "delete"))
):
    """删除部门"""
    target_org_id = _get_org_id(scope)
    logger.info(f"用户 {scope.user.email} 删除部门: {dept_id}")

    result = await db.execute(
        select(Department).where(
            Department.id == dept_id,
            Department.org_id == target_org_id,
        )
    )
    dept = result.scalar_one_or_none()

    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="部门不存在"
        )

    # 检查是否有子部门
    children_result = await db.execute(
        select(func.count(Department.id)).where(
            Department.parent_id == dept_id
        )
    )
    children_count = children_result.scalar()
    if children_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该部门下有子部门，无法删除"
        )

    # 检查是否有用户关联
    from app.models.user import User
    user_result = await db.execute(
        select(func.count(User.id)).where(
            User.department_id == dept_id
        )
    )
    user_count = user_result.scalar()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该部门下有用户，无法删除"
        )

    await db.delete(dept)
    await db.commit()

    logger.info(f"部门已删除: {dept.name}")
    return MessageResponse(message="部门已删除")
