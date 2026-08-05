import re
from typing import List, Dict, Any, Optional
from ..utils.logger import kiki_logger


class ConversationMemory:
    """
    Component — Conversation Memory (Kiki 2.0)
    Tracks multi-turn conversational history and accumulates entity constraints across follow-ups.

    Example Flow:
    1. "Show purchases"          => entity="purchases"
    2. "Only July"               => entity="purchases", period="July"
    3. "Only pending"            => entity="purchases", period="July", status="pending"
    4. "Sort by vendor"          => entity="purchases", period="July", status="pending", sort="vendor"
    5. "Export report"           => action="export", entity="purchases", period="July", status="pending"
    """

    MONTH_REGEX = r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b"

    @classmethod
    def resolve_conversation(
        cls,
        current_question: str,
        history: Optional[List[Dict[str, Any]]] = None,
        existing_constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        constraints = dict(existing_constraints or {})
        clean_q = current_question.strip().lower()

        # 1. Inspect History to extract previous context if present
        history_list = history or []
        if history_list and not constraints.get("entity"):
            for msg in reversed(history_list):
                txt = (msg.get("text") or msg.get("content") or "").lower()
                if "purchase" in txt:
                    constraints["entity"] = "purchases"
                    break
                elif "sale" in txt or "revenue" in txt:
                    constraints["entity"] = "sales"
                    break
                elif "gst" in txt or "tax" in txt:
                    constraints["entity"] = "gst"
                    break
                elif "vendor" in txt:
                    constraints["entity"] = "vendors"
                    break
                elif "customer" in txt:
                    constraints["entity"] = "customers"
                    break

        # 2. Extract new constraints from current turn
        # Entity extraction
        if "purchase" in clean_q:
            constraints["entity"] = "purchases"
        elif "sale" in clean_q:
            constraints["entity"] = "sales"
        elif "gst" in clean_q:
            constraints["entity"] = "gst"

        # Month / Period extraction
        month_match = re.search(cls.MONTH_REGEX, clean_q)
        if month_match:
            constraints["period"] = month_match.group(1).title()

        # Status extraction
        if "pending" in clean_q or "unpaid" in clean_q or "outstanding" in clean_q:
            constraints["status"] = "pending"
        elif "posted" in clean_q or "paid" in clean_q or "approved" in clean_q:
            constraints["status"] = "posted"

        # Action / Sorting extraction
        if "export" in clean_q or "download" in clean_q:
            constraints["action"] = "export"
        if "sort by vendor" in clean_q or "by vendor" in clean_q:
            constraints["sort_by"] = "vendor"
        elif "sort by date" in clean_q:
            constraints["sort_by"] = "date"
        elif "sort by amount" in clean_q:
            constraints["sort_by"] = "amount"

        kiki_logger.info(
            f"[CONVERSATION MEMORY] Resolved constraints for '{current_question}': {constraints}"
        )
        return constraints
