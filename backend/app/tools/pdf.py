# app/tools/pdf.py
# PDF 生成工具
#
# 功能说明：
# 1. 生成报价单 PDF
# 2. 上传到 OSS
# 3. 返回签名访问链接
#
# 使用方法：
#   from app.tools.pdf import PDFTool
#
#   pdf_tool = PDFTool()
#   result = await pdf_tool.generate_quote_pdf(
#       customer_name="客户名称",
#       items=[{"name": "产品A", "quantity": 10, "unit_price": 100, "total": 1000}],
#       total_price=1000,
#   )
#   print(result["url"])  # OSS 签名链接
#
# 依赖：
#   pip install reportlab

import io
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.oss import oss_client
from app.tools.base import BaseTool, tool
from app.tools.registry import register_tool

logger = get_logger(__name__)


# 尝试注册中文字体
# 如果没有中文字体，使用默认字体（可能无法显示中文）
_chinese_font_registered = False

def _register_chinese_font():
    """注册中文字体"""
    global _chinese_font_registered
    if _chinese_font_registered:
        return

    # 尝试常见的中文字体路径
    font_paths = [
        # macOS
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]

    for font_path in font_paths:
        try:
            pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
            _chinese_font_registered = True
            logger.info(f"[PDFTool] 注册中文字体成功: {font_path}")
            return
        except Exception:
            continue

    logger.warning("[PDFTool] 未找到中文字体，PDF 可能无法正确显示中文")


@register_tool
class PDFTool(BaseTool):
    """
    PDF 生成工具

    提供 PDF 文档生成功能，目前支持：
    - 报价单 PDF 生成
    """

    name = "pdf"
    description = "PDF 文档生成工具"

    def __init__(self):
        super().__init__()
        _register_chinese_font()

    @tool(
        name="generate_quote_pdf",
        description="生成报价单 PDF 文档，上传到 OSS 并返回访问链接",
        parameters={
            "customer_name": {
                "type": "string",
                "description": "客户名称"
            },
            "items": {
                "type": "array",
                "description": "报价明细列表，每项包含 name, quantity, unit_price, total"
            },
            "total_price": {
                "type": "number",
                "description": "总价"
            },
            "currency": {
                "type": "string",
                "description": "货币单位，默认 CNY",
                "default": "CNY"
            },
            "valid_days": {
                "type": "integer",
                "description": "报价有效期（天），默认 7 天",
                "default": 7
            },
            "quote_no": {
                "type": "string",
                "description": "报价单号，不提供则自动生成"
            },
            "notes": {
                "type": "string",
                "description": "备注信息"
            },
        }
    )
    async def generate_quote_pdf(
        self,
        customer_name: str,
        items: list[dict],
        total_price: float,
        currency: str = "CNY",
        valid_days: int = 7,
        quote_no: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """
        生成报价单 PDF

        Args:
            customer_name: 客户名称
            items: 报价明细列表
            total_price: 总价
            currency: 货币单位
            valid_days: 报价有效期（天）
            quote_no: 报价单号
            notes: 备注信息

        Returns:
            dict: {
                "success": bool,
                "url": str,  # OSS 签名链接
                "quote_no": str,  # 报价单号
                "file_key": str,  # OSS 文件路径
            }
        """
        try:
            # 生成报价单号
            if not quote_no:
                quote_no = f"Q{datetime.now().strftime('%Y%m%d')}{str(uuid4())[:8].upper()}"

            # 计算有效期
            valid_until = datetime.now() + timedelta(days=valid_days)

            # 生成 PDF 内容
            pdf_buffer = await asyncio.to_thread(
                self._generate_quote_pdf_content,
                customer_name=customer_name,
                items=items,
                total_price=total_price,
                currency=currency,
                valid_until=valid_until,
                quote_no=quote_no,
                notes=notes,
            )

            # 上传到 OSS
            file_key = f"quotes/{datetime.now().strftime('%Y/%m')}/{quote_no}.pdf"

            await oss_client.upload(
                key=file_key,
                data=pdf_buffer.getvalue(),
                content_type="application/pdf"
            )

            # 生成签名链接（7 天有效）
            url = oss_client.get_signed_url(file_key, expires=7 * 24 * 3600)

            logger.info(f"[PDFTool] 生成报价单成功: {quote_no}")

            return {
                "success": True,
                "url": url,
                "quote_no": quote_no,
                "file_key": file_key,
            }

        except Exception as e:
            logger.error(f"[PDFTool] 生成报价单失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "quote_no": quote_no,
            }

    def _generate_quote_pdf_content(
        self,
        customer_name: str,
        items: list[dict],
        total_price: float,
        currency: str,
        valid_until: datetime,
        quote_no: str,
        notes: Optional[str],
    ) -> io.BytesIO:
        """
        生成 PDF 内容（同步方法）

        Returns:
            io.BytesIO: PDF 文件内容
        """
        buffer = io.BytesIO()

        # 创建 PDF 文档
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        # 获取样式
        styles = getSampleStyleSheet()

        # 创建自定义样式
        if _chinese_font_registered:
            title_style = ParagraphStyle(
                "ChineseTitle",
                parent=styles["Title"],
                fontName="ChineseFont",
                fontSize=18,
                spaceAfter=20,
            )
            normal_style = ParagraphStyle(
                "ChineseNormal",
                parent=styles["Normal"],
                fontName="ChineseFont",
                fontSize=10,
            )
        else:
            title_style = styles["Title"]
            normal_style = styles["Normal"]

        # 构建内容
        elements = []

        # 标题
        elements.append(Paragraph("报价单", title_style))
        elements.append(Spacer(1, 10))

        # 基本信息
        info_data = [
            ["报价单号：", quote_no],
            ["客户名称：", customer_name],
            ["报价日期：", datetime.now().strftime("%Y-%m-%d")],
            ["有效期至：", valid_until.strftime("%Y-%m-%d")],
        ]

        info_table = Table(info_data, colWidths=[80, 300])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "ChineseFont" if _chinese_font_registered else "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # 明细表头
        headers = ["序号", "产品名称", "数量", "单价", "金额"]

        # 明细数据
        table_data = [headers]
        for i, item in enumerate(items, 1):
            row = [
                str(i),
                item.get("name", ""),
                str(item.get("quantity", "")),
                f"{currency} {item.get('unit_price', 0):,.2f}",
                f"{currency} {item.get('total', 0):,.2f}",
            ]
            table_data.append(row)

        # 合计行
        table_data.append(["", "", "", "合计：", f"{currency} {total_price:,.2f}"])

        # 创建表格
        col_widths = [40, 200, 60, 80, 100]
        detail_table = Table(table_data, colWidths=col_widths)
        detail_table.setStyle(TableStyle([
            # 字体
            ("FONTNAME", (0, 0), (-1, -1), "ChineseFont" if _chinese_font_registered else "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            # 表头样式
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, 0), 11),
            # 对齐
            ("ALIGN", (0, 0), (0, -1), "CENTER"),  # 序号居中
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),  # 数字右对齐
            # 边框
            ("GRID", (0, 0), (-1, -2), 0.5, colors.black),
            # 合计行样式
            ("FONTNAME", (3, -1), (-1, -1), "ChineseFont" if _chinese_font_registered else "Helvetica-Bold"),
            ("LINEABOVE", (3, -1), (-1, -1), 1, colors.black),
            # 内边距
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(detail_table)
        elements.append(Spacer(1, 20))

        # 备注
        if notes:
            elements.append(Paragraph(f"备注：{notes}", normal_style))
            elements.append(Spacer(1, 10))

        # 页脚信息
        footer_text = "本报价单有效期内有效，如有疑问请联系销售人员。"
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(footer_text, normal_style))

        # 生成 PDF
        doc.build(elements)

        buffer.seek(0)
        return buffer

    @tool(
        name="check_pdf_status",
        description="检查 PDF 工具状态",
    )
    async def check_pdf_status(self) -> dict:
        """
        检查 PDF 工具状态

        Returns:
            dict: {
                "available": bool,
                "chinese_font": bool,
                "oss_configured": bool,
            }
        """
        return {
            "available": True,
            "chinese_font": _chinese_font_registered,
            "oss_configured": bool(settings.OSS_ACCESS_KEY_ID and settings.OSS_BUCKET),
        }


# 全局单例
pdf_tool = PDFTool()
