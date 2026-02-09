# app/models/__init__.py
# 数据模型包
#
# 这个文件用于导出所有数据模型，方便其他模块导入
# 使用方式：from app.models import User

from app.models.organization import Organization
from app.models.department import Department
from app.models.role import Role, Permission, RolePermission, RoleDataScope
from app.models.user_department import UserDepartment
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
from app.models.payment_method import PaymentMethod
from app.models.warehouse import Warehouse
from app.models.inventory import Inventory
from app.models.contract_number_rule import ContractNumberRule
from app.models.purchase_contract import PurchaseContract, PurchaseLine
from app.models.sales_contract import SalesContract, SalesLine
from app.models.inbound_order import InboundOrder, InboundLine
from app.models.outbound_order import OutboundOrder, OutboundLine
from app.models.project import Project, ProjectAssociation
from app.models.task import Task
from app.models.progress import Progress
from app.models.project_suggestion import ProjectSuggestion
from app.models.client_rfq import ClientRFQ, ClientRFQLine
from app.models.quotation import Quotation, QuotationLine
from app.models.supplier_rfq import SupplierRFQ, SupplierRFQLine
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationLine

# 导出所有模型（方便 Alembic 自动发现）
__all__ = [
    "Organization",
    "Department",
    "Role",
    "Permission",
    "RolePermission",
    "RoleDataScope",
    "UserDepartment",
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
    "PaymentMethod",
    "Warehouse",
    "Inventory",
    "ContractNumberRule",
    "PurchaseContract",
    "PurchaseLine",
    "SalesContract",
    "SalesLine",
    "InboundOrder",
    "InboundLine",
    "OutboundOrder",
    "OutboundLine",
    "Project",
    "ProjectAssociation",
    "Task",
    "Progress",
    "ProjectSuggestion",
    "ClientRFQ",
    "ClientRFQLine",
    "Quotation",
    "QuotationLine",
    "SupplierRFQ",
    "SupplierRFQLine",
    "SupplierQuotation",
    "SupplierQuotationLine",
]
