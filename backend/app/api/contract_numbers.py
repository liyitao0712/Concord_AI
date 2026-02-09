# app/api/contract_numbers.py
# 合同编号规则管理 API
#
# 路由：
#   GET    /admin/contract-number-rules           规则列表
#   PUT    /admin/contract-number-rules/{type}    更新规则
#   POST   /admin/contract-number-rules/preview   预览编号

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import require_permission, DataScope
from app.models.contract_number_rule import ContractNumberRule
from app.schemas.contract_number_rule import (
    ContractNumberRuleUpdate,
    ContractNumberRuleResponse,
    ContractNumberRuleListResponse,
    ContractNumberPreviewRequest,
    ContractNumberPreviewResponse,
)
from app.services.contract_number import preview_contract_number, DEFAULT_RULES

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/contract-number-rules", tags=["编号规则"])


@router.get("", response_model=ContractNumberRuleListResponse)
async def list_contract_number_rules(
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "read")),
):
    """
    获取所有编号规则

    如果某个类型还没有配置规则，返回默认值。
    """
    query = select(ContractNumberRule).order_by(ContractNumberRule.rule_type)
    if scope.org_id:
        query = query.where(ContractNumberRule.org_id == scope.org_id)
    result = await session.execute(query)
    existing_rules = {r.rule_type: r for r in result.scalars().all()}

    items = []
    for rule_type, defaults in DEFAULT_RULES.items():
        if rule_type in existing_rules:
            items.append(ContractNumberRuleResponse.model_validate(existing_rules[rule_type]))
        else:
            # 返回默认值（不持久化）
            items.append(ContractNumberRuleResponse(
                id="",
                rule_type=rule_type,
                prefix=defaults["prefix"],
                date_format=defaults["date_format"],
                separator=defaults["separator"],
                sequence_length=defaults["sequence_length"],
                current_sequence=0,
                last_date=None,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ))

    return ContractNumberRuleListResponse(items=items, total=len(items))


@router.put("/{rule_type}", response_model=ContractNumberRuleResponse)
async def update_contract_number_rule(
    rule_type: str,
    data: ContractNumberRuleUpdate,
    session: AsyncSession = Depends(get_db),
    scope: DataScope = Depends(require_permission("setting", "update")),
):
    """更新编号规则（不存在则创建）"""
    if rule_type not in DEFAULT_RULES:
        raise HTTPException(
            status_code=400,
            detail=f"规则类型必须是: {', '.join(sorted(DEFAULT_RULES.keys()))}"
        )

    query = select(ContractNumberRule).where(ContractNumberRule.rule_type == rule_type)
    if scope.org_id:
        query = query.where(ContractNumberRule.org_id == scope.org_id)
    result = await session.execute(query)
    rule = result.scalar_one_or_none()

    if rule:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)
        rule.updated_at = datetime.utcnow()
    else:
        defaults = DEFAULT_RULES[rule_type]
        rule = ContractNumberRule(
            rule_type=rule_type,
            prefix=data.prefix or defaults["prefix"],
            date_format=data.date_format or defaults["date_format"],
            separator=data.separator if data.separator is not None else defaults["separator"],
            sequence_length=data.sequence_length or defaults["sequence_length"],
            is_active=data.is_active if data.is_active is not None else True,
            org_id=scope.org_id,
        )
        session.add(rule)

    await session.commit()
    await session.refresh(rule)

    logger.info(f"[ContractNumberRulesAPI] 更新编号规则: {rule_type} by {scope.user.email}")
    return ContractNumberRuleResponse.model_validate(rule)


@router.post("/preview", response_model=ContractNumberPreviewResponse)
async def preview_number(
    data: ContractNumberPreviewRequest,
    _: DataScope = Depends(require_permission("setting", "read")),
):
    """预览编号格式"""
    preview = await preview_contract_number(
        prefix=data.prefix,
        date_format=data.date_format,
        separator=data.separator,
        sequence_length=data.sequence_length,
    )
    return ContractNumberPreviewResponse(preview=preview)
