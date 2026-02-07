# app/models/__init__.py
# 数据模型包
#
# 这个文件用于导出所有数据模型，方便其他模块导入
# 使用方式：from app.models import User

from app.models.user import User
from app.models.prompt import Prompt, PromptHistory
from app.models.settings import SystemSetting
from app.models.execution import WorkflowExecution, AgentExecution
from app.models.chat import ChatSession, ChatMessage
from app.models.event import Event, EventStatus, EventType, EventSource
from app.models.email_account import EmailAccount, EmailPurpose
from app.models.worker import WorkerConfig
from app.models.email_raw import EmailRawMessage, EmailAttachment
from app.models.email_analysis import EmailAnalysis
from app.models.llm_model_config import LLMModelConfig
from app.models.work_type import WorkType, WorkTypeSuggestion
from app.models.customer import Customer, Contact
from app.models.customer_suggestion import CustomerSuggestion
from app.models.supplier import Supplier, SupplierContact
from app.models.category import Category
from app.models.product import Product, ProductSupplier
from app.models.country import Country
from app.models.trade_term import TradeTerm

# 导出所有模型（方便 Alembic 自动发现）
__all__ = [
    "User",
    "Prompt",
    "PromptHistory",
    "SystemSetting",
    "WorkflowExecution",
    "AgentExecution",
    "ChatSession",
    "ChatMessage",
    "Event",
    "EventStatus",
    "EventType",
    "EventSource",
    "EmailAccount",
    "EmailPurpose",
    "WorkerConfig",
    "EmailRawMessage",
    "EmailAttachment",
    "EmailAnalysis",
    "LLMModelConfig",
    "WorkType",
    "WorkTypeSuggestion",
    "Customer",
    "Contact",
    "CustomerSuggestion",
    "Supplier",
    "SupplierContact",
    "Category",
    "Product",
    "ProductSupplier",
    "Country",
    "TradeTerm",
]
