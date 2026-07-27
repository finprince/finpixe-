from typing import Dict, Any, Optional, List
from ..navigation.navigation_engine import NavigationEngine
from ..runtime.investigation_engine import InvestigationEngine
from ..engines.kpi_engine import KPIEngine
from ..engines.action_engine import ActionEngine
from ..help.help_handler import HelpHandler
from ..engines.workflow_engine import WorkflowEngine
from ..engines.clarification_engine import ClarificationEngine
from ..engines.conversation_engine import ConversationEngine
from ..utils.logger import kiki_logger


class IntentDispatcher:
    """
    Component — Dedicated Intent Dispatcher
    Responsibilities:
    1. Receive classified intent and question
    2. Validate confidence
    3. Route request to the appropriate specialized engine
    4. Guarantee that ONLY ONE engine executes per request. No engine calls another engine.
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
        kiki_logger.info(f"[INTENT DISPATCHER] Dispatching intent '{intent}' for query '{question}'")

        if intent == "NAVIGATION":
            return NavigationEngine.navigate(question, user_permissions=user_permissions)

        elif intent in ["BUSINESS_INVESTIGATION", "FOLLOW_UP"]:
            investigation_engine = InvestigationEngine()
            result = investigation_engine.run_investigation(
                question=question,
                context=context_dict
            )
            res_dict = result.to_dict()
            res_dict["reply"] = result.final_response
            res_dict["intent"] = intent
            # Optional navigation suggestion
            res_dict["navigation_suggestions"] = [
                {"title": "Open Dashboard", "route": "/dashboard", "description": "View live workspace metrics"}
            ]
            return res_dict


        elif intent == "KPI_QUERY":
            return KPIEngine.execute(question)

        elif intent == "ACTION":
            return ActionEngine.execute(question, context=context_dict)

        elif intent == "HELP":
            return HelpHandler.handle_help(question)

        elif intent == "WORKFLOW":
            return WorkflowEngine.execute(question)

        elif intent in ["GREETING", "SMALL_TALK"]:
            return ConversationEngine.execute(question, intent)

        elif intent == "CLARIFICATION":
            return ClarificationEngine.execute(question)

        else:
            kiki_logger.warning(f"[INTENT DISPATCHER] Unknown intent '{intent}'. Falling back to ClarificationEngine.")
            return ClarificationEngine.execute(question)
