# app/services/inventory_service.py
# 库存操作服务
#
# 功能说明：
# 1. 库存占用（销售合同占用库存）
# 2. 库存释放（取消占用、出仓完成）
# 3. 入仓增加库存
# 4. 出仓减少库存
#
# 使用方法：
#   from app.services.inventory_service import InventoryService

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import Inventory
from app.core.logging import get_logger

logger = get_logger(__name__)


class InventoryService:
    """库存操作服务"""

    @staticmethod
    async def get_or_create_inventory(
        session: AsyncSession,
        warehouse_id: str,
        product_id: str,
        unit: str = "",
    ) -> Inventory:
        """
        获取或创建库存记录

        每个仓库+产品组合只有一条记录，如果不存在则创建。
        """
        result = await session.execute(
            select(Inventory).where(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_id == product_id,
            ).with_for_update()
        )
        inventory = result.scalar_one_or_none()

        if not inventory:
            inventory = Inventory(
                id=str(uuid4()),
                warehouse_id=warehouse_id,
                product_id=product_id,
                quantity=0,
                reserved_quantity=0,
                unit=unit,
            )
            session.add(inventory)
            await session.flush()

        return inventory

    @staticmethod
    async def increase_stock(
        session: AsyncSession,
        warehouse_id: str,
        product_id: str,
        quantity: float,
        unit: str = "",
    ) -> Inventory:
        """
        增加库存（入仓时调用）

        参数：
            warehouse_id: 仓库 ID
            product_id: 产品 ID
            quantity: 增加数量（必须 > 0）
            unit: 单位
        """
        if quantity <= 0:
            raise ValueError("增加库存数量必须大于 0")

        inventory = await InventoryService.get_or_create_inventory(
            session, warehouse_id, product_id, unit
        )
        inventory.quantity = Decimal(str(inventory.quantity)) + Decimal(str(quantity))
        await session.flush()

        logger.info(
            f"[InventoryService] 增加库存: warehouse={warehouse_id} "
            f"product={product_id} +{quantity}, 当前={inventory.quantity}"
        )
        return inventory

    @staticmethod
    async def decrease_stock(
        session: AsyncSession,
        warehouse_id: str,
        product_id: str,
        quantity: float,
    ) -> Inventory:
        """
        减少库存（出仓时调用）

        参数：
            warehouse_id: 仓库 ID
            product_id: 产品 ID
            quantity: 减少数量（必须 > 0）

        异常：
            ValueError: 库存不足
        """
        if quantity <= 0:
            raise ValueError("减少库存数量必须大于 0")

        result = await session.execute(
            select(Inventory).where(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_id == product_id,
            ).with_for_update()
        )
        inventory = result.scalar_one_or_none()

        if not inventory:
            raise ValueError(f"库存记录不存在: warehouse={warehouse_id} product={product_id}")

        qty = Decimal(str(inventory.quantity))
        dec_quantity = Decimal(str(quantity))
        if qty < dec_quantity:
            raise ValueError(
                f"库存不足: 当前={inventory.quantity}, 需要={quantity}"
            )

        inventory.quantity = qty - dec_quantity
        await session.flush()

        logger.info(
            f"[InventoryService] 减少库存: warehouse={warehouse_id} "
            f"product={product_id} -{quantity}, 当前={inventory.quantity}"
        )
        return inventory

    @staticmethod
    async def reserve_stock(
        session: AsyncSession,
        warehouse_id: str,
        product_id: str,
        quantity: float,
    ) -> Inventory:
        """
        占用库存（销售合同占用）

        校验：reserved_quantity 不能超过 quantity
        可用库存 = quantity - reserved_quantity >= 需要占用的数量

        参数：
            warehouse_id: 仓库 ID
            product_id: 产品 ID
            quantity: 占用数量（必须 > 0）
        """
        if quantity <= 0:
            raise ValueError("占用库存数量必须大于 0")

        result = await session.execute(
            select(Inventory).where(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_id == product_id,
            ).with_for_update()
        )
        inventory = result.scalar_one_or_none()

        if not inventory:
            raise ValueError(f"库存记录不存在: warehouse={warehouse_id} product={product_id}")

        qty = Decimal(str(inventory.quantity))
        reserved = Decimal(str(inventory.reserved_quantity))
        dec_quantity = Decimal(str(quantity))
        available = qty - reserved
        if available < dec_quantity:
            raise ValueError(
                f"可用库存不足: 实际={inventory.quantity}, "
                f"已占用={inventory.reserved_quantity}, 可用={available}, 需要={quantity}"
            )

        inventory.reserved_quantity = reserved + dec_quantity
        await session.flush()

        logger.info(
            f"[InventoryService] 占用库存: warehouse={warehouse_id} "
            f"product={product_id} +{quantity}, 已占用={inventory.reserved_quantity}"
        )
        return inventory

    @staticmethod
    async def release_stock(
        session: AsyncSession,
        warehouse_id: str,
        product_id: str,
        quantity: float,
    ) -> Inventory:
        """
        释放库存占用（取消合同/出仓完成时调用）

        参数：
            warehouse_id: 仓库 ID
            product_id: 产品 ID
            quantity: 释放数量（必须 > 0）
        """
        if quantity <= 0:
            raise ValueError("释放库存数量必须大于 0")

        result = await session.execute(
            select(Inventory).where(
                Inventory.warehouse_id == warehouse_id,
                Inventory.product_id == product_id,
            ).with_for_update()
        )
        inventory = result.scalar_one_or_none()

        if not inventory:
            raise ValueError(f"库存记录不存在: warehouse={warehouse_id} product={product_id}")

        reserved = Decimal(str(inventory.reserved_quantity))
        dec_quantity = Decimal(str(quantity))
        if reserved < dec_quantity:
            raise ValueError(
                f"释放数量超过已占用数量: 已占用={inventory.reserved_quantity}, 释放={quantity}"
            )

        inventory.reserved_quantity = reserved - dec_quantity
        await session.flush()

        logger.info(
            f"[InventoryService] 释放库存: warehouse={warehouse_id} "
            f"product={product_id} -{quantity}, 已占用={inventory.reserved_quantity}"
        )
        return inventory
