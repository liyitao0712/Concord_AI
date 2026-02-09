# app/api/permissions_api.py
# 权限注册表 API（只读）
#
# 功能说明：
# 返回所有权限按 resource 分组，供前端角色管理页面的权限矩阵使用。
#
# API 列表：
# GET /admin/permissions - 获取所有权限（按 resource 分组）

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_permission, DataScope
from app.core.logging import get_logger
from app.models.role import Permission

# 获取当前模块的 logger
logger = get_logger(__name__)

# 创建路由器
router = APIRouter(
    prefix="/admin/permissions",
    tags=["权限管理"],
)

# ==================== 资源中文标签 ====================

RESOURCE_LABELS = {
    "customer": "客户", "contact": "联系人", "supplier": "供应商",
    "supplier_contact": "供应商联系人", "product": "产品", "category": "品类",
    "warehouse": "仓库", "inventory": "库存",
    "purchase_contract": "采购合同", "sales_contract": "销售合同",
    "inbound_order": "入仓单", "outbound_order": "出仓单",
    "client_rfq": "客户询价", "quotation": "报价单",
    "supplier_rfq": "供应商询价", "supplier_quotation": "供应商报价",
    "project": "项目", "task": "任务",
    "email": "邮件", "email_account": "邮箱配置",
    "worker": "Worker", "work_type": "工作类型",
    "user": "用户", "setting": "系统设置",
    "llm_model": "LLM 模型", "prompt": "提示词",
    "agent": "Agent", "chat": "对话",
    "contract_number_rule": "编号规则",
}


# ==================== Pydantic Schema ====================

class PermissionItem(BaseModel):
    """单条权限"""
    id: str = Field(..., description="权限 ID")
    resource: str = Field(..., description="资源标识")
    action: str = Field(..., description="操作类型")
    description: Optional[str] = Field(None, description="权限描述")

    model_config = {"from_attributes": True}


class PermissionGroup(BaseModel):
    """按资源分组的权限"""
    resource: str = Field(..., description="资源标识")
    resource_label: str = Field(..., description="资源中文名")
    permissions: List[PermissionItem] = Field(..., description="该资源下的权限列表")


# ==================== API 路由 ====================

@router.get(
    "",
    response_model=List[PermissionGroup],
    summary="获取所有权限（按资源分组）",
    description="返回所有权限记录，按 resource 分组，供权限矩阵使用"
)
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read"))
):
    """
    获取所有权限（按 resource 分组）

    返回系统中所有预置的功能权限，按资源分组并附带中文标签。
    """
    logger.info(f"用户 {scope.user.email} 获取权限列表")

    # 查询所有权限
    result = await db.execute(
        select(Permission).order_by(Permission.resource, Permission.action)
    )
    permissions = result.scalars().all()

    # 按 resource 分组
    groups_dict: dict[str, list] = {}
    for perm in permissions:
        if perm.resource not in groups_dict:
            groups_dict[perm.resource] = []
        groups_dict[perm.resource].append(
            PermissionItem.model_validate(perm)
        )

    # 组装返回结果
    groups = []
    for resource, perms in groups_dict.items():
        groups.append(PermissionGroup(
            resource=resource,
            resource_label=RESOURCE_LABELS.get(resource, resource),
            permissions=perms,
        ))

    return groups
