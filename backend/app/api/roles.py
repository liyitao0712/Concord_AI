# app/api/roles.py
# 角色管理 API
#
# 功能说明：
# 角色的增删改查 + 权限批量设置 + 数据范围配置。
#
# API 列表：
# GET    /admin/roles                   - 获取角色列表
# POST   /admin/roles                   - 创建角色
# GET    /admin/roles/{id}              - 获取角色详情（含权限和数据范围）
# PUT    /admin/roles/{id}              - 更新角色基本信息
# DELETE /admin/roles/{id}              - 删除角色
# PUT    /admin/roles/{id}/permissions  - 批量设置权限
# PUT    /admin/roles/{id}/data-scopes  - 批量设置数据范围

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission, DataScope
from app.core.logging import get_logger
from app.models.role import Role, Permission, RolePermission, RoleDataScope
from app.models.user import User

# 获取当前模块的 logger
logger = get_logger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/admin/roles",
    tags=["角色管理"],
)


# ==================== Pydantic Schema ====================

class RoleListItem(BaseModel):
    """角色列表项"""
    id: str = Field(..., description="角色 ID")
    org_id: Optional[str] = Field(None, description="组织 ID")
    name: str = Field(..., description="角色名称")
    code: str = Field(..., description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")
    is_system: bool = Field(False, description="是否系统预置")
    is_active: bool = Field(True, description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    permission_ids: List[str] = Field(default_factory=list, description="权限 ID 列表")
    user_count: int = Field(0, description="关联用户数")

    model_config = {"from_attributes": True}


class DataScopeItem(BaseModel):
    """数据范围项"""
    id: str = Field(..., description="ID")
    resource: str = Field(..., description="资源标识")
    scope_type: str = Field(..., description="范围类型")
    custom_dept_ids: Optional[dict] = Field(None, description="自定义部门 ID 列表")

    model_config = {"from_attributes": True}


class RoleDetail(BaseModel):
    """角色详情"""
    id: str = Field(..., description="角色 ID")
    org_id: Optional[str] = Field(None, description="组织 ID")
    name: str = Field(..., description="角色名称")
    code: str = Field(..., description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")
    is_system: bool = Field(False, description="是否系统预置")
    is_active: bool = Field(True, description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    permission_ids: List[str] = Field(default_factory=list, description="权限 ID 列表")
    data_scopes: List[DataScopeItem] = Field(default_factory=list, description="数据范围列表")

    model_config = {"from_attributes": True}


class CreateRoleRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=1, description="角色名称")
    code: str = Field(..., min_length=1, description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")


class UpdateRoleRequest(BaseModel):
    """更新角色请求"""
    name: Optional[str] = Field(None, description="角色名称")
    code: Optional[str] = Field(None, description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")
    is_active: Optional[bool] = Field(None, description="是否启用")


class SetPermissionsRequest(BaseModel):
    """批量设置权限请求"""
    permission_ids: List[str] = Field(..., description="权限 ID 列表")


class DataScopeInput(BaseModel):
    """数据范围输入"""
    resource: str = Field(..., description="资源标识")
    scope_type: str = Field(..., description="范围类型：self/department/department_tree/organization/all/custom")
    custom_dept_ids: Optional[dict] = Field(None, description="自定义部门 ID 列表（scope_type=custom 时使用）")


class SetDataScopesRequest(BaseModel):
    """批量设置数据范围请求"""
    scopes: List[DataScopeInput] = Field(..., description="数据范围列表")


class RoleListResponse(BaseModel):
    """角色列表响应"""
    total: int = Field(..., description="总数")
    items: List[RoleListItem] = Field(..., description="角色列表")


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str = Field(..., description="消息")


# ==================== 辅助函数 ====================

async def _get_role_permission_ids(db: AsyncSession, role_id: str) -> List[str]:
    """获取角色的权限 ID 列表"""
    result = await db.execute(
        select(RolePermission.permission_id).where(
            RolePermission.role_id == role_id
        )
    )
    return [row[0] for row in result]


async def _get_role_data_scopes(db: AsyncSession, role_id: str) -> List[DataScopeItem]:
    """获取角色的数据范围列表"""
    result = await db.execute(
        select(RoleDataScope).where(RoleDataScope.role_id == role_id)
    )
    return [DataScopeItem.model_validate(ds) for ds in result.scalars().all()]


# ==================== API 路由 ====================

@router.get(
    "",
    response_model=RoleListResponse,
    summary="获取角色列表",
    description="获取当前组织的角色列表（含系统角色）"
)
async def list_roles(
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read"))
):
    """获取角色列表"""
    logger.info(f"用户 {scope.user.email} 获取角色列表")

    # 查询本组织角色 + 系统角色
    query = select(Role)
    if not scope.is_super_admin and scope.org_id:
        query = query.where(
            (Role.org_id == scope.org_id) | (Role.is_system == True)
        )

    query = query.order_by(Role.is_system.desc(), desc(Role.created_at))
    result = await db.execute(query)
    roles = result.scalars().all()

    # 批量获取权限 ID 和用户数
    role_ids = [r.id for r in roles]

    # 权限 ID 映射
    perm_map: dict[str, list[str]] = {rid: [] for rid in role_ids}
    if role_ids:
        rp_result = await db.execute(
            select(RolePermission.role_id, RolePermission.permission_id).where(
                RolePermission.role_id.in_(role_ids)
            )
        )
        for role_id, perm_id in rp_result:
            perm_map[role_id].append(perm_id)

    # 用户数映射
    user_count_map: dict[str, int] = {rid: 0 for rid in role_ids}
    if role_ids:
        uc_result = await db.execute(
            select(User.role_id, func.count(User.id))
            .where(User.role_id.in_(role_ids))
            .group_by(User.role_id)
        )
        for role_id, count in uc_result:
            user_count_map[role_id] = count

    # 组装响应
    items = []
    for r in roles:
        item = RoleListItem(
            id=r.id,
            org_id=r.org_id,
            name=r.name,
            code=r.code,
            description=r.description,
            is_system=r.is_system,
            is_active=r.is_active,
            created_at=r.created_at,
            updated_at=r.updated_at,
            permission_ids=perm_map.get(r.id, []),
            user_count=user_count_map.get(r.id, 0),
        )
        items.append(item)

    return RoleListResponse(
        total=len(items),
        items=items,
    )


@router.post(
    "",
    response_model=RoleDetail,
    status_code=status.HTTP_201_CREATED,
    summary="创建角色",
    description="创建新角色"
)
async def create_role(
    request: CreateRoleRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "create"))
):
    """创建角色"""
    logger.info(f"用户 {scope.user.email} 创建角色: {request.name}")

    # 确定 org_id
    org_id = scope.org_id
    if not org_id and not scope.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法确定组织 ID"
        )

    # 检查同组织下编码唯一性
    existing = await db.execute(
        select(Role).where(
            Role.code == request.code,
            Role.org_id == org_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色编码已存在"
        )

    role = Role(
        org_id=org_id,
        name=request.name,
        code=request.code,
        description=request.description,
        is_system=False,
        is_active=True,
    )

    db.add(role)
    await db.commit()
    await db.refresh(role)

    logger.info(f"角色创建成功: {role.name} ({role.code})")
    return RoleDetail(
        id=role.id,
        org_id=role.org_id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permission_ids=[],
        data_scopes=[],
    )


@router.get(
    "/{role_id}",
    response_model=RoleDetail,
    summary="获取角色详情",
    description="获取角色详情（含权限和数据范围）"
)
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read"))
):
    """获取角色详情"""
    logger.info(f"用户 {scope.user.email} 获取角色详情: {role_id}")

    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 非超管只能查看本组织或系统角色
    if not scope.is_super_admin and scope.org_id:
        if role.org_id and role.org_id != scope.org_id and not role.is_system:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="角色不存在"
            )

    permission_ids = await _get_role_permission_ids(db, role.id)
    data_scopes = await _get_role_data_scopes(db, role.id)

    return RoleDetail(
        id=role.id,
        org_id=role.org_id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permission_ids=permission_ids,
        data_scopes=data_scopes,
    )


@router.put(
    "/{role_id}",
    response_model=RoleDetail,
    summary="更新角色",
    description="更新角色基本信息"
)
async def update_role(
    role_id: str,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "update"))
):
    """更新角色"""
    logger.info(f"用户 {scope.user.email} 更新角色: {role_id}")

    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 系统角色不允许修改编码
    if role.is_system and request.code is not None and request.code != role.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统角色不允许修改编码"
        )

    if request.name is not None:
        role.name = request.name
    if request.code is not None and request.code != role.code:
        # 检查编码唯一性
        existing = await db.execute(
            select(Role).where(
                Role.code == request.code,
                Role.org_id == role.org_id,
                Role.id != role.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色编码已存在"
            )
        role.code = request.code
    if request.description is not None:
        role.description = request.description
    if request.is_active is not None:
        role.is_active = request.is_active

    await db.commit()
    await db.refresh(role)

    permission_ids = await _get_role_permission_ids(db, role.id)
    data_scopes = await _get_role_data_scopes(db, role.id)

    logger.info(f"角色更新成功: {role.name}")
    return RoleDetail(
        id=role.id,
        org_id=role.org_id,
        name=role.name,
        code=role.code,
        description=role.description,
        is_system=role.is_system,
        is_active=role.is_active,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permission_ids=permission_ids,
        data_scopes=data_scopes,
    )


@router.delete(
    "/{role_id}",
    response_model=MessageResponse,
    summary="删除角色",
    description="删除角色（系统角色不可删除，有用户关联不可删除）"
)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "delete"))
):
    """删除角色"""
    logger.info(f"用户 {scope.user.email} 删除角色: {role_id}")

    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 系统角色不可删除
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统角色不可删除"
        )

    # 检查是否有用户关联
    user_count_result = await db.execute(
        select(func.count(User.id)).where(User.role_id == role_id)
    )
    user_count = user_count_result.scalar()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该角色下有 {user_count} 个用户，无法删除"
        )

    await db.delete(role)
    await db.commit()

    logger.info(f"角色已删除: {role.name}")
    return MessageResponse(message="角色已删除")


@router.put(
    "/{role_id}/permissions",
    response_model=MessageResponse,
    summary="批量设置权限",
    description="替换角色的全部功能权限"
)
async def set_role_permissions(
    role_id: str,
    request: SetPermissionsRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "update"))
):
    """批量设置权限"""
    logger.info(f"用户 {scope.user.email} 设置角色 {role_id} 的权限")

    # 检查角色存在
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 删除旧权限
    await db.execute(
        delete(RolePermission).where(RolePermission.role_id == role_id)
    )

    # 批量插入新权限
    if request.permission_ids:
        # 验证权限 ID 都存在
        perm_result = await db.execute(
            select(Permission.id).where(
                Permission.id.in_(request.permission_ids)
            )
        )
        valid_ids = {row[0] for row in perm_result}

        for perm_id in request.permission_ids:
            if perm_id not in valid_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"权限 ID 不存在: {perm_id}"
                )
            rp = RolePermission(
                role_id=role_id,
                permission_id=perm_id,
            )
            db.add(rp)

    await db.commit()

    logger.info(f"角色 {role.name} 的权限已更新，共 {len(request.permission_ids)} 条")
    return MessageResponse(message="权限设置成功")


@router.put(
    "/{role_id}/data-scopes",
    response_model=MessageResponse,
    summary="批量设置数据范围",
    description="替换角色的全部数据范围配置"
)
async def set_role_data_scopes(
    role_id: str,
    request: SetDataScopesRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "update"))
):
    """批量设置数据范围"""
    logger.info(f"用户 {scope.user.email} 设置角色 {role_id} 的数据范围")

    # 检查角色存在
    result = await db.execute(
        select(Role).where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="角色不存在"
        )

    # 验证 scope_type 合法
    valid_scope_types = {"self", "department", "department_tree", "organization", "all", "custom"}
    for s in request.scopes:
        if s.scope_type not in valid_scope_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的数据范围类型: {s.scope_type}"
            )

    # 删除旧数据范围
    await db.execute(
        delete(RoleDataScope).where(RoleDataScope.role_id == role_id)
    )

    # 批量插入新数据范围
    for s in request.scopes:
        ds = RoleDataScope(
            role_id=role_id,
            resource=s.resource,
            scope_type=s.scope_type,
            custom_dept_ids=s.custom_dept_ids,
        )
        db.add(ds)

    await db.commit()

    logger.info(f"角色 {role.name} 的数据范围已更新，共 {len(request.scopes)} 条")
    return MessageResponse(message="数据范围设置成功")
