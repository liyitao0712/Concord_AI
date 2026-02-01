# app/tools/database.py
# 数据库查询 Tool
#
# 提供 Agent 查询业务数据的能力：
# - 查询客户信息
# - 查询产品信息
# - 查询订单信息

from typing import Optional

from app.core.logging import get_logger
from app.tools.base import BaseTool, tool
from app.tools.registry import register_tool

# 注意：当前使用模拟数据，实际数据库查询待后续实现
# from sqlalchemy import select, or_
# from app.core.database import get_db

logger = get_logger(__name__)


@register_tool
class DatabaseTool(BaseTool):
    """
    数据库查询工具

    提供 Agent 访问业务数据的能力
    """

    name = "database"
    description = "查询数据库中的业务数据（客户、产品、订单等）"

    @tool(
        name="search_customers",
        description="搜索客户信息",
        parameters={
            "keyword": {
                "type": "string",
                "description": "搜索关键词（公司名、联系人、邮箱）",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量上限",
            },
        },
    )
    async def search_customers(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[dict]:
        """搜索客户信息"""
        # TODO: 实现实际的数据库查询
        # 这里返回模拟数据，等 Customer 模型创建后再实现
        logger.info(f"[DatabaseTool] 搜索客户: {keyword}")

        # 模拟数据
        mock_customers = [
            {
                "id": "cust-001",
                "name": "示例公司A",
                "contact": "张三",
                "email": "zhangsan@example.com",
                "phone": "13800138001",
                "level": "VIP",
            },
            {
                "id": "cust-002",
                "name": "示例公司B",
                "contact": "李四",
                "email": "lisi@example.com",
                "phone": "13800138002",
                "level": "普通",
            },
        ]

        # 简单过滤
        results = [
            c for c in mock_customers
            if keyword.lower() in c["name"].lower()
            or keyword.lower() in c["contact"].lower()
            or keyword.lower() in c["email"].lower()
        ]

        return results[:limit]

    @tool(
        name="get_customer",
        description="根据ID获取客户详情",
        parameters={
            "customer_id": {
                "type": "string",
                "description": "客户ID",
            },
        },
    )
    async def get_customer(self, customer_id: str) -> Optional[dict]:
        """获取客户详情"""
        logger.info(f"[DatabaseTool] 获取客户: {customer_id}")

        # TODO: 实际数据库查询
        return {
            "id": customer_id,
            "name": "示例公司",
            "contact": "张三",
            "email": "zhangsan@example.com",
            "phone": "13800138001",
            "address": "北京市朝阳区xxx街道",
            "level": "VIP",
            "credit_limit": 100000.00,
            "payment_terms": "月结30天",
        }

    @tool(
        name="search_products",
        description="搜索产品信息",
        parameters={
            "keyword": {
                "type": "string",
                "description": "搜索关键词（产品名、型号、类别）",
            },
            "category": {
                "type": "string",
                "description": "产品类别（可选）",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量上限",
            },
        },
    )
    async def search_products(
        self,
        keyword: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """搜索产品信息"""
        logger.info(f"[DatabaseTool] 搜索产品: {keyword}")

        # TODO: 实际数据库查询
        mock_products = [
            {
                "id": "prod-001",
                "name": "产品A",
                "model": "A-100",
                "category": "电子元器件",
                "price": 10.00,
                "unit": "个",
                "stock": 1000,
                "description": "高质量电子元器件",
            },
            {
                "id": "prod-002",
                "name": "产品B",
                "model": "B-200",
                "category": "电子元器件",
                "price": 25.00,
                "unit": "个",
                "stock": 500,
                "description": "精密电子元器件",
            },
        ]

        results = [
            p for p in mock_products
            if keyword.lower() in p["name"].lower()
            or keyword.lower() in p["model"].lower()
        ]

        if category:
            results = [p for p in results if p["category"] == category]

        return results[:limit]

    @tool(
        name="get_product",
        description="根据ID获取产品详情",
        parameters={
            "product_id": {
                "type": "string",
                "description": "产品ID",
            },
        },
    )
    async def get_product(self, product_id: str) -> Optional[dict]:
        """获取产品详情"""
        logger.info(f"[DatabaseTool] 获取产品: {product_id}")

        return {
            "id": product_id,
            "name": "示例产品",
            "model": "X-100",
            "category": "电子元器件",
            "price": 15.00,
            "unit": "个",
            "stock": 800,
            "min_order": 100,
            "lead_time": "3-5个工作日",
            "description": "高品质电子元器件，适用于各类电子产品",
        }

    @tool(
        name="get_price",
        description="获取产品价格（含客户折扣）",
        parameters={
            "product_id": {
                "type": "string",
                "description": "产品ID",
            },
            "customer_id": {
                "type": "string",
                "description": "客户ID（用于计算折扣）",
            },
            "quantity": {
                "type": "integer",
                "description": "数量（用于计算阶梯价）",
            },
        },
    )
    async def get_price(
        self,
        product_id: str,
        customer_id: Optional[str] = None,
        quantity: int = 1,
    ) -> dict:
        """获取产品价格"""
        logger.info(f"[DatabaseTool] 获取价格: {product_id}, 数量: {quantity}")

        # 基础价格
        base_price = 15.00

        # 阶梯价
        if quantity >= 1000:
            unit_price = base_price * 0.85
            discount_type = "批量折扣"
        elif quantity >= 500:
            unit_price = base_price * 0.90
            discount_type = "批量折扣"
        elif quantity >= 100:
            unit_price = base_price * 0.95
            discount_type = "批量折扣"
        else:
            unit_price = base_price
            discount_type = None

        # VIP 客户额外折扣
        if customer_id:
            # TODO: 根据客户等级获取折扣
            pass

        return {
            "product_id": product_id,
            "base_price": base_price,
            "unit_price": round(unit_price, 2),
            "quantity": quantity,
            "total": round(unit_price * quantity, 2),
            "discount_type": discount_type,
            "discount_rate": round((1 - unit_price / base_price) * 100, 1) if discount_type else 0,
        }
