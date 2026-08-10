"""
KIKI Retrieval Facade — Phase 17
================================
Single entry-point API coordinator for external consumers (AI Orchestrator & Knowledge Capability).
Coordinates request entry, delegates planning to RetrievalPlanner, and delegates execution to ExecutionPipeline.
The Orchestrator knows ONLY one facade interface.
"""
from typing import Dict, Any, Optional
from .settings import rag_settings
from .planner import retrieval_planner
from .execution_pipeline import execution_pipeline
from core.kiki.evidence.model import Evidence
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("retrieval_facade")


class RetrievalFacade:
    """Enterprise Retrieval Facade Coordinator."""

    def retrieve(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        tenant_id: str = "global"
    ) -> Evidence:
        """
        Single entry point for all retrieval operations.
        1. Evaluates fast vector probe evidence.
        2. Delegates planning to RetrievalPlanner.
        3. Delegates stage execution to ExecutionPipeline.
        """
        logger.info(f"[RETRIEVAL FACADE] Received query: '{query}' | Tenant: '{tenant_id}'")

        if not query or not query.strip():
            return Evidence(
                type="KNOWLEDGE",
                source="finpixe_global_knowledge",
                payload={"chunks": [], "context_string": ""},
                summary="Empty query provided.",
                confidence=0.0,
                citations=[]
            )

        # 1. Fast vector probe score estimate
        from .providers.chroma_provider import chroma_vector_store_provider
        from .providers.embedding_provider import bge_embedding_provider

        try:
            q_vec = bge_embedding_provider.embed_text(query)
            probe_results = chroma_vector_store_provider.query_vectors(q_vec, top_k=1)
            probe_score = probe_results[0].get("confidence", 0.0) if probe_results else 0.0
        except Exception:
            probe_score = 0.0

        # 2. Delegate planning to RetrievalPlanner
        plan = retrieval_planner.plan(
            query=query,
            context=context,
            probe_score=probe_score
        )

        # 3. Delegate execution to ExecutionPipeline
        evidence_obj = execution_pipeline.execute_plan(
            query=query,
            plan=plan,
            context=context,
            tenant_id=tenant_id
        )

        return evidence_obj


retrieval_facade = RetrievalFacade()
