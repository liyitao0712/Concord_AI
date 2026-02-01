# app/prompts/__init__.py
# Prompt 模板包
#
# 这个文件用于导出所有 Prompt 模板，方便其他模块导入
# 使用方式：from app.prompts import INTENT_CLASSIFIER_PROMPT

# 基础模块
from app.prompts.base import (
    PromptTemplate,
    SystemPrompt,
    ASSISTANT_SYSTEM,
    JSON_OUTPUT_SYSTEM,
)

# 意图分类
from app.prompts.intent import (
    INTENT_SYSTEM,
    INTENT_CLASSIFIER_PROMPT,
    EMAIL_INTENT_PROMPT,
    BATCH_INTENT_PROMPT,
)

# 实体提取
from app.prompts.extraction import (
    EXTRACTION_SYSTEM,
    ENTITY_EXTRACTION_PROMPT,
    INQUIRY_EXTRACTION_PROMPT,
    ORDER_EXTRACTION_PROMPT,
    CONTACT_EXTRACTION_PROMPT,
)

__all__ = [
    # 基础
    "PromptTemplate",
    "SystemPrompt",
    "ASSISTANT_SYSTEM",
    "JSON_OUTPUT_SYSTEM",
    # 意图分类
    "INTENT_SYSTEM",
    "INTENT_CLASSIFIER_PROMPT",
    "EMAIL_INTENT_PROMPT",
    "BATCH_INTENT_PROMPT",
    # 实体提取
    "EXTRACTION_SYSTEM",
    "ENTITY_EXTRACTION_PROMPT",
    "INQUIRY_EXTRACTION_PROMPT",
    "ORDER_EXTRACTION_PROMPT",
    "CONTACT_EXTRACTION_PROMPT",
]
