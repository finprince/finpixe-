"""
KIKI Chat & Conversation API View
=================================
Primary REST & SSE streaming endpoint passing incoming prompts through the AI Kernel.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..kernel import ai_kernel
from ..logging import get_kiki_logger

logger = get_kiki_logger("chat_api")

class KikiChatView(APIView):
    """POST /api/v2/kiki/chat/"""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        message = request.data.get("message", "").strip()
        if not message:
            return Response({"error": "Message parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        context_data = request.data.get("context_data", {})
        
        try:
            result = ai_kernel.process_request(
                message=message,
                request_user=request.user,
                context_data=context_data
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error processing AI Kernel chat request: {str(e)}")
            return Response({
                "error": "Failed to process AI request.",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
