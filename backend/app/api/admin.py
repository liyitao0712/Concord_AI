# app/api/admin.py
# 管理员后台 API
#
# 功能说明：
# 1. 用户管理（增删改查、禁用、重置密码）
# 2. 系统统计（用户数量、活跃用户等）
#
# 权限要求：
# 使用 require_permission 进行细粒度权限控制，
# 非超管只能访问本组织的用户数据。
#
# API 列表：
# ┌─────────────────────────────────────────────────────────────┐
# │                     管理员 API 列表                          │
# ├─────────────────────────────────────────────────────────────┤
# │ GET    /admin/stats              │ 获取系统统计信息          │
# │ GET    /admin/users              │ 获取用户列表              │
# │ GET    /admin/users/{user_id}    │ 获取单个用户详情          │
# │ POST   /admin/users              │ 创建新用户                │
# │ PUT    /admin/users/{user_id}    │ 更新用户信息              │
# │ DELETE /admin/users/{user_id}    │ 删除用户                  │
# │ POST   /admin/users/{id}/toggle  │ 启用/禁用用户             │
# │ POST   /admin/users/{id}/reset   │ 重置用户密码              │
# └─────────────────────────────────────────────────────────────┘

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    get_current_admin_user,
    hash_password,
    require_permission,
    DataScope,
    apply_data_scope,
)
from app.core.logging import get_logger
from app.models.user import User
from app.models.role import Role
from app.models.department import Department

# 获取当前模块的 logger
logger = get_logger(__name__)

# 创建路由器，所有路由都以 /admin 开头
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ==================== Pydantic Schema ====================

class UserListItem(BaseModel):
    """User list item (for list display)"""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    name: str = Field(..., description="User name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Is active")
    created_at: datetime = Field(..., description="Created time")
    org_id: Optional[str] = Field(None, description="组织 ID")
    department_id: Optional[str] = Field(None, description="部门 ID")
    role_id: Optional[str] = Field(None, description="角色 ID")
    supervisor_id: Optional[str] = Field(None, description="上级 ID")
    is_super_admin: bool = Field(False, description="超管")
    role_name: Optional[str] = Field(None, description="角色名")
    department_name: Optional[str] = Field(None, description="部门名")

    model_config = {"from_attributes": True}


class UserDetail(UserListItem):
    """User detail (includes all fields)"""
    updated_at: Optional[datetime] = Field(None, description="Updated time")


class CreateUserRequest(BaseModel):
    """Create user request"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    name: str = Field(..., min_length=1, description="User name")
    role: str = Field("user", description="User role: admin or user")
    role_id: Optional[str] = Field(None, description="角色 ID")
    department_id: Optional[str] = Field(None, description="主部门 ID")
    supervisor_id: Optional[str] = Field(None, description="直属上级 ID")


class UpdateUserRequest(BaseModel):
    """Update user request"""
    email: Optional[EmailStr] = Field(None, description="New email")
    name: Optional[str] = Field(None, description="New name")
    role: Optional[str] = Field(None, description="New role")
    role_id: Optional[str] = Field(None, description="角色 ID")
    department_id: Optional[str] = Field(None, description="主部门 ID")
    supervisor_id: Optional[str] = Field(None, description="直属上级 ID")


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    new_password: str = Field(..., min_length=6, description="New password (min 6 chars)")


class UserListResponse(BaseModel):
    """User list response with pagination"""
    total: int = Field(..., description="Total user count")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    users: List[UserListItem] = Field(..., description="User list")


class StatsResponse(BaseModel):
    """System statistics response"""
    total_users: int = Field(..., description="Total user count")
    active_users: int = Field(..., description="Active user count")
    admin_users: int = Field(..., description="Admin user count")
    today_new_users: int = Field(..., description="New users today")


class MessageResponse(BaseModel):
    """General message response"""
    message: str = Field(..., description="Response message")


# ==================== 辅助函数 ====================

def _org_filter(scope: DataScope):
    """返回组织隔离条件列表（非超管且有 org_id 时生效）"""
    if not scope.is_super_admin and scope.org_id:
        return [User.org_id == scope.org_id]
    return []


def _check_user_org(scope: DataScope, user: User):
    """
    检查目标用户是否属于当前操作者的组织。
    非超管时，如果目标用户不在同一组织则抛 404。
    """
    if not scope.is_super_admin and scope.org_id and user.org_id != scope.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )


# ==================== API 路由 ====================

@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get system statistics",
    description="Get dashboard statistics including user counts"
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "read"))
):
    """
    获取系统统计信息

    返回：
    - 总用户数
    - 活跃用户数
    - 管理员数量
    - 今日新增用户数
    """
    logger.info(f"管理员 {scope.user.email} 获取系统统计")

    # 组织隔离条件
    org_conditions = _org_filter(scope)

    # 总用户数
    total_q = select(func.count(User.id))
    for cond in org_conditions:
        total_q = total_q.where(cond)
    total_result = await db.execute(total_q)
    total_users = total_result.scalar()

    # 活跃用户数
    active_q = select(func.count(User.id)).where(User.is_active == True)
    for cond in org_conditions:
        active_q = active_q.where(cond)
    active_result = await db.execute(active_q)
    active_users = active_result.scalar()

    # 管理员数量
    admin_q = select(func.count(User.id)).where(User.role == "admin")
    for cond in org_conditions:
        admin_q = admin_q.where(cond)
    admin_result = await db.execute(admin_q)
    admin_users = admin_result.scalar()

    # 今日新增用户
    today = datetime.utcnow().date()
    today_q = select(func.count(User.id)).where(
        func.date(User.created_at) == today
    )
    for cond in org_conditions:
        today_q = today_q.where(cond)
    today_result = await db.execute(today_q)
    today_new_users = today_result.scalar()

    return StatsResponse(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        today_new_users=today_new_users
    )


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="Get user list",
    description="Get paginated user list with optional filters"
)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search by email or name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "read"))
):
    """
    获取用户列表（分页）

    支持的筛选条件：
    - search: 搜索邮箱或名称
    - role: 按角色筛选
    - is_active: 按激活状态筛选
    """
    logger.info(f"管理员 {scope.user.email} 获取用户列表，页码: {page}")

    # 构建查询
    query = select(User)

    # 非超管只能看到本组织的用户
    if not scope.is_super_admin:
        if scope.org_id:
            query = query.where(User.org_id == scope.org_id)

    # 搜索条件
    if search:
        query = query.where(
            (User.email.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )

    # 角色筛选
    if role:
        query = query.where(User.role == role)

    # 激活状态筛选
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # 计算总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 分页并排序（按创建时间倒序）
    query = query.order_by(desc(User.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    users = result.scalars().all()

    # 批量获取角色名和部门名（避免 N+1 查询）
    role_ids = {u.role_id for u in users if u.role_id}
    dept_ids = {u.department_id for u in users if u.department_id}

    role_name_map = {}
    dept_name_map = {}

    if role_ids:
        role_result = await db.execute(
            select(Role.id, Role.name).where(Role.id.in_(role_ids))
        )
        for rid, rname in role_result:
            role_name_map[rid] = rname

    if dept_ids:
        dept_result = await db.execute(
            select(Department.id, Department.name).where(Department.id.in_(dept_ids))
        )
        for did, dname in dept_result:
            dept_name_map[did] = dname

    # 构建响应，附带角色名和部门名
    user_items = []
    for u in users:
        item = UserListItem.model_validate(u)
        item.role_name = role_name_map.get(u.role_id) if u.role_id else None
        item.department_name = dept_name_map.get(u.department_id) if u.department_id else None
        user_items.append(item)

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=user_items
    )


@router.get(
    "/users/{user_id}",
    response_model=UserDetail,
    summary="Get user detail",
    description="Get detailed information of a specific user"
)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "read"))
):
    """
    获取单个用户详情
    """
    logger.info(f"管理员 {scope.user.email} 获取用户详情: {user_id}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 非超管只能查看本组织的用户
    _check_user_org(scope, user)

    return UserDetail.model_validate(user)


@router.post(
    "/users",
    response_model=UserDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create new user",
    description="Create a new user account (admin only)"
)
async def create_user(
    request: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "create"))
):
    """
    创建新用户

    管理员可以直接创建用户，包括创建其他管理员
    """
    logger.info(f"管理员 {scope.user.email} 创建新用户: {request.email}")

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )

    # 验证角色值
    if request.role not in ["admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色只能是 admin 或 user"
        )

    # 创建用户
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        role=request.role,
        is_active=True,
        org_id=scope.org_id,  # 新建用户归入当前组织
        role_id=request.role_id,
        department_id=request.department_id,
        supervisor_id=request.supervisor_id,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"用户创建成功: {user.email}, 角色: {user.role}")
    return UserDetail.model_validate(user)


@router.put(
    "/users/{user_id}",
    response_model=UserDetail,
    summary="Update user",
    description="Update user information"
)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "update"))
):
    """
    更新用户信息

    可更新的字段：邮箱、名称、角色
    """
    logger.info(f"管理员 {scope.user.email} 更新用户: {user_id}")

    # 查找用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 非超管只能操作本组织的用户
    _check_user_org(scope, user)

    # 更新邮箱（需要检查唯一性）
    if request.email and request.email != user.email:
        email_check = await db.execute(
            select(User).where(User.email == request.email)
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用"
            )
        user.email = request.email

    # 更新名称
    if request.name:
        user.name = request.name

    # 更新角色
    if request.role:
        if request.role not in ["admin", "user"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="角色只能是 admin 或 user"
            )
        user.role = request.role

    # 更新角色关联
    if request.role_id is not None:
        user.role_id = request.role_id
    if request.department_id is not None:
        user.department_id = request.department_id
    if request.supervisor_id is not None:
        user.supervisor_id = request.supervisor_id

    await db.commit()
    await db.refresh(user)

    logger.info(f"用户更新成功: {user.email}")
    return UserDetail.model_validate(user)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="Permanently delete a user account"
)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "delete"))
):
    """
    删除用户

    注意：这是永久删除操作，无法恢复！
    如果只是想禁用用户，请使用 toggle 接口
    """
    logger.info(f"管理员 {scope.user.email} 删除用户: {user_id}")

    # 不能删除自己
    if user_id == scope.user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己"
        )

    # 查找用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 非超管只能操作本组织的用户
    _check_user_org(scope, user)

    # 删除用户
    await db.delete(user)
    await db.commit()

    logger.info(f"用户已删除: {user.email}")
    return MessageResponse(message="用户已删除")


@router.post(
    "/users/{user_id}/toggle",
    response_model=UserDetail,
    summary="Toggle user status",
    description="Enable or disable a user account"
)
async def toggle_user_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "update"))
):
    """
    启用/禁用用户

    切换用户的激活状态：
    - 如果当前是激活状态，则禁用
    - 如果当前是禁用状态，则激活
    """
    logger.info(f"管理员 {scope.user.email} 切换用户状态: {user_id}")

    # 不能禁用自己
    if user_id == scope.user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己"
        )

    # 查找用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 非超管只能操作本组织的用户
    _check_user_org(scope, user)

    # 切换状态
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)

    status_text = "激活" if user.is_active else "禁用"
    logger.info(f"用户状态已更改: {user.email} -> {status_text}")
    return UserDetail.model_validate(user)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=MessageResponse,
    summary="Reset user password",
    description="Reset a user's password to a new value"
)
async def reset_user_password(
    user_id: str,
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("user", "update"))
):
    """
    重置用户密码

    管理员可以为任何用户重置密码
    """
    logger.info(f"管理员 {scope.user.email} 重置用户密码: {user_id}")

    # 查找用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 非超管只能操作本组织的用户
    _check_user_org(scope, user)

    # 更新密码
    user.password_hash = hash_password(request.new_password)
    await db.commit()

    logger.info(f"用户密码已重置: {user.email}")
    return MessageResponse(message="密码已重置")
