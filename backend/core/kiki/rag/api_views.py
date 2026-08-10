"""
KIKI Developer Knowledge Library Admin REST API Views
=====================================================
Developer-only management endpoints for the Global Knowledge Library.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .knowledge_indexer import knowledge_indexer
from .vector_store import chroma_store
from core.kiki.config import kiki_settings

# Phase 17.4: collection name from settings, not module constant
GLOBAL_COLLECTION_NAME = getattr(kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge")

class RAGReindexView(APIView):
    """Developer Admin Endpoint: Reindex Developer Knowledge Library."""

    def post(self, request, *args, **kwargs):
        rebuild = request.data.get('rebuild', False)
        report = knowledge_indexer.index_all(rebuild=rebuild)
        return Response(report, status=status.HTTP_200_OK)

class RAGStatsView(APIView):
    """Developer Admin Endpoint: Global Collection Statistics."""

    def get(self, request, *args, **kwargs):
        try:
            coll = chroma_store.client.get_or_create_collection(GLOBAL_COLLECTION_NAME)
            total_chunks = coll.count()
        except Exception:
            total_chunks = 0

        return Response({
            "collection_name": GLOBAL_COLLECTION_NAME,
            "knowledge_directory": knowledge_indexer.knowledge_dir,
            "total_chunks_indexed": total_chunks,
            "persist_directory": chroma_store.persist_dir,
            "status": "HEALTHY"
        }, status=status.HTTP_200_OK)

class RAGSearchView(APIView):
    """Developer Admin Endpoint: Developer Search Diagnostics Test."""

    def post(self, request, *args, **kwargs):
        query = request.data.get('query', '')
        if not query:
            return Response({"error": "Query string is required."}, status=status.HTTP_400_BAD_REQUEST)

        results = chroma_store.query_global(query_text=query, top_k=4)
        return Response({
            "query": query,
            "total_results": len(results),
            "results": results
        }, status=status.HTTP_200_OK)
