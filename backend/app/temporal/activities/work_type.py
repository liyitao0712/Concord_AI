# app/temporal/activities/work_type.py
# 工作类型相关 Activities
#
# Activities 是工作流中执行具体业务逻辑的单元
# 可以进行数据库操作、调用外部 API 等

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from temporalio import activity
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.work_type import WorkType, WorkTypeSuggestion

logger = logging.getLogger(__name__)


@activity.defn
async def notify_admin_activity(suggestion_id: str) -> bool:
    """
    发送审批通知给管理员

    TODO: 实现通知逻辑（邮件/飞书/站内信）
    目前只记录日志

    Args:
        suggestion_id: 建议 ID

    Returns:
        bool: 是否发送成功
    """
    activity.logger.info(f"发送审批通知: suggestion_id={suggestion_id}")

    async with async_session_maker() as session:
        # 获取建议详情
        result = await session.execute(
            select(WorkTypeSuggestion).where(WorkTypeSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            activity.logger.warning(f"建议不存在: {suggestion_id}")
            return False

        # TODO: 发送通知
        # - 邮件通知
        # - 飞书机器人
        # - 站内消息
        activity.logger.info(
            f"新的工作类型建议待审批:\n"
            f"  - 建议代码: {suggestion.suggested_code}\n"
            f"  - 建议名称: {suggestion.suggested_name}\n"
            f"  - 置信度: {suggestion.confidence:.2f}\n"
            f"  - 推理: {suggestion.reasoning[:100]}..."
        )

        return True


@activity.defn
async def approve_suggestion_activity(
    suggestion_id: str,
    reviewer_id: str,
    note: str
) -> dict:
    """
    批准建议 - 创建 WorkType

    Args:
        suggestion_id: 建议 ID
        reviewer_id: 审批人 ID
        note: 审批备注

    Returns:
        dict: 操作结果
    """
    activity.logger.info(f"执行批准操作: suggestion_id={suggestion_id}, reviewer={reviewer_id}")

    async with async_session_maker() as session:
        # 1. 获取建议
        result = await session.execute(
            select(WorkTypeSuggestion).where(WorkTypeSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            activity.logger.error(f"建议不存在: {suggestion_id}")
            return {"success": False, "error": "建议不存在"}

        if suggestion.status != "pending":
            activity.logger.warning(f"建议状态不是 pending: {suggestion.status}")
            return {"success": False, "error": f"建议状态不是 pending: {suggestion.status}"}

        # 2. 创建 WorkType
        # 确定父级
        parent_id: Optional[str] = None
        path = f"/{suggestion.suggested_code}"

        if suggestion.suggested_parent_id:
            # 查询父级
            parent_result = await session.execute(
                select(WorkType).where(WorkType.id == suggestion.suggested_parent_id)
            )
            parent = parent_result.scalar_one_or_none()
            if parent:
                parent_id = parent.id
                path = f"{parent.path}/{suggestion.suggested_code}"

        # 创建新的 WorkType
        work_type = WorkType(
            id=str(uuid4()),
            parent_id=parent_id,
            code=suggestion.suggested_code,
            name=suggestion.suggested_name,
            description=suggestion.suggested_description,
            level=suggestion.suggested_level,
            path=path,
            examples=suggestion.suggested_examples or [],
            keywords=suggestion.suggested_keywords or [],
            is_active=True,
            is_system=False,
            usage_count=0,
            created_by=f"ai_approved_by_{reviewer_id}",
        )
        session.add(work_type)

        # 3. 更新建议状态
        suggestion.status = "approved"
        suggestion.reviewed_by = reviewer_id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.review_note = note
        suggestion.created_work_type_id = work_type.id

        await session.commit()

        activity.logger.info(f"WorkType 创建成功: id={work_type.id}, code={work_type.code}")

        return {
            "success": True,
            "work_type_id": work_type.id,
            "work_type_code": work_type.code,
            "suggestion_id": suggestion_id,
        }


@activity.defn
async def reject_suggestion_activity(
    suggestion_id: str,
    reviewer_id: str,
    note: str
) -> dict:
    """
    拒绝建议

    Args:
        suggestion_id: 建议 ID
        reviewer_id: 审批人 ID
        note: 拒绝原因

    Returns:
        dict: 操作结果
    """
    activity.logger.info(f"执行拒绝操作: suggestion_id={suggestion_id}, reviewer={reviewer_id}")

    async with async_session_maker() as session:
        # 获取建议
        result = await session.execute(
            select(WorkTypeSuggestion).where(WorkTypeSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            activity.logger.error(f"建议不存在: {suggestion_id}")
            return {"success": False, "error": "建议不存在"}

        if suggestion.status != "pending":
            activity.logger.warning(f"建议状态不是 pending: {suggestion.status}")
            return {"success": False, "error": f"建议状态不是 pending: {suggestion.status}"}

        # 更新建议状态
        suggestion.status = "rejected"
        suggestion.reviewed_by = reviewer_id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.review_note = note

        await session.commit()

        activity.logger.info(f"建议已拒绝: suggestion_id={suggestion_id}")

        return {
            "success": True,
            "suggestion_id": suggestion_id,
            "rejected_reason": note,
        }
