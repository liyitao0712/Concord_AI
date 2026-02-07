# app/temporal/activities/customer.py
# 客户审批相关的 Temporal Activities
#
# 包含三个 Activity：
# 1. notify_admin_customer_activity - 通知管理员
# 2. approve_customer_activity - 批准建议，创建 Customer + Contact
# 3. reject_customer_activity - 拒绝建议

from datetime import datetime
from uuid import uuid4

from temporalio import activity
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.customer import Customer, Contact
from app.models.customer_suggestion import CustomerSuggestion


@activity.defn
async def notify_admin_customer_activity(suggestion_id: str) -> bool:
    """
    通知管理员有新的客户建议待审批

    Args:
        suggestion_id: CustomerSuggestion ID

    Returns:
        bool: 通知是否成功
    """
    activity.logger.info(f"发送客户审批通知: suggestion_id={suggestion_id}")

    async with async_session_maker() as session:
        result = await session.execute(
            select(CustomerSuggestion).where(CustomerSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            activity.logger.warning(f"客户建议不存在: {suggestion_id}")
            return False

        # TODO: 实际发送通知（邮件/飞书/站内信）
        activity.logger.info(
            f"新的客户建议待审批:\n"
            f"  - 类型: {suggestion.suggestion_type}\n"
            f"  - 公司: {suggestion.suggested_company_name}\n"
            f"  - 联系人: {suggestion.suggested_contact_name}\n"
            f"  - 邮箱: {suggestion.suggested_contact_email}\n"
            f"  - 置信度: {suggestion.confidence:.2f}"
        )
        return True


@activity.defn
async def approve_customer_activity(
    suggestion_id: str,
    reviewer_id: str,
    note: str,
) -> dict:
    """
    批准客户建议，创建 Customer 和/或 Contact 记录

    根据 suggestion_type：
    - new_customer: 创建 Customer + Contact
    - new_contact: 仅创建 Contact 关联到已有 Customer

    Args:
        suggestion_id: CustomerSuggestion ID
        reviewer_id: 审批人 ID
        note: 审批备注

    Returns:
        dict: 执行结果
    """
    activity.logger.info(
        f"执行客户批准操作: suggestion_id={suggestion_id}, reviewer={reviewer_id}"
    )

    async with async_session_maker() as session:
        # 获取建议
        result = await session.execute(
            select(CustomerSuggestion).where(CustomerSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            return {"success": False, "error": f"客户建议不存在: {suggestion_id}"}

        if suggestion.status != "pending":
            return {
                "success": False,
                "error": f"客户建议状态不正确: {suggestion.status}",
            }

        customer_id = None
        contact_id = None

        if suggestion.suggestion_type == "new_customer":
            # 创建新客户
            customer = Customer(
                id=str(uuid4()),
                name=suggestion.suggested_company_name,
                short_name=suggestion.suggested_short_name,
                country=suggestion.suggested_country,
                region=suggestion.suggested_region,
                industry=suggestion.suggested_industry,
                website=suggestion.suggested_website,
                customer_level=suggestion.suggested_customer_level or "potential",
                email=suggestion.suggested_contact_email,  # 用联系人邮箱作为公司主邮箱
                is_active=True,
                source="email",
                tags=suggestion.suggested_tags or [],
            )
            session.add(customer)
            await session.flush()
            customer_id = customer.id

            # 创建主联系人
            if suggestion.suggested_contact_name:
                contact = Contact(
                    id=str(uuid4()),
                    customer_id=customer_id,
                    name=suggestion.suggested_contact_name,
                    email=suggestion.suggested_contact_email,
                    title=suggestion.suggested_contact_title,
                    phone=suggestion.suggested_contact_phone,
                    department=suggestion.suggested_contact_department,
                    is_primary=True,
                    is_active=True,
                )
                session.add(contact)
                await session.flush()
                contact_id = contact.id

        elif suggestion.suggestion_type == "new_contact":
            # 仅创建联系人关联到已有客户
            customer_id = suggestion.matched_customer_id

            if not customer_id:
                return {"success": False, "error": "缺少关联客户 ID"}

            # 验证客户存在
            existing_customer = await session.scalar(
                select(Customer).where(Customer.id == customer_id)
            )
            if not existing_customer:
                return {"success": False, "error": f"关联客户不存在: {customer_id}"}

            if suggestion.suggested_contact_name:
                contact = Contact(
                    id=str(uuid4()),
                    customer_id=customer_id,
                    name=suggestion.suggested_contact_name,
                    email=suggestion.suggested_contact_email,
                    title=suggestion.suggested_contact_title,
                    phone=suggestion.suggested_contact_phone,
                    department=suggestion.suggested_contact_department,
                    is_primary=False,  # 新联系人不自动设为主联系人
                    is_active=True,
                )
                session.add(contact)
                await session.flush()
                contact_id = contact.id

        # 更新建议状态
        suggestion.status = "approved"
        suggestion.reviewed_by = reviewer_id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.review_note = note
        suggestion.created_customer_id = customer_id
        suggestion.created_contact_id = contact_id

        await session.commit()

        activity.logger.info(
            f"客户建议已批准: suggestion={suggestion_id}, "
            f"customer={customer_id}, contact={contact_id}"
        )

        return {
            "success": True,
            "suggestion_id": suggestion_id,
            "customer_id": customer_id,
            "contact_id": contact_id,
        }


@activity.defn
async def reject_customer_activity(
    suggestion_id: str,
    reviewer_id: str,
    note: str,
) -> dict:
    """
    拒绝客户建议

    Args:
        suggestion_id: CustomerSuggestion ID
        reviewer_id: 审批人 ID
        note: 拒绝原因

    Returns:
        dict: 执行结果
    """
    activity.logger.info(
        f"执行客户拒绝操作: suggestion_id={suggestion_id}, reviewer={reviewer_id}"
    )

    async with async_session_maker() as session:
        result = await session.execute(
            select(CustomerSuggestion).where(CustomerSuggestion.id == suggestion_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            return {"success": False, "error": f"客户建议不存在: {suggestion_id}"}

        if suggestion.status != "pending":
            return {
                "success": False,
                "error": f"客户建议状态不正确: {suggestion.status}",
            }

        suggestion.status = "rejected"
        suggestion.reviewed_by = reviewer_id
        suggestion.reviewed_at = datetime.utcnow()
        suggestion.review_note = note

        await session.commit()

        activity.logger.info(f"客户建议已拒绝: suggestion={suggestion_id}")

        return {
            "success": True,
            "suggestion_id": suggestion_id,
            "rejected_reason": note,
        }
