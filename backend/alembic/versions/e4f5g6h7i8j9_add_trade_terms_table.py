"""add trade_terms table

Revision ID: e4f5g6h7i8j9
Revises: d3e4f5g6h7i8
Create Date: 2026-02-08

创建贸易术语表（只读，系统预置）
包含 Incoterms 2020 及历史版本常用术语
"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5g6h7i8j9'
down_revision: Union[str, None] = 'd3e4f5g6h7i8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _t(code, name_en, name_zh, version, transport_mode, description_zh, description_en, risk_transfer, is_current, sort_order):
    """辅助函数：构造贸易术语数据字典"""
    return {
        "id": str(uuid4()),
        "code": code,
        "name_en": name_en,
        "name_zh": name_zh,
        "version": version,
        "transport_mode": transport_mode,
        "description_zh": description_zh,
        "description_en": description_en,
        "risk_transfer": risk_transfer,
        "is_current": is_current,
        "sort_order": sort_order,
    }


def upgrade() -> None:
    # 创建 trade_terms 表
    trade_terms_table = op.create_table(
        'trade_terms',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(10), nullable=False, comment='术语代码'),
        sa.Column('name_en', sa.String(200), nullable=False, comment='英文全称'),
        sa.Column('name_zh', sa.String(200), nullable=False, comment='中文名称'),
        sa.Column('version', sa.String(20), nullable=False, comment='Incoterms 版本'),
        sa.Column('transport_mode', sa.String(50), nullable=False, comment='适用运输方式'),
        sa.Column('description_zh', sa.Text(), nullable=True, comment='中文说明'),
        sa.Column('description_en', sa.Text(), nullable=True, comment='英文说明'),
        sa.Column('risk_transfer', sa.String(500), nullable=True, comment='风险转移点描述'),
        sa.Column('is_current', sa.Boolean(), nullable=False, comment='是否当前有效版本'),
        sa.Column('sort_order', sa.Integer(), nullable=False, comment='排序序号'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )

    # 创建索引
    op.create_index('ix_trade_terms_code', 'trade_terms', ['code'], unique=True)
    op.create_index('ix_trade_terms_version', 'trade_terms', ['version'])

    # ==================== Incoterms 2020（当前有效） ====================
    # 任何运输方式（7 个）+ 仅海运/内河运输（4 个）

    op.bulk_insert(trade_terms_table, [
        # ========== Incoterms 2020 - 任何运输方式 ==========
        _t(
            "EXW", "Ex Works", "工厂交货", "2020", "any",
            "卖方在其所在地（工厂、仓库等）将货物交给买方处置。卖方不负责将货物装上买方安排的车辆，也不负责办理出口清关手续。买方承担从卖方所在地提取货物至最终目的地的一切费用和风险。",
            "The seller places the goods at the disposal of the buyer at the seller's premises or at another named place. The seller does not need to load the goods on any collecting vehicle, nor does it need to clear the goods for export.",
            "货物在卖方所在地（工厂/仓库）交给买方处置时，风险转移给买方",
            True, 1
        ),
        _t(
            "FCA", "Free Carrier", "货交承运人", "2020", "any",
            "卖方在指定地点将货物交给买方指定的承运人或其他人。如果指定地点是卖方所在地，则卖方负责将货物装上运输工具；如果在其他地点，卖方只需将货物运到该地点并准备好卸货即可。卖方负责出口清关。",
            "The seller delivers the goods to the carrier or another person nominated by the buyer at the seller's premises or another named place. The seller is responsible for export clearance.",
            "货物交付给承运人时（在指定地点），风险转移给买方",
            True, 2
        ),
        _t(
            "CPT", "Carriage Paid To", "运费付至", "2020", "any",
            "卖方负责将货物交给其安排的承运人，并支付运费至指定目的地。但货物在交给第一承运人后，货物灭失或损坏的风险即由买方承担。卖方负责出口清关。",
            "The seller delivers the goods to the carrier nominated by the seller at an agreed place. The seller must contract for and pay the costs of carriage necessary to bring the goods to the named place of destination. Risk transfers when goods are handed to the first carrier.",
            "货物交给第一承运人时，风险转移给买方（注意：风险转移点与费用分担点不同）",
            True, 3
        ),
        _t(
            "CIP", "Carriage and Insurance Paid To", "运费和保险费付至", "2020", "any",
            "与 CPT 相同，但卖方还必须为货物在运输途中的灭失或损坏风险投保。Incoterms 2020 要求 CIP 下卖方投保最高级别的保险（ICC A 条款或类似条款）。卖方负责出口清关。",
            "Same as CPT, but the seller must also contract for insurance cover against the buyer's risk of loss of or damage to the goods during the carriage. Under Incoterms 2020, CIP requires the seller to obtain insurance with maximum cover (ICC A clauses or similar).",
            "货物交给第一承运人时，风险转移给买方（卖方需投保 ICC A 条款保险）",
            True, 4
        ),
        _t(
            "DAP", "Delivered at Place", "目的地交货", "2020", "any",
            "卖方将货物运至指定目的地，在到达的运输工具上准备好卸货时即完成交货。卖方承担将货物运至目的地的一切风险和费用。买方负责卸货和进口清关。",
            "The seller delivers when the goods are placed at the disposal of the buyer on the arriving means of transport ready for unloading at the named place of destination. The seller bears all risks involved in bringing the goods to the named place.",
            "货物在指定目的地、到达运输工具上准备卸货时，风险转移给买方",
            True, 5
        ),
        _t(
            "DPU", "Delivered at Place Unloaded", "目的地卸货交货", "2020", "any",
            "卖方将货物运至指定目的地并卸货后完成交货。这是唯一要求卖方在目的地卸货的术语。卖方承担将货物运至目的地并卸货的一切风险和费用。买方负责进口清关。该术语取代了 Incoterms 2010 中的 DAT。",
            "The seller delivers when the goods, once unloaded from the arriving means of transport, are placed at the disposal of the buyer at a named place of destination. DPU is the only Incoterms rule that requires the seller to unload goods at destination. Replaces DAT from Incoterms 2010.",
            "货物在指定目的地卸货后，风险转移给买方",
            True, 6
        ),
        _t(
            "DDP", "Delivered Duty Paid", "完税后交货", "2020", "any",
            "卖方承担最大义务：将货物运至指定目的地，办理进口清关并支付一切关税和税费，在到达运输工具上准备好卸货时完成交货。买方只需负责卸货。",
            "The seller delivers the goods when the goods are placed at the disposal of the buyer, cleared for import on the arriving means of transport ready for unloading at the named place of destination. The seller bears all the costs and risks involved in bringing the goods to the place of destination and has an obligation to clear the goods for import and pay all duties and taxes.",
            "货物在指定目的地、到达运输工具上准备卸货时，风险转移给买方（卖方已完成进口清关和缴税）",
            True, 7
        ),

        # ========== Incoterms 2020 - 仅海运和内河运输 ==========
        _t(
            "FAS", "Free Alongside Ship", "船边交货", "2020", "sea",
            "卖方在指定装运港将货物放置在船边（如码头上或驳船上）时完成交货。从那时起，货物灭失或损坏的风险由买方承担。卖方负责出口清关。",
            "The seller delivers when the goods are placed alongside the vessel nominated by the buyer at the named port of shipment. The risk of loss of or damage to the goods passes when the goods are alongside the ship. The seller clears the goods for export.",
            "货物在指定装运港放置于船边时，风险转移给买方",
            True, 8
        ),
        _t(
            "FOB", "Free On Board", "船上交货", "2020", "sea",
            "卖方在指定装运港将货物装上买方指定的船舶时完成交货。从那时起，货物灭失或损坏的风险由买方承担。卖方负责出口清关。这是国际贸易中最常用的术语之一。",
            "The seller delivers the goods on board the vessel nominated by the buyer at the named port of shipment. The risk of loss of or damage to the goods passes when the goods are on board the vessel. The seller clears the goods for export. FOB is one of the most commonly used Incoterms.",
            "货物在指定装运港装上船舶时，风险转移给买方",
            True, 9
        ),
        _t(
            "CFR", "Cost and Freight", "成本加运费", "2020", "sea",
            "卖方将货物装上船舶并支付运费至指定目的港。但货物在装运港装上船后，灭失或损坏的风险即由买方承担。卖方负责出口清关。",
            "The seller delivers the goods on board the vessel at the port of shipment. The seller must contract for and pay the costs and freight necessary to bring the goods to the named port of destination. Risk passes when goods are on board the vessel at the port of shipment.",
            "货物在装运港装上船舶时，风险转移给买方（注意：风险转移点与费用分担点不同）",
            True, 10
        ),
        _t(
            "CIF", "Cost, Insurance and Freight", "成本、保险费加运费", "2020", "sea",
            "与 CFR 相同，但卖方还必须为货物投保海运保险。Incoterms 2020 下 CIF 仅要求最低级别保险（ICC C 条款或类似条款）。这是国际贸易中最常用的术语之一，尤其在海运大宗商品贸易中。",
            "Same as CFR, but the seller must also contract for insurance cover against the buyer's risk of loss of or damage to the goods during the carriage. Under Incoterms 2020, CIF requires only minimum cover (ICC C clauses or similar). CIF is one of the most commonly used Incoterms, especially in maritime commodity trade.",
            "货物在装运港装上船舶时，风险转移给买方（卖方需投保 ICC C 条款最低保险）",
            True, 11
        ),

        # ========== Incoterms 2010 历史术语 ==========
        _t(
            "DAT", "Delivered at Terminal", "目的地码头交货", "2010", "any",
            "卖方将货物运至指定目的港或目的地的指定码头（码头包括码头、仓库、集装箱堆场或公路、铁路、航空货运站等），并在那里卸货后完成交货。该术语在 Incoterms 2020 中被 DPU 取代。",
            "The seller delivers once the goods, once unloaded from the arriving means of transport, are placed at the disposal of the buyer at a named terminal at the named port or place of destination. Replaced by DPU in Incoterms 2020.",
            "货物在指定目的地码头卸货后，风险转移给买方",
            False, 101
        ),

        # ========== Incoterms 2000 历史术语 ==========
        _t(
            "DEQ", "Delivered Ex Quay", "码头交货", "2000", "sea",
            "卖方将货物在指定目的港码头上交给买方处置时完成交货。该术语在 Incoterms 2010 中被 DAT 取代，后来又被 Incoterms 2020 的 DPU 取代。",
            "The seller delivers when the goods are placed at the disposal of the buyer on the quay at the named port of destination. Replaced by DAT in Incoterms 2010.",
            "货物在指定目的港码头上交给买方处置时，风险转移给买方",
            False, 102
        ),
        _t(
            "DES", "Delivered Ex Ship", "船上交货（目的港）", "2000", "sea",
            "卖方将货物运至指定目的港，在船上交给买方处置时完成交货。卖方承担将货物运至目的港的一切风险和费用，但不负责卸货和进口清关。该术语在 Incoterms 2010 中被 DAP 取代。",
            "The seller delivers when the goods are placed at the disposal of the buyer on board the ship at the named port of destination. Replaced by DAP in Incoterms 2010.",
            "货物在目的港船上交给买方处置时，风险转移给买方",
            False, 103
        ),
        _t(
            "DAF", "Delivered at Frontier", "边境交货", "2000", "any",
            "卖方将货物运至边境指定地点，在到达运输工具上准备好卸货时完成交货。主要用于铁路或公路运输的跨境贸易。该术语在 Incoterms 2010 中被 DAP 取代。",
            "The seller delivers when the goods are placed at the disposal of the buyer on the arriving means of transport not unloaded, cleared for export but not cleared for import at the named point and place at the frontier. Replaced by DAP in Incoterms 2010.",
            "货物在边境指定地点、到达运输工具上准备卸货时，风险转移给买方",
            False, 104
        ),
        _t(
            "DDU", "Delivered Duty Unpaid", "未完税交货", "2000", "any",
            "卖方将货物运至指定目的地，在到达运输工具上准备好卸货时完成交货。卖方承担运输风险和费用，但不负责进口清关和缴纳关税。该术语在 Incoterms 2010 中被 DAP 取代。",
            "The seller delivers the goods to the buyer, not cleared for import, and not unloaded from any arriving means of transport at the named place of destination. Replaced by DAP in Incoterms 2010.",
            "货物在指定目的地、到达运输工具上准备卸货时，风险转移给买方（未完税）",
            False, 105
        ),
    ])


def downgrade() -> None:
    op.drop_index('ix_trade_terms_version', table_name='trade_terms')
    op.drop_index('ix_trade_terms_code', table_name='trade_terms')
    op.drop_table('trade_terms')
