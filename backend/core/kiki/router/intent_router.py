import re
from typing import List, Dict, Any, Optional
from ..utils.logger import kiki_logger


class IntentRouter:
    """
    Component — Intent Router
    Classifies incoming user questions into explicit ERP intent categories:
    GREETING, SMALL_TALK, HELP, CLARIFICATION, NAVIGATION, KPI_QUERY, FOLLOW_UP, BUSINESS_INVESTIGATION.

    Guarantees:
    - NAVIGATION is ONLY triggered by explicit navigation action verbs ('open', 'go to', 'navigate', 'launch', etc.)
      or contextual follow-ups ('open it', 'go there').
    - Information queries ('Today's Sales', 'GST Summary', 'Cash Flow', 'Top Vendors') NEVER trigger Navigation directly.
    - Vague requests ('tell me', 'show me', 'explain') trigger CLARIFICATION.
    - Only BUSINESS_INVESTIGATION and FOLLOW_UP trigger the InvestigationEngine database pipeline.
    """

    GREETING_REGEX = r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b"
    SMALL_TALK_REGEX = r"^(thanks|thank you|bye|goodbye|how are you|cool|great|awesome)\b"
    HELP_REGEX = r"\b(how (do|to|can) i|help|guide|how do)\b"

    # Explicit Navigation Verbs/Phrases — MUST contain one of these verbs to trigger NAVIGATION
    NAVIGATION_VERBS_REGEX = r"\b(open|go to|goto|navigate|navigate to|take me to|bring me to|launch|show page|show the page|switch to)\b"

    # Contextual Navigation Triggers (when history exists)
    CONTEXTUAL_NAV_REGEX = r"^(open it|go there|open page|open that|take me there|bring me there|go to it)$"

    # Action / Operations Keywords (Rule 7)
    ACTION_REGEX = r"\b(create|approve|generate|delete)\s+(vendor|customer|voucher|invoice|ledger|stock|item)\b"

    # KPI Keywords
    KPI_REGEX = r"\b(total sales|sales total|today's sales|todays sales|sales summary|total purchase|purchases summary|receivables|payables|cash balance|bank balance|cash flow|profit|revenue|gst payable|outstanding receivables)\b"

    FOLLOW_UP_PREFIXES = ["what about", "then what", "compare with", "and for", "how about", "what if"]

    # Vague queries requiring clarification
    VAGUE_REGEX = r"^(tell me|show me|explain|display|check|help me|what|show)$"

    @classmethod
    def classify_intent(cls, question: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        if not question or not isinstance(question, str):
            return "UNKNOWN"

        clean_q = question.strip().lower()
        has_history = bool(history and len(history) > 0)
        word_count = len(clean_q.split())

        # 1. Check Contextual Follow-Up / Contextual Navigation (when history is present)
        if has_history:
            # Check contextual navigation (e.g. "open it", "go there")
            if re.search(cls.CONTEXTUAL_NAV_REGEX, clean_q):
                kiki_logger.info(f"[INTENT ROUTER] Classified as NAVIGATION (contextual follow-up: '{clean_q}')")
                return "NAVIGATION"

            # Check follow-up questions
            for prefix in cls.FOLLOW_UP_PREFIXES:
                if clean_q.startswith(prefix):
                    kiki_logger.info(f"[INTENT ROUTER] Classified as FOLLOW_UP ('{clean_q}')")
                    return "FOLLOW_UP"

        # 2. Check Greetings
        if len(clean_q) < 20 and re.search(cls.GREETING_REGEX, clean_q):
            kiki_logger.info(f"[INTENT ROUTER] Classified as GREETING ('{clean_q}')")
            return "GREETING"

        # 3. Check Small Talk
        if len(clean_q) < 25 and re.search(cls.SMALL_TALK_REGEX, clean_q):
            kiki_logger.info(f"[INTENT ROUTER] Classified as SMALL_TALK ('{clean_q}')")
            return "SMALL_TALK"

        # 4. Check Vague Incomplete Requests requiring CLARIFICATION
        if word_count <= 3 and re.search(cls.VAGUE_REGEX, clean_q):
            kiki_logger.info(f"[INTENT ROUTER] Classified as CLARIFICATION ('{clean_q}')")
            return "CLARIFICATION"

        # 5. Check Explicit Navigation Verbs ONLY
        # Navigation Engine should ONLY execute when Intent == NAVIGATION and explicit verb is present
        if re.search(cls.NAVIGATION_VERBS_REGEX, clean_q):
            kiki_logger.info(f"[INTENT ROUTER] Classified as NAVIGATION ('{clean_q}')")
            return "NAVIGATION"

        # 6. Check Action / Operations Intent (Rule 7)
        if re.search(cls.ACTION_REGEX, clean_q):
            kiki_logger.info(f"[INTENT ROUTER] Classified as ACTION ('{clean_q}')")
            return "ACTION"

        # 7. Check Help Intent
        if re.search(cls.HELP_REGEX, clean_q):
            kiki_logger.info(f"[INTENT ROUTER] Classified as HELP ('{clean_q}')")
            return "HELP"

        # 8. Check KPI Queries
        if re.search(cls.KPI_REGEX, clean_q) and not any(w in clean_q for w in ["why", "decrease", "increase", "compare"]):
            kiki_logger.info(f"[INTENT ROUTER] Classified as KPI_QUERY ('{clean_q}')")
            return "KPI_QUERY"

        # 9. Default Business Investigation for all data / reporting questions
        kiki_logger.info(f"[INTENT ROUTER] Classified as BUSINESS_INVESTIGATION ('{clean_q}')")
        return "BUSINESS_INVESTIGATION"


