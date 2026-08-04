from typing import Dict, Any, Optional
from ..utils.logger import kiki_logger


class PersonaManager:
    """
    Component — Persona Manager
    Adapts response language, depth, and detail level to match user persona/role:
    - Finance Manager: Financial summaries & strategic metrics.
    - Accountant: Deep accounting ledger & transaction context.
    - Administrator: System operations & administrative context.
    - CEO: Executive summary & high-level highlights.
    - Developer: Technical metrics & architecture context.
    """

    VALID_PERSONAS = {
        "Finance Manager",
        "Accountant",
        "Administrator",
        "CEO",
        "Developer"
    }

    ROLE_MAP = {
        "finance_manager": "Finance Manager",
        "finance": "Finance Manager",
        "manager": "Finance Manager",
        "accountant": "Accountant",
        "auditor": "Accountant",
        "admin": "Administrator",
        "administrator": "Administrator",
        "ceo": "CEO",
        "director": "CEO",
        "executive": "CEO",
        "developer": "Developer",
        "dev": "Developer",
    }

    @classmethod
    def resolve_persona(cls, user_permissions: Optional[Dict[str, Any]] = None, context_dict: Optional[Dict[str, Any]] = None) -> str:
        if context_dict and context_dict.get("persona") in cls.VALID_PERSONAS:
            return context_dict["persona"]

        if user_permissions:
            role = str(user_permissions.get("role", "")).lower()
            if role in cls.ROLE_MAP:
                return cls.ROLE_MAP[role]

        if context_dict:
            user_role = str(context_dict.get("user_role", "")).lower()
            if user_role in cls.ROLE_MAP:
                return cls.ROLE_MAP[user_role]

        return "Accountant"  # Default ERP persona

    @classmethod
    def format_summary_for_persona(cls, persona: str, base_summary: str, result_val: Optional[str] = None) -> str:
        if persona == "CEO":
            if result_val:
                return f"Executive Brief: Key figure stands at {result_val}. {base_summary}"
            return f"Executive Brief: {base_summary}"
        elif persona == "Finance Manager":
            return f"Financial Perspective: {base_summary}"
        elif persona == "Administrator":
            return f"Operational View: {base_summary}"
        elif persona == "Developer":
            return f"Technical/Data Context: {base_summary}"
        return base_summary
