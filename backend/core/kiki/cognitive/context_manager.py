from typing import Dict, Any, Optional, List
from ..models.dto import ContextState
from ..utils.logger import kiki_logger


class ContextManager:
    """
    Component — Context Manager (Kiki 2.0)
    Single source of conversational & ERP context truth.

    Maintains:
    - Current Page, Active Module, Company, Branch, Financial Year
    - Active Dashboard Filters, Active Period
    - User Persona & Role
    - Selected Business Entity (Customer, Vendor, Voucher)
    - Previous Investigation Results & Workflow State
    - Cumulative Multi-turn Constraints
    """

    def __init__(self, state: Optional[ContextState] = None):
        self.state = state or ContextState(question="")

    @classmethod
    def build_context(
        cls,
        question: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> ContextState:
        ctx = context_dict or {}
        perms = user_permissions or {}

        # Resolve persona
        persona = ctx.get("persona") or perms.get("role") or "Accountant"

        state = ContextState(
            question=question.strip(),
            tenant_id=str(ctx.get("tenant_id", "") or ""),
            company_name=ctx.get("company_name") or "Active Company",
            branch_name=ctx.get("branch_name") or "Main Branch",
            financial_year=ctx.get("financial_year", "2025-2026"),
            current_page=ctx.get("current_page", "Dashboard"),
            active_module=ctx.get("active_module", "Accounting ERP"),
            dashboard_filters=ctx.get("dashboard_filters", {}),
            active_period=ctx.get("active_period", "current_month"),
            persona=persona,
            user_role=perms.get("role") or ctx.get("user_role"),
            selected_entity=ctx.get("selected_entity"),
            previous_investigations=ctx.get("previous_investigations", []),
            workflow_state=ctx.get("workflow_state", {}),
            cumulative_constraints=ctx.get("cumulative_constraints", {})
        )

        kiki_logger.info(
            f"[CONTEXT MANAGER] Context State initialized for query: '{question}' "
            f"(Page: {state.current_page}, Persona: {state.persona}, FY: {state.financial_year})"
        )
        return state
