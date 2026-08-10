"""
KIKI API V2 URL Configuration
=============================
"""
from django.urls import path, include
from .views_health import KikiHealthCheckView
from .views_chat import KikiChatView

urlpatterns = [
    path('health/', KikiHealthCheckView.as_view(), name='kiki-health'),
    path('chat/', KikiChatView.as_view(), name='kiki-chat'),
    path('rag/', include('core.kiki.rag.urls')),
]
