import re
from typing import Dict, Any, Optional
from ..utils.logger import kiki_logger


class NavigationRegistry:
    """
    Component — Configuration-Driven Navigation Registry & Alias Resolver
    Maintains deterministic ERP module aliases and configuration-driven frontend routes.
    Bypasses LLM investigation, QuestionUnderstanding, Planner, QueryBuilder, and SQL execution.
    """

    NAV_VERBS = [
        "go to", "open", "navigate", "take me to", "show page", "show", "launch",
        "switch to", "move to", "view page", "view", "go", "create"
    ]

    MODULE_REGISTRY = [
        {
            "module": "Voucher",
            "route": "/dashboard?page=vouchers",
            "aliases": ["voucher", "vouchers", "voucher entry", "voucher master", "voucher page", "create voucher"]
        },
        {
            "module": "Vendor Portal",
            "route": "/dashboard?page=vendor-portal",
            "aliases": ["vendor", "vendors", "supplier", "supplier portal", "vendor master", "vendor portal", "create vendor"]
        },
        {
            "module": "Customer Portal",
            "route": "/dashboard?page=customer-portal",
            "aliases": ["customer", "customers", "customer portal", "customer master", "client", "client master", "create customer"]
        },
        {
            "module": "Inventory",
            "route": "/dashboard?page=inventory",
            "aliases": ["inventory", "stock", "items", "warehouse", "item master", "products"]
        },
        {
            "module": "Dashboard",
            "route": "/dashboard?page=dashboard",
            "aliases": ["dashboard", "home", "main page", "overview"]
        },
        {
            "module": "Purchase",
            "route": "/dashboard?page=purchase",
            "aliases": ["purchase", "purchases", "purchase order", "purchase orders", "po", "pending purchase", "purchase voucher"]
        },
        {
            "module": "Sales",
            "route": "/dashboard?page=sales",
            "aliases": ["sales", "sales order", "sales orders", "sales quotation"]
        },
        {
            "module": "Reports",
            "route": "/dashboard?page=reports",
            "aliases": ["reports", "analytics", "dashboard reports", "financial reports", "sales report"]
        },
        {
            "module": "GST",
            "route": "/dashboard?page=gst",
            "aliases": ["gst", "gstr1", "gstr-1", "gstr3b", "gstr-3b", "returns", "gst report"]
        },
        {
            "module": "Ledgers",
            "route": "/dashboard?page=ledgers",
            "aliases": ["ledger", "ledgers", "accounting master", "chart of accounts"]
        },
        {
            "module": "Bank Upload",
            "route": "/dashboard?page=bank-upload",
            "aliases": ["bank upload", "bank statement", "bank reconciliation"]
        }
    ]

    @classmethod
    def is_navigation_query(cls, question: str) -> bool:
        """
        Deterministic navigation detection rule.
        Returns True if the query contains a navigation verb and module alias.
        """
        if not question or not isinstance(question, str):
            return False

        clean_q = question.strip().lower()

        # Direct exact match check on aliases
        for entry in cls.MODULE_REGISTRY:
            for alias in entry["aliases"]:
                for verb in cls.NAV_VERBS:
                    if clean_q == f"{verb} {alias}" or clean_q == f"{verb} the {alias}":
                        return True

        # Verb + Alias pattern match
        has_verb = any(v in clean_q for v in cls.NAV_VERBS)
        if not has_verb:
            return False

        has_alias = False
        for entry in cls.MODULE_REGISTRY:
            for alias in entry["aliases"]:
                if alias in clean_q:
                    has_alias = True
                    break
            if has_alias:
                break

        return has_verb and has_alias

    @classmethod
    def resolve_route(cls, question: str) -> Dict[str, Any]:
        """
        Resolves query to structured Navigation Contract payload.
        Issue 4: Structured response contract only (zero natural language chat output, zero SQL execution).
        """
        clean_q = question.strip().lower()

        for entry in cls.MODULE_REGISTRY:
            for alias in entry["aliases"]:
                if alias in clean_q:
                    module_name = entry["module"]
                    route = entry["route"]
                    msg = f"Navigating to {module_name} ({route})."
                    kiki_logger.info(f"[NAVIGATION REGISTRY] Matched query '{question}' -> Route '{route}' ({module_name})")
                    return {
                        "intent": "NAVIGATION",
                        "module": module_name,
                        "route": route,
                        "action": "open",
                        "confidence": 0.99,
                        "final_response": msg,
                        "reply": msg,
                        "investigation_steps": [],
                        "evidences": []
                    }

        # Fallback default dashboard navigation
        msg = "Navigating to Dashboard (/dashboard?page=dashboard)."
        return {
            "intent": "NAVIGATION",
            "module": "Dashboard",
            "route": "/dashboard?page=dashboard",
            "action": "open",
            "confidence": 0.99,
            "final_response": msg,
            "reply": msg,
            "investigation_steps": [],
            "evidences": []
        }
