# app/api/organizations.py
# 组织管理 API
#
# 功能说明：
# 组织的增删改查，仅超级管理员可操作。
#
# API 列表：
# GET    /admin/organizations           - 获取组织列表（分页）
# POST   /admin/organizations           - 创建组织
# GET    /admin/organizations/{id}      - 获取组织详情
# PUT    /admin/organizations/{id}      - 更新组织
# DELETE /admin/organizations/{id}      - 删除组织（软删除）

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission, DataScope
from app.core.logging import get_logger
from app.models.organization import Organization
from app.models.department import Department
from app.models.user import User

# 获取当前模块的 logger
logger = get_logger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/admin/organizations",
    tags=["组织管理"],
)


# ==================== Pydantic Schema ====================

class OrganizationListItem(BaseModel):
    """组织列表项"""
    id: str = Field(..., description="组织 ID")
    name: str = Field(..., description="组织名称")
    code: str = Field(..., description="组织编码")
    logo: Optional[str] = Field(None, description="Logo 文件 key")
    contact_info: Optional[str] = Field(None, description="联系信息")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    department_count: int = Field(0, description="部门数量")
    user_count: int = Field(0, description="用户数量")

    model_config = {"from_attributes": True}


class OrganizationDetail(BaseModel):
    """组织详情"""
    id: str = Field(..., description="组织 ID")
    name: str = Field(..., description="组织名称")
    code: str = Field(..., description="组织编码")
    logo: Optional[str] = Field(None, description="Logo 文件 key")
    contact_info: Optional[str] = Field(None, description="联系信息")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    model_config = {"from_attributes": True}


class CreateOrganizationRequest(BaseModel):
    """创建组织请求"""
    name: str = Field(..., min_length=1, description="组织名称")
    code: str = Field(..., min_length=1, description="组织编码（唯一）")
    logo: Optional[str] = Field(None, description="Logo 文件 key")
    contact_info: Optional[str] = Field(None, description="联系信息")


class UpdateOrganizationRequest(BaseModel):
    """更新组织请求"""
    name: Optional[str] = Field(None, description="组织名称")
    code: Optional[str] = Field(None, description="组织编码")
    logo: Optional[str] = Field(None, description="Logo 文件 key")
    contact_info: Optional[str] = Field(None, description="联系信息")
    is_active: Optional[bool] = Field(None, description="是否启用")


class OrganizationListResponse(BaseModel):
    """组织列表响应"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    items: List[OrganizationListItem] = Field(..., description="组织列表")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="消息")


# ==================== 辅助函数 ====================

def _check_super_admin(scope: DataScope):
    """检查是否超级管理员"""
    if not scope.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可操作组织"
        )


# ==================== API 路由 ====================

@router.get(
    "",
    response_model=OrganizationListResponse,
    summary="获取组织列表",
    description="获取组织列表（分页），支持按名称或编码搜索"
)
async def list_organizations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="按名称或编码搜索"),
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read"))
):
    """获取组织列表（分页）"""
    _check_super_admin(scope)
    logger.info(f"超级管理员 {scope.user.email} 获取组织列表")

    # 构建查询
    query = select(Organization)

    if search:
        query = query.where(
            (Organization.name.ilike(f"%{search}%")) |
            (Organization.code.ilike(f"%{search}%"))
        )

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页并排序
    query = query.order_by(desc(Organization.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    organizations = result.scalars().all()

    # 批量查询部门数和用户数
    org_ids = [org.id for org in organizations]

    dept_counts = {}
    user_counts = {}

    if org_ids:
        # 部门计数
        dept_count_q = (
            select(Department.org_id, func.count(Department.id))
            .where(Department.org_id.in_(org_ids))
            .group_by(Department.org_id)
        )
        dept_result = await db.execute(dept_count_q)
        for org_id, count in dept_result:
            dept_counts[org_id] = count

        # 用户计数
        user_count_q = (
            select(User.org_id, func.count(User.id))
            .where(User.org_id.in_(org_ids))
            .group_by(User.org_id)
        )
        user_result = await db.execute(user_count_q)
        for org_id, count in user_result:
            user_counts[org_id] = count

    # 组装响应
    items = []
    for org in organizations:
        item = OrganizationListItem(
            id=org.id,
            name=org.name,
            code=org.code,
            logo=org.logo,
            contact_info=org.contact_info,
            is_active=org.is_active,
            created_at=org.created_at,
            updated_at=org.updated_at,
            department_count=dept_counts.get(org.id, 0),
            user_count=user_counts.get(org.id, 0),
        )
        items.append(item)

    return OrganizationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.post(
    "",
    response_model=OrganizationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="创建组织",
    description="创建新组织（仅超级管理员）"
)
async def create_organization(
    request: CreateOrganizationRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "create"))
):
    """创建组织"""
    _check_super_admin(scope)
    logger.info(f"超级管理员 {scope.user.email} 创建组织: {request.name}")

    # 检查编码唯一性
    existing = await db.execute(
        select(Organization).where(Organization.code == request.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="组织编码已存在"
        )

    org = Organization(
        name=request.name,
        code=request.code,
        logo=request.logo,
        contact_info=request.contact_info,
        is_active=True,
    )

    db.add(org)
    await db.commit()
    await db.refresh(org)

    logger.info(f"组织创建成功: {org.name} ({org.code})")
    return OrganizationDetail.model_validate(org)


@router.get(
    "/{org_id}",
    response_model=OrganizationDetail,
    summary="获取组织详情",
    description="获取指定组织的详细信息"
)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read"))
):
    """获取组织详情"""
    _check_super_admin(scope)
    logger.info(f"超级管理员 {scope.user.email} 获取组织详情: {org_id}")

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )

    return OrganizationDetail.model_validate(org)


@router.put(
    "/{org_id}",
    response_model=OrganizationDetail,
    summary="更新组织",
    description="更新组织信息（仅超级管理员）"
)
async def update_organization(
    org_id: str,
    request: UpdateOrganizationRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "update"))
):
    """更新组织"""
    _check_super_admin(scope)
    logger.info(f"超级管理员 {scope.user.email} 更新组织: {org_id}")

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )

    # 更新名称
    if request.name is not None:
        org.name = request.name

    # 更新编码（需要检查唯一性）
    if request.code is not None and request.code != org.code:
        existing = await db.execute(
            select(Organization).where(Organization.code == request.code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="组织编码已存在"
            )
        org.code = request.code

    # 更新其他字段
    if request.logo is not None:
        org.logo = request.logo
    if request.contact_info is not None:
        org.contact_info = request.contact_info
    if request.is_active is not None:
        org.is_active = request.is_active

    await db.commit()
    await db.refresh(org)

    logger.info(f"组织更新成功: {org.name}")
    return OrganizationDetail.model_validate(org)


@router.delete(
    "/{org_id}",
    response_model=MessageResponse,
    summary="删除组织（软删除）",
    description="软删除组织，将 is_active 设为 False"
)
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "delete"))
):
    """删除组织（软删除）"""
    _check_super_admin(scope)
    logger.info(f"超级管理员 {scope.user.email} 删除组织: {org_id}")

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="组织不存在"
        )

    # 软删除
    org.is_active = False
    await db.commit()

    logger.info(f"组织已软删除: {org.name}")
    return MessageResponse(message="组织已删除")
