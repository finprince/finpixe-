from typing import Dict, Any, Optional, List
from ..cognitive.cognitive_layer import KikiCognitiveLayer
from ..utils.logger import kiki_logger


class IntentDispatcher:
    """
    Component — Dedicated Intent Dispatcher
    Delegates all query processing to the Kiki Cognitive Layer (AI Brain).
    The Cognitive Layer acts as the single decision maker, orchestrating worker engines,
    performing business reasoning, evaluating confidence, and composing responses.
    """

    @classmethod
    def dispatch(
        cls,
        intent: str,
        question: str,
        context_dict: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, str]]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        kiki_logger.info(f"[INTENT DISPATCHER] Routing query '{question}' (initial intent: '{intent}') to KikiCognitiveLayer")
        return KikiCognitiveLayer.process_request(
            question=question,
            context_dict=context_dict,
            history=history,
            user_permissions=user_permissions
        )

