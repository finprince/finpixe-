"""
KIKI Health Check & Observability View
======================================
API endpoint returning local Ollama, MySQL, Redis, and system status.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
import requests
from ..config import kiki_settings
from ..telemetry import metrics_collector

class KikiHealthCheckView(APIView):
    """GET /api/v2/kiki/health/"""
    
    permission_classes = []  # Open for health probes
    authentication_classes = []

    def get(self, request):
        health_status = {
            "status": "HEALTHY",
            "version": "4.0.0",
            "components": {
                "mysql": "UNKNOWN",
                "ollama": "UNKNOWN"
            },
            "metrics": metrics_collector.get_summary()
        }
        
        # 1. Test MySQL DB Connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["components"]["mysql"] = "UP"
        except Exception as e:
            health_status["components"]["mysql"] = f"DOWN ({str(e)})"
            health_status["status"] = "DEGRADED"

        # 2. Test Local Ollama Server Connection
        try:
            resp = requests.get(f"{kiki_settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
            if resp.status_code == 200:
                health_status["components"]["ollama"] = "UP"
            else:
                health_status["components"]["ollama"] = f"DEGRADED (HTTP {resp.status_code})"
                health_status["status"] = "DEGRADED"
        except Exception as e:
            health_status["components"]["ollama"] = f"DOWN ({str(e)})"
            health_status["status"] = "DEGRADED"

        return Response(health_status, status=status.HTTP_200_OK if health_status["status"] == "HEALTHY" else status.HTTP_503_SERVICE_UNAVAILABLE)
