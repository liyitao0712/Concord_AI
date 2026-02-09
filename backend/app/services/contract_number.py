# app/services/contract_number.py
# 合同编号生成服务
#
# 功能说明：
# 1. 根据编号规则自动生成合同编号
# 2. 支持按日期重置序号
# 3. 支持自定义前缀、日期格式、分隔符、序号位数
#
# 使用方法：
#   from app.services.contract_number import generate_contract_number

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract_number_rule import ContractNumberRule


# 默认编号规则（当数据库中没有配置时使用）
DEFAULT_RULES = {
    "sales_contract": {"prefix": "SC", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
    "purchase_contract": {"prefix": "PO", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
    "inbound_order": {"prefix": "IN", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
    "outbound_order": {"prefix": "OUT", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
    "client_rfq": {"prefix": "CRFQ", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
    "quotation": {"prefix": "QT", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
    "supplier_rfq": {"prefix": "SRFQ", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
    "supplier_quotation": {"prefix": "SQT", "date_format": "%Y%m%d", "separator": "-", "sequence_length": 3},
}


async def generate_contract_number(
    session: AsyncSession,
    rule_type: str,
    org_id: str = None,
) -> str:
    """
    生成合同/单据编号

    根据 contract_number_rules 表中的规则生成编号。
    如果没有配置规则，使用默认规则。

    编号格式：前缀 + 分隔符 + 日期 + 分隔符 + 序号
    例如：SC-20260208-001

    参数：
        session: 数据库会话
        rule_type: 规则类型（sales_contract / purchase_contract / inbound_order / outbound_order）

    返回：
        生成的编号字符串
    """
    now = datetime.utcnow()

    # 查询编号规则（行级锁防止并发生成重复编号）
    query = select(ContractNumberRule).where(
        ContractNumberRule.rule_type == rule_type,
        ContractNumberRule.is_active == True,
    )
    if org_id:
        query = query.where(ContractNumberRule.org_id == org_id)
    else:
        query = query.where(ContractNumberRule.org_id.is_(None))
    query = query.with_for_update()

    result = await session.execute(query)
    rule = result.scalar_one_or_none()

    if rule:
        prefix = rule.prefix
        date_format = rule.date_format
        separator = rule.separator
        seq_length = rule.sequence_length

        # 生成日期字符串
        date_str = now.strftime(date_format)

        # 判断是否需要重置序号（日期变化时重置）
        if rule.last_date != date_str:
            rule.current_sequence = 1
            rule.last_date = date_str
        else:
            rule.current_sequence += 1

        sequence = rule.current_sequence
        rule.updated_at = now
        await session.flush()
    else:
        # 使用默认规则
        defaults = DEFAULT_RULES.get(rule_type, DEFAULT_RULES["sales_contract"])
        prefix = defaults["prefix"]
        date_format = defaults["date_format"]
        separator = defaults["separator"]
        seq_length = defaults["sequence_length"]

        date_str = now.strftime(date_format)

        # 没有持久化规则时，创建一条
        rule = ContractNumberRule(
            rule_type=rule_type,
            prefix=prefix,
            date_format=date_format,
            separator=separator,
            sequence_length=seq_length,
            current_sequence=1,
            last_date=date_str,
            is_active=True,
            org_id=org_id,
        )
        session.add(rule)
        await session.flush()
        sequence = 1

    # 格式化序号
    seq_str = str(sequence).zfill(seq_length)

    return f"{prefix}{separator}{date_str}{separator}{seq_str}"


async def preview_contract_number(
    prefix: str = "SC",
    date_format: str = "%Y%m%d",
    separator: str = "-",
    sequence_length: int = 3,
) -> str:
    """
    预览编号格式（不实际生成，不操作数据库）

    返回：
        预览的编号字符串，如 SC-20260208-001
    """
    now = datetime.utcnow()
    date_str = now.strftime(date_format)
    seq_str = "1".zfill(sequence_length)
    return f"{prefix}{separator}{date_str}{separator}{seq_str}"
