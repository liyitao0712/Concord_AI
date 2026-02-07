"""add payment_methods table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f7
Create Date: 2026-02-08

付款方式表：
- 系统预置国际贸易常用付款方式
- 包含汇款、信用证、托收、其他四大类
"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pm(code, name_en, name_zh, category, desc_zh, desc_en, is_common, sort_order):
    """构造付款方式数据"""
    return {
        'id': str(uuid4()),
        'code': code,
        'name_en': name_en,
        'name_zh': name_zh,
        'category': category,
        'description_zh': desc_zh,
        'description_en': desc_en,
        'is_common': is_common,
        'sort_order': sort_order,
    }


def upgrade() -> None:
    # 建表
    payment_methods = op.create_table(
        'payment_methods',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(20), nullable=False, unique=True, comment='付款方式代码'),
        sa.Column('name_en', sa.String(200), nullable=False, comment='英文全称'),
        sa.Column('name_zh', sa.String(200), nullable=False, comment='中文名称'),
        sa.Column('category', sa.String(50), nullable=False, comment='分类: remittance/credit/collection/other'),
        sa.Column('description_zh', sa.Text, nullable=True, comment='中文说明'),
        sa.Column('description_en', sa.Text, nullable=True, comment='英文说明'),
        sa.Column('is_common', sa.Boolean, nullable=False, default=False, comment='是否常用'),
        sa.Column('sort_order', sa.Integer, nullable=False, default=0, comment='排序序号'),
        sa.Column('created_at', sa.DateTime, nullable=True),
    )

    # 索引
    op.create_index('ix_payment_methods_code', 'payment_methods', ['code'], unique=True)
    op.create_index('ix_payment_methods_category', 'payment_methods', ['category'])

    # ==================== 灌入预置数据 ====================
    data = [
        # ---------- 汇款类 (remittance) ----------
        _pm('T/T', 'Telegraphic Transfer', '电汇', 'remittance',
            '通过银行电报或电子方式将货款直接汇入卖方银行账户，是目前国际贸易中最常用的付款方式。通常分为预付（T/T in advance）和后付（T/T after shipment）。',
            'Payment transferred electronically through the banking system directly to the seller\'s bank account. The most common payment method in international trade, typically split into advance payment and post-shipment payment.',
            True, 1),
        _pm('M/T', 'Mail Transfer', '信汇', 'remittance',
            '汇款银行通过邮寄付款委托书方式将款项汇给收款人所在地的银行（解付行），由其解付给收款人。速度较慢，现已较少使用。',
            'Payment instruction sent by mail from the remitting bank to the paying bank. Slower than T/T, rarely used today.',
            False, 2),
        _pm('D/D', 'Demand Draft', '票汇', 'remittance',
            '由汇款银行开立以解付行为付款人的银行即期汇票，交由汇款人自行寄送或携带至收款人处，凭票取款。',
            'A bank draft issued by the remitting bank, payable on demand at the paying bank. The remitter sends or carries the draft to the payee.',
            False, 3),

        # ---------- 信用证类 (credit) ----------
        _pm('L/C at Sight', 'Letter of Credit at Sight', '即期信用证', 'credit',
            '开证银行或付款银行在收到符合信用证条款的单据后立即付款。对出口商较安全，银行信用担保。',
            'The issuing or paying bank makes payment immediately upon receipt of compliant documents. Provides strong security for the exporter with bank credit guarantee.',
            True, 10),
        _pm('L/C Usance', 'Usance Letter of Credit', '远期信用证', 'credit',
            '开证银行在收到符合信用证条款的单据后，在规定的远期日期（如 30/60/90/180 天）到期时付款。买方可以获得融资时间。',
            'Payment is made at a future date (e.g., 30/60/90/180 days) after presentation of compliant documents. Provides financing time for the buyer.',
            True, 11),
        _pm('Standby L/C', 'Standby Letter of Credit', '备用信用证', 'credit',
            '作为担保工具，当买方未能按合同付款时，卖方可以凭备用信用证向银行索赔。类似银行保函。',
            'Serves as a guarantee instrument. If the buyer fails to pay per the contract, the seller can claim payment from the bank under the standby L/C. Similar to a bank guarantee.',
            False, 12),

        # ---------- 托收类 (collection) ----------
        _pm('D/P at Sight', 'Documents against Payment at Sight', '即期付款交单', 'collection',
            '出口商通过银行向进口商提示单据，进口商付款后才能取得货运单据。即期 D/P 要求买方见票即付。',
            'The exporter presents documents through a bank. The importer must pay upon presentation to obtain the shipping documents.',
            True, 20),
        _pm('D/P after Sight', 'Documents against Payment after Sight', '远期付款交单', 'collection',
            '进口商在承兑汇票后，于到期日付款才能取得货运单据。出口商承担一定信用风险。',
            'The importer accepts a time draft and pays at maturity to obtain shipping documents. The exporter bears some credit risk.',
            False, 21),
        _pm('D/A', 'Documents against Acceptance', '承兑交单', 'collection',
            '进口商在承兑汇票后即可取得货运单据，到期日再付款。出口商风险较大，依赖买方商业信用。',
            'The importer obtains shipping documents upon accepting a time draft, with payment due at maturity. Higher risk for the exporter, relying on the buyer\'s commercial credit.',
            False, 22),

        # ---------- 其他 (other) ----------
        _pm('O/A', 'Open Account', '赊销（放账）', 'other',
            '卖方先发货，买方在约定期限内（如 30/60/90 天）付款。对买方最有利，卖方承担全部风险。常用于信任度高的老客户。',
            'The seller ships goods first, and the buyer pays within an agreed period. Most favorable for the buyer; the seller bears all risk. Common for trusted long-term customers.',
            True, 30),
        _pm('CAD', 'Cash against Documents', '凭单付款', 'other',
            '买方在收到卖方提交的货运单据后即行付款。与 D/P 类似，但通常不通过银行托收渠道。',
            'The buyer pays upon receipt of shipping documents from the seller. Similar to D/P but usually without using the bank collection channel.',
            False, 31),
        _pm('DP', 'Down Payment', '预付定金', 'other',
            '买方在下单时支付部分货款作为定金，余款在发货前后支付。常见比例为 30% 定金 + 70% 发货前。',
            'The buyer pays a partial amount as deposit when placing the order, with the balance paid before or after shipment. Common ratio: 30% deposit + 70% before shipment.',
            True, 32),
        _pm('CIA', 'Cash in Advance', '预付货款', 'other',
            '买方在卖方发货前全额付款。对卖方最有利，无任何风险。通常用于小额订单或新客户首单。',
            'Full payment by the buyer before the seller ships the goods. Most favorable for the seller with zero risk. Typically used for small orders or first orders from new customers.',
            False, 33),
        _pm('COD', 'Cash on Delivery', '货到付款', 'other',
            '货物送达买方后，买方当场支付货款。多用于国内贸易或跨境电商小包裹。',
            'Payment is made by the buyer upon delivery of goods. Commonly used in domestic trade or cross-border e-commerce small parcels.',
            False, 34),
        _pm('Escrow', 'Escrow Payment', '第三方托管支付', 'other',
            '买方将货款交给第三方托管机构，待买方确认收货后，托管机构将款项释放给卖方。如阿里巴巴信保交易。',
            'The buyer deposits payment with a third-party escrow service, which releases funds to the seller after the buyer confirms receipt. E.g., Alibaba Trade Assurance.',
            False, 35),
        _pm('Mixed', 'Mixed Payment', '混合支付方式', 'other',
            '组合使用多种付款方式，如「30% T/T 定金 + 70% L/C 即期」。可灵活满足买卖双方需求。',
            'A combination of multiple payment methods, e.g., "30% T/T deposit + 70% L/C at sight". Flexibly meets the needs of both buyers and sellers.',
            False, 36),
    ]

    op.bulk_insert(payment_methods, data)


def downgrade() -> None:
    op.drop_index('ix_payment_methods_category', table_name='payment_methods')
    op.drop_index('ix_payment_methods_code', table_name='payment_methods')
    op.drop_table('payment_methods')
