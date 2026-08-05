from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ..runtime.investigation_engine import InvestigationEngine
from ..router.intent_router import IntentRouter
from ..navigation.navigation_engine import NavigationEngine
from ..help.help_handler import HelpHandler
from ..query.kpi_resolver import KPIResolver
from ..exceptions.kiki_exceptions import KikiException
from ..utils.logger import kiki_logger


class KikiChatView(APIView):
    """
    Kiki Chat API Endpoint
    Accepts user business questions, routes intents, and executes autonomous investigations.
    Endpoint: POST /api/kiki/chat/ or /api/kiki/investigate/
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        question = (
            request.data.get('question')
            or request.data.get('query')
            or request.data.get('message')
        )

        if not question or not isinstance(question, str) or not question.strip():
            return Response(
                {"error": "Please provide a valid, non-empty 'question' string in the request body."},
                status=status.HTTP_400_BAD_REQUEST
            )

        clean_q = question.strip()
        history = request.data.get('history') or []

        # 1. Intent Router
        intent = IntentRouter.classify_intent(clean_q, history=history)

        kiki_logger.info(
            f"[KIKI TELEMETRY LOG]\n"
            f"Endpoint: /api/kiki/chat/\n"
            f"Intent: {intent}\n"
            f"Question: '{clean_q}'\n"
            f"History Included: {bool(intent == 'FOLLOW_UP')}\n"
            f"History Count: {len(history)}"
        )

        try:
            user = getattr(request, 'user', None)
            context_dict = {
                "user_id": str(getattr(user, 'id', '') or ''),
                "tenant_id": str(getattr(user, 'tenant_id', '') or ''),
                "company_name": getattr(user, 'company_name', None),
                "branch_name": getattr(user, 'branch_name', None),
                "current_page": request.data.get('currentPage') or request.data.get('current_page'),
                "dashboard_filters": request.data.get('dashboardFilters') or request.data.get('dashboard_filters') or {},
                "active_period": request.data.get('activePeriod') or request.data.get('active_period') or "current_month",
                "financial_year": request.data.get('financialYear') or request.data.get('financial_year') or "2025-2026",
                "persona": request.data.get('persona') or request.data.get('userRole') or request.data.get('role'),
                "user_role": getattr(user, 'role', None) if user else None,
            }
            user_permissions = getattr(request, 'permissions', None)

            # Dispatch query to the appropriate specialized engine
            from ..router.dispatcher import IntentDispatcher
            payload = IntentDispatcher.dispatch(
                intent=intent,
                question=clean_q,
                context_dict=context_dict,
                history=history,
                user_permissions=user_permissions
            )

            # Ensure reply field is populated for frontend compatibility
            if isinstance(payload, dict) and "reply" not in payload and "final_response" in payload:
                payload["reply"] = payload["final_response"]

            return Response(payload, status=status.HTTP_200_OK)


        except KikiException as ke:
            kiki_logger.error(f"Kiki Exception handled in view: {ke}")
            return Response(
                {"error": f"Kiki Investigation error: {str(ke)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            kiki_logger.exception(f"Unexpected error in KikiChatView: {e}")
            return Response(
                {"error": f"Internal server error during investigation: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
