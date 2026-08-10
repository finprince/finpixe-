"""
KIKI RAG Subsystem Feature Flags & Configuration — Phase 17
============================================================
Central feature flags and configuration settings for the RAG retrieval subsystem.
Every stage can be independently enabled/disabled or configured for A/B testing and rollback.
"""
import os


class RAGSettings:
    """Central feature flags and configuration settings for Phase 17 RAG."""

    # Stage Feature Flags
    ENABLE_RETRIEVAL_FACADE: bool = os.getenv("KIKI_RAG_FACADE", "true").lower() == "true"
    ENABLE_RETRIEVAL_PLANNER: bool = os.getenv("KIKI_RAG_PLANNER", "true").lower() == "true"
    ENABLE_QUERY_REWRITE: bool = os.getenv("KIKI_RAG_QUERY_REWRITE", "true").lower() == "true"
    ENABLE_MULTI_QUERY: bool = os.getenv("KIKI_RAG_MULTI_QUERY", "true").lower() == "true"
    ENABLE_BM25: bool = os.getenv("KIKI_RAG_BM25", "true").lower() == "true"
    ENABLE_RERANKER: bool = os.getenv("KIKI_RAG_RERANKER", "true").lower() == "true"
    ENABLE_PARENT_CHILD: bool = os.getenv("KIKI_RAG_PARENT_CHILD", "true").lower() == "true"
    ENABLE_CONTEXT_COMPRESSION: bool = os.getenv("KIKI_RAG_COMPRESSION", "true").lower() == "true"
    ENABLE_DYNAMIC_TOPK: bool = os.getenv("KIKI_RAG_DYNAMIC_TOPK", "true").lower() == "true"
    ENABLE_STRICT_VALIDATION: bool = os.getenv("KIKI_RAG_STRICT_VALIDATION", "true").lower() == "true"
    ENABLE_RETRIEVAL_TRACE: bool = os.getenv("KIKI_RAG_TRACE", "true").lower() == "true"

    # Active Providers Configuration
    VECTOR_PROVIDER: str = os.getenv("KIKI_VECTOR_PROVIDER", "chromadb")
    EMBEDDING_PROVIDER: str = os.getenv("KIKI_EMBEDDING_PROVIDER", "bge_local")
    RERANKER_PROVIDER: str = os.getenv("KIKI_RERANKER_PROVIDER", "local_cross_encoder")


rag_settings = RAGSettings()
