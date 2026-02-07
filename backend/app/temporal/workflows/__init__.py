# app/temporal/workflows/__init__.py
# Temporal Workflows 包

from app.temporal.workflows.work_type_suggestion import WorkTypeSuggestionWorkflow
from app.temporal.workflows.customer_approval import CustomerApprovalWorkflow

__all__ = [
    "WorkTypeSuggestionWorkflow",
    "CustomerApprovalWorkflow",
]
