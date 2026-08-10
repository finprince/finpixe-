"""
KIKI RAG Runtime Lifecycle Manager — Phase 17.1 Zero Hardcode Architecture
==========================================================================
Centralized manager for RAG subsystem initialization, model preloading,
index provenance validation, and lifecycle state management.
Preloads expensive models during application startup to guarantee zero model cold start on user requests.
"""
from typing import Dict, Any, Tuple
from .config_validator import rag_config_validator
from .providers.embedding_provider import bge_embedding_provider
from .providers.reranker_provider import local_reranker_provider
from .providers.chroma_provider import chroma_vector_store_provider
from .pipeline.sparse_engine import bm25_sparse_engine
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("rag_runtime_manager")


class RAGRuntimeManager:
    """Enterprise RAG Runtime Lifecycle & Health Manager."""

    STATE_STARTING = "STARTING"
    STATE_INITIALIZING = "INITIALIZING"
    STATE_LOADING_EMBEDDING = "LOADING_EMBEDDING"
    STATE_LOADING_RERANKER = "LOADING_RERANKER"
    STATE_LOADING_BM25 = "LOADING_BM25"
    STATE_LOADING_VECTOR_STORE = "LOADING_VECTOR_STORE"
    STATE_VALIDATING_INDEX = "VALIDATING_INDEX"
    STATE_VALIDATING_CORPUS_SYNC = "VALIDATING_CORPUS_SYNC"   # Phase 17.4
    STATE_READY = "READY"
    STATE_DEGRADED = "DEGRADED"                               # Phase 17.4
    STATE_MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
    STATE_NOT_READY = "NOT_READY"
    STATE_FAILED = "FAILED"

    def __init__(self):
        self.state = self.STATE_STARTING
        self.last_error = None
        self._corpus_sync_status = "NOT_CHECKED"   # Phase 17.4

    def initialize(self) -> str:
        """
        Runs RAG subsystem startup initialization and model preloading.

        Guarantees zero model downloading/construction during user query processing.
        """
        logger.info("[RAG RUNTIME] Starting startup initialization sequence...")
        self.state = self.STATE_INITIALIZING

        # 1. Validate Configuration
        if not rag_config_validator.validate():
            self.state = self.STATE_NOT_READY
            self.last_error = "Unconfigured required RAG settings"
            logger.error("[RAG RUNTIME] Configuration validation failed. Subsystem NOT_READY.")
            return self.state

        # 2. Preload Embedding Model
        self.state = self.STATE_LOADING_EMBEDDING
        try:
            bge_embedding_provider.preload()
            embed_caps = bge_embedding_provider.capabilities()
            if not embed_caps.dimension or embed_caps.dimension == 0:
                self.state = self.STATE_NOT_READY
                self.last_error = f"Embedding model '{embed_caps.model_id}' failed to initialize dimension"
                logger.error(f"[RAG RUNTIME] {self.last_error}")
                return self.state
        except Exception as e:
            self.state = self.STATE_NOT_READY
            self.last_error = str(e)
            logger.error(f"[RAG RUNTIME] Embedding provider initialization error: {e}")
            return self.state


        # 3. Preload Reranker Model
        self.state = self.STATE_LOADING_RERANKER
        try:
            local_reranker_provider.preload()   # Phase 17.4: explicit preload(), no _get_encoder() call
        except Exception as e:
            logger.warning(f"[RAG RUNTIME] Reranker preload warning: {str(e)}")

        # 4. Preload BM25 Sparse Index
        self.state = self.STATE_LOADING_BM25
        try:
            bm25_sparse_engine._load_index()
        except Exception as e:
            logger.warning(f"[RAG RUNTIME] BM25 sparse index preload warning: {str(e)}")

        # 5. Preload & Validate Vector Store Provenance
        self.state = self.STATE_LOADING_VECTOR_STORE
        try:
            from .providers.chroma_provider import ChromaVectorStoreProvider
            from core.kiki.config import kiki_settings
            global_coll_name = getattr(kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge")
            global_provider = ChromaVectorStoreProvider(collection_name=global_coll_name)

            is_compatible, reason = global_provider.validate_provenance()
            self.state = self.STATE_VALIDATING_INDEX

            if not is_compatible and reason != "EMPTY_COLLECTION":
                self.state = self.STATE_MIGRATION_REQUIRED
                self.last_error = f"Global knowledge provenance mismatch: {reason}"
                logger.warning(
                    f"[RAG RUNTIME] Global collection '{global_coll_name}' provenance mismatch ({reason}). "
                    "State set to MIGRATION_REQUIRED."
                )
                return self.state

            # Also inspect primary user collection for health warnings
            primary_coll_name = getattr(kiki_settings, "PRIMARY_COLLECTION_NAME", "kiki_knowledge_documents")
            user_provider = ChromaVectorStoreProvider(collection_name=primary_coll_name)
            u_ok, u_reason = user_provider.validate_provenance()
            if not u_ok and u_reason != "EMPTY_COLLECTION":
                logger.warning(
                    f"[RAG RUNTIME] User documents collection '{primary_coll_name}' has provenance notice ({u_reason}). "
                    "User documents may require re-ingestion."
                )

        except Exception as e:
            self.state = self.STATE_NOT_READY
            self.last_error = str(e)
            logger.error(f"[RAG RUNTIME] Vector store validation error: {e}")
            return self.state


        # 6. Phase 17.4: Corpus Synchronization Validation
        self.state = self.STATE_VALIDATING_CORPUS_SYNC
        try:
            from .corpus_sync import validate_rag_corpus_sync
            from core.kiki.config import kiki_settings
            global_coll = getattr(kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge")
            # Validate global knowledge BM25 against global Chroma only
            # (user-uploaded kiki_knowledge_documents is a separate corpus)
            sync_result = validate_rag_corpus_sync(
                collection_name=global_coll, include_global=False
            )
            self._corpus_sync_status = sync_result.get("sync_status", "UNKNOWN")
            if self._corpus_sync_status != "SYNCHRONIZED":
                logger.warning(
                    f"[RAG RUNTIME] Global knowledge corpus sync: {self._corpus_sync_status} | "
                    f"dense={sync_result.get('primary_collection_count')} | "
                    f"sparse={sync_result.get('sparse_chunk_count')} | "
                    f"missing_from_sparse={sync_result.get('missing_from_sparse')} — "
                    "System DEGRADED. Run 'python manage.py index_knowledge --rebuild' to fix."
                )
                self.state = self.STATE_DEGRADED
            else:
                self.state = self.STATE_READY
        except Exception as e:
            logger.warning(f"[RAG RUNTIME] Corpus sync validation warning: {e}")
            self._corpus_sync_status = "CHECK_FAILED"
            self.state = self.STATE_READY   # degraded warning but still operational


        logger.info(f"[RAG RUNTIME] Subsystem initialization complete. RAG STATUS = {self.state}.")
        return self.state

    def status(self) -> Dict[str, Any]:
        """Returns comprehensive health & status dictionary — Phase 17.4 expanded."""
        embed_caps = bge_embedding_provider.capabilities()
        chroma_prov = chroma_vector_store_provider.get_provenance()
        bm25_prov = bm25_sparse_engine.get_provenance()
        return {
            "status": self.state,
            "last_error": self.last_error,
            "embedding_provider": {
                "model_id": embed_caps.model_id,
                "dimension": embed_caps.dimension,
                "distance_metric": embed_caps.distance_metric,
                "normalized": embed_caps.normalized,
                "is_loaded": bge_embedding_provider.is_loaded(),
            },
            "reranker_provider": {
                "model": local_reranker_provider.model_name,
                "is_loaded": local_reranker_provider.is_loaded(),
            },
            "vector_provenance": chroma_prov,
            "bm25_provenance": bm25_prov,
            "bm25_chunk_count": bm25_sparse_engine.count(),
            "corpus_sync_status": self._corpus_sync_status,
        }


rag_runtime_manager = RAGRuntimeManager()
