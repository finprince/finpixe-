from typing import Dict, Any
from ..utils.logger import kiki_logger


class ClarificationEngine:
    """
    Specialized Engine — Clarification Engine
    Triggered when user request is incomplete or ambiguous ('Tell me', 'Show me', 'Explain').
    Asks clarifying question. NEVER returns navigation options.
    """

    @classmethod
    def execute(cls, question: str) -> Dict[str, Any]:
        kiki_logger.info(f"[CLARIFICATION ENGINE] Asking clarification for '{question}'")
        clarification_text = (
            "What would you like to know or investigate today? "
            "Please specify a metric, report, or transaction (for example: 'Today's Sales', 'GST Summary', 'Cash Flow', or 'Top Vendors')."
        )
        return {
            "question": question,
            "intent": "CLARIFICATION",
            "final_response": clarification_text,
            "reply": clarification_text,
            "investigation_steps": [],
            "evidences": [],
            "navigation_suggestions": []
        }
