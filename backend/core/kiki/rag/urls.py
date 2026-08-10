"""
KIKI Developer Knowledge Library URL Router
===========================================
"""
from django.urls import path
from .api_views import RAGStatsView, RAGReindexView, RAGSearchView

urlpatterns = [
    path('stats/', RAGStatsView.as_view(), name='rag_stats'),
    path('reindex/', RAGReindexView.as_view(), name='rag_reindex'),
    path('search/', RAGSearchView.as_view(), name='rag_search'),
]
