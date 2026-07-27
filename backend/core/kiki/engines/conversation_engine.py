from typing import Dict, Any
from ..utils.logger import kiki_logger


class ConversationEngine:
    """
    Specialized Engine — Conversation Engine
    Handles GREETING and SMALL_TALK user messages.
    """

    @classmethod
    def execute(cls, question: str, intent: str = "GREETING") -> Dict[str, Any]:
        kiki_logger.info(f"[CONVERSATION ENGINE] Handling '{intent}' for '{question}'")
        text = (
            "Hello! I am Kiki, your AI ERP Copilot. How can I help you analyze your financial data today?"
            if intent == "GREETING" else
            "You're welcome! Let me know if you need any further financial analysis or reporting assistance."
        )
        return {
            "question": question,
            "intent": intent,
            "final_response": text,
            "reply": text,
            "investigation_steps": [],
            "evidences": []
        }
