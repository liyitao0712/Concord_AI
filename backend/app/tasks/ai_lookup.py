# app/tasks/ai_lookup.py
# AI 新建客户搜索 Celery 任务
#
# 功能说明：
# 1. 后台执行 AI 搜索公司信息（Anthropic Web Search）
# 2. 搜索完成后自动填充客户记录字段
#
# 队列：default（通用任务队列）

from app.celery_app import celery_app
from app.core.logging import get_logger
from app.tasks.email import AsyncTask

logger = get_logger(__name__)


class AILookupTask(AsyncTask):
    """AI 搜索任务基类，增加失败兜底：确保客户不会永远卡在 searching 状态"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务彻底失败后（含重试耗尽），同步标记客户为 failed"""
        customer_id = args[0] if args else kwargs.get("customer_id")
        if not customer_id:
            return
        try:
            from sqlalchemy import text
            from app.core.database import sync_session_maker
            with sync_session_maker() as session:
                session.execute(
                    text("UPDATE customers SET ai_status = 'failed' WHERE id = :id AND ai_status = 'searching'"),
                    {"id": customer_id},
                )
                session.commit()
                logger.warning(f"[Celery:AINewCustomer] on_failure 兜底: 已标记 customer {customer_id} 为 failed")
        except Exception as e:
            logger.error(f"[Celery:AINewCustomer] on_failure 兜底失败: {e}")


@celery_app.task(
    bind=True,
    base=AILookupTask,
    name="app.tasks.ai_lookup.ai_lookup_new_customer",
    queue="default",
    max_retries=2,
    default_retry_delay=30,
)
async def ai_lookup_new_customer(self, customer_id: str, company_name: str, org_id: str = None):
    """
    AI 新建客户：根据公司名称搜索信息并自动填充客户记录

    Args:
        customer_id: 待更新的客户 ID
        company_name: 搜索的公司名称
    """
    from sqlalchemy import select
    from app.core.database import async_session_maker
    from app.models.customer import Customer
    from app.llm import apply_llm_settings
    from app.agents.registry import agent_registry

    logger.info(
        f"[Celery:AINewCustomer] 开始 AI 搜索: customer_id={customer_id}, "
        f"company_name={company_name}"
    )

    async with async_session_maker() as session:
        try:
            # 加载 LLM 设置
            await apply_llm_settings(session)

            # 获取 Agent 并加载配置
            agent = agent_registry.get("add_new_client_helper")
            if not agent:
                raise RuntimeError("Agent add_new_client_helper 未注册")
            await agent.load_config_from_db(session)

            # 执行 AI 搜索
            result = await agent.lookup(company_name)

            # 查找客户记录
            stmt = select(Customer).where(Customer.id == customer_id)
            if org_id:
                stmt = stmt.where(Customer.org_id == org_id)
            db_customer = (await session.execute(stmt)).scalar_one_or_none()
            if not db_customer:
                logger.error(f"[Celery:AINewCustomer] 客户不存在或不属于该组织: {customer_id}")
                return {"status": "error", "message": "客户记录不存在"}

            # 判断是否搜索成功
            if result.get("error"):
                db_customer.ai_status = "failed"
                logger.warning(
                    f"[Celery:AINewCustomer] AI 搜索失败: {result.get('error')}"
                )
            else:
                # 用 AI 结果更新客户字段（仅覆盖空字段或全部覆盖）
                if result.get("name"):
                    db_customer.name = result["name"]
                if result.get("short_name"):
                    db_customer.short_name = result["short_name"]
                if result.get("country"):
                    db_customer.country = result["country"]
                if result.get("region"):
                    db_customer.region = result["region"]
                if result.get("industry"):
                    db_customer.industry = result["industry"]
                if result.get("company_size"):
                    db_customer.company_size = result["company_size"]
                if result.get("email"):
                    db_customer.email = result["email"]
                if result.get("phone"):
                    db_customer.phone = result["phone"]
                if result.get("website"):
                    db_customer.website = result["website"]
                if result.get("address"):
                    db_customer.address = result["address"]
                if result.get("notes"):
                    db_customer.notes = result["notes"]
                if result.get("tags"):
                    db_customer.tags = result["tags"]

                db_customer.ai_status = "completed"
                db_customer.ai_confidence = result.get("confidence", 0)

                logger.info(
                    f"[Celery:AINewCustomer] AI 搜索完成: customer_id={customer_id}, "
                    f"confidence={result.get('confidence', 0)}"
                )

            await session.commit()

            return {
                "status": db_customer.ai_status,
                "customer_id": customer_id,
                "confidence": db_customer.ai_confidence,
            }

        except Exception as e:
            logger.error(f"[Celery:AINewCustomer] 任务异常: {e}", exc_info=True)

            # 标记客户为搜索失败
            try:
                stmt = select(Customer).where(Customer.id == customer_id)
                db_customer = (await session.execute(stmt)).scalar_one_or_none()
                if db_customer:
                    db_customer.ai_status = "failed"
                    await session.commit()
            except Exception:
                await session.rollback()

            raise self.retry(exc=e)
