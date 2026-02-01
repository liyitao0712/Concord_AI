# app/tools/email_cleaner.py
# 邮件清洗工具
#
# 功能说明：
# 1. 清洗邮件正文，减少 LLM token 消耗
# 2. 移除签名、引用历史、HTML 标签等
# 3. 提取核心正文内容

import re
from typing import Optional

from app.core.logging import get_logger
from app.tools.base import BaseTool, tool
from app.tools.registry import register_tool

logger = get_logger(__name__)


# 签名块开始的常见标识
SIGNATURE_PATTERNS = [
    # 英文签名
    r"^--\s*$",                          # -- (标准签名分隔符)
    r"^_{3,}",                            # ___
    r"^-{3,}",                            # ---
    r"^Best\s+regards?[,.]?\s*$",
    r"^Kind\s+regards?[,.]?\s*$",
    r"^Warm\s+regards?[,.]?\s*$",
    r"^Regards[,.]?\s*$",
    r"^Sincerely[,.]?\s*$",
    r"^Thanks?[,.]?\s*$",
    r"^Thank\s+you[,.]?\s*$",
    r"^Cheers[,.]?\s*$",
    r"^Yours\s+(truly|sincerely|faithfully)[,.]?\s*$",
    # 中文签名
    r"^此致[,.]?\s*$",
    r"^敬祝[,.]?\s*$",
    r"^顺祝[,.]?\s*$",
    r"^祝好[,.]?\s*$",
    r"^谢谢[,.]?\s*$",
    # 移动设备签名
    r"^发自我的\s*(iPhone|iPad|华为|小米|Android)",
    r"^Sent\s+from\s+(my\s+)?(iPhone|iPad|Galaxy|Android|Outlook|Mail)",
    r"^Get\s+Outlook\s+for\s+(iOS|Android)",
]

# 引用历史的标识
QUOTE_PATTERNS = [
    r"^On\s+.+wrote:\s*$",               # On ... wrote:
    r"^在\s*.+写道：?\s*$",               # 在 ... 写道：
    r"^From:\s+.+$",                      # From: ...
    r"^发件人：\s*.+$",                   # 发件人：...
    r"^-+\s*Original\s+Message\s*-+",    # ----- Original Message -----
    r"^-+\s*原始邮件\s*-+",               # ----- 原始邮件 -----
    r"^-+\s*Forwarded\s+message\s*-+",   # ----- Forwarded message -----
    r"^>+\s*",                            # > 引用行
]

# 需要移除的 HTML 标签和实体
HTML_CLEANUP_PATTERNS = [
    (r"<style[^>]*>.*?</style>", "", re.DOTALL | re.IGNORECASE),
    (r"<script[^>]*>.*?</script>", "", re.DOTALL | re.IGNORECASE),
    (r"<head[^>]*>.*?</head>", "", re.DOTALL | re.IGNORECASE),
    (r"<[^>]+>", " ", 0),                 # 所有 HTML 标签
    (r"&nbsp;", " ", 0),
    (r"&lt;", "<", 0),
    (r"&gt;", ">", 0),
    (r"&amp;", "&", 0),
    (r"&quot;", '"', 0),
    (r"&#\d+;", "", 0),                   # 数字实体
]


def clean_html(html_content: str) -> str:
    """
    清洗 HTML 内容，提取纯文本

    Args:
        html_content: HTML 内容

    Returns:
        str: 纯文本内容
    """
    if not html_content:
        return ""

    text = html_content

    for pattern, replacement, flags in HTML_CLEANUP_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=flags)

    # 清理多余空白
    text = re.sub(r"\s+", " ", text)
    text = text.strip()

    return text


def remove_signature(text: str) -> str:
    """
    移除邮件签名块

    Args:
        text: 邮件正文

    Returns:
        str: 移除签名后的正文
    """
    if not text:
        return ""

    lines = text.split("\n")
    result_lines = []
    signature_started = False

    for line in lines:
        # 检查是否是签名开始
        if not signature_started:
            for pattern in SIGNATURE_PATTERNS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    signature_started = True
                    break

        if not signature_started:
            result_lines.append(line)

    return "\n".join(result_lines)


def remove_quoted_content(text: str) -> str:
    """
    移除引用的历史邮件内容

    Args:
        text: 邮件正文

    Returns:
        str: 移除引用后的正文
    """
    if not text:
        return ""

    lines = text.split("\n")
    result_lines = []
    quote_started = False

    for line in lines:
        stripped = line.strip()

        # 检查是否是引用开始（非 > 开头的引用标识）
        if not quote_started:
            for pattern in QUOTE_PATTERNS[:-1]:  # 排除 > 模式
                if re.match(pattern, stripped, re.IGNORECASE):
                    quote_started = True
                    break

        # 如果已经开始引用，跳过后续所有内容
        if quote_started:
            continue

        # 跳过以 > 开头的引用行
        if stripped.startswith(">"):
            continue

        result_lines.append(line)

    return "\n".join(result_lines)


def normalize_whitespace(text: str) -> str:
    """
    规范化空白字符

    Args:
        text: 文本内容

    Returns:
        str: 规范化后的文本
    """
    if not text:
        return ""

    # 将多个空行替换为单个空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 移除行尾空白
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)

    # 移除首尾空白
    text = text.strip()

    return text


def truncate_content(text: str, max_length: int = 3000) -> str:
    """
    截断过长的内容

    Args:
        text: 文本内容
        max_length: 最大长度

    Returns:
        str: 截断后的文本
    """
    if not text or len(text) <= max_length:
        return text

    # 尝试在句子边界截断
    truncated = text[:max_length]

    # 找最后一个句号/问号/感叹号
    for sep in ["。", ".", "！", "!", "？", "?"]:
        last_sep = truncated.rfind(sep)
        if last_sep > max_length * 0.7:  # 至少保留 70%
            return truncated[:last_sep + 1]

    # 找最后一个换行
    last_newline = truncated.rfind("\n")
    if last_newline > max_length * 0.7:
        return truncated[:last_newline]

    return truncated + "..."


@register_tool
class EmailCleanerTool(BaseTool):
    """
    邮件清洗工具

    提供邮件正文清洗功能，减少 LLM token 消耗：
    1. 移除 HTML 标签
    2. 移除签名块
    3. 移除引用的历史邮件
    4. 规范化空白
    5. 截断过长内容
    """

    name = "email_cleaner"
    description = "邮件正文清洗工具，提取核心内容"

    @tool(
        name="clean_email",
        description="清洗邮件正文，移除签名、HTML 等，提取核心内容",
        parameters={
            "body_text": {
                "type": "string",
                "description": "邮件纯文本正文",
            },
            "body_html": {
                "type": "string",
                "description": "邮件 HTML 正文（可选，会转换为纯文本）",
            },
            "max_length": {
                "type": "integer",
                "description": "最大长度，超过会截断（默认 10000）",
            },
            "remove_signature": {
                "type": "boolean",
                "description": "是否移除签名（默认 true）",
            },
            "remove_quotes": {
                "type": "boolean",
                "description": "是否移除引用历史（默认 false，保留历史邮件）",
            },
        },
    )
    async def clean_email(
        self,
        body_text: str = "",
        body_html: str = "",
        max_length: int = 10000,
        remove_signature_flag: bool = True,
        remove_quotes: bool = False,
    ) -> dict:
        """
        清洗邮件正文

        Args:
            body_text: 邮件纯文本正文
            body_html: 邮件 HTML 正文（可选）
            max_length: 最大长度
            remove_signature_flag: 是否移除签名
            remove_quotes: 是否移除引用历史

        Returns:
            dict: {"cleaned_content": str, "original_length": int, "cleaned_length": int}
        """
        # 优先使用纯文本，HTML 作为备选
        if body_text and body_text.strip():
            content = body_text
        elif body_html:
            content = clean_html(body_html)
        else:
            return {
                "cleaned_content": "",
                "original_length": 0,
                "cleaned_length": 0,
            }

        original_length = len(content)

        # 移除签名
        if remove_signature_flag:
            content = remove_signature(content)

        # 移除引用历史
        if remove_quotes:
            content = remove_quoted_content(content)

        # 规范化空白
        content = normalize_whitespace(content)

        # 截断
        content = truncate_content(content, max_length)

        cleaned_length = len(content)

        logger.debug(
            f"[EmailCleaner] 清洗完成: {original_length} -> {cleaned_length} 字符 "
            f"(减少 {((original_length - cleaned_length) / original_length * 100):.1f}%)"
        )

        return {
            "cleaned_content": content,
            "original_length": original_length,
            "cleaned_length": cleaned_length,
        }


# 便捷函数，供直接调用
async def clean_email_content(
    body_text: str = "",
    body_html: str = "",
    max_length: int = 10000,
    remove_signature: bool = False,
    remove_quotes: bool = False,
) -> str:
    """
    清洗邮件正文的便捷函数

    Args:
        body_text: 邮件纯文本正文
        body_html: 邮件 HTML 正文（可选）
        max_length: 最大长度（默认 10000）
        remove_signature: 是否移除签名（默认 False，保留签名）
        remove_quotes: 是否移除引用历史（默认 False，保留历史邮件）

    Returns:
        str: 清洗后的正文
    """
    tool = EmailCleanerTool()
    result = await tool.clean_email(
        body_text=body_text,
        body_html=body_html,
        max_length=max_length,
        remove_signature_flag=remove_signature,
        remove_quotes=remove_quotes,
    )
    return result["cleaned_content"]
