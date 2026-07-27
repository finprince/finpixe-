from typing import Dict, Any, Optional
from ..utils.logger import kiki_logger


class ActionEngine:
    """
    Specialized Engine — Action Engine
    Handles user operations requests (e.g. 'Create Vendor', 'Approve Invoice', 'Generate Voucher', 'Delete Customer').
    Provides step-by-step action guidance and launches the appropriate workspace form.
    """

    ACTION_ROUTES = {
        "vendor": {"title": "Vendor Portal", "route": "/dashboard?page=vendor-portal", "action": "Create Vendor / Manage Vendors"},
        "customer": {"title": "Customer Portal", "route": "/dashboard?page=customer-portal", "action": "Manage Customers"},
        "voucher": {"title": "Voucher Entry", "route": "/dashboard?page=vouchers", "action": "Generate Voucher"},
        "invoice": {"title": "Pending Purchases", "route": "/dashboard?page=pending-purchases", "action": "Approve OCR Invoices"},
        "inventory": {"title": "Inventory Management", "route": "/dashboard?page=inventory", "action": "Manage Stock Items"}
    }

    @classmethod
    def execute(cls, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        kiki_logger.info(f"[ACTION ENGINE] Executing action resolution for '{question}'")
        clean_q = question.strip().lower()

        target = "voucher"
        for key in cls.ACTION_ROUTES:
            if key in clean_q:
                target = key
                break

        action_info = cls.ACTION_ROUTES[target]
        reply_text = f"To perform this operation ({action_info['action']}), launch the {action_info['title']} workspace."

        return {
            "question": question,
            "intent": "ACTION",
            "final_response": reply_text,
            "reply": reply_text,
            "target_action": action_info["action"],
            "target_route": action_info["route"],
            "navigation_suggestions": [
                {"title": action_info["title"], "route": action_info["route"], "description": action_info["action"]}
            ]
        }
