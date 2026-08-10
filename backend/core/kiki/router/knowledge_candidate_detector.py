"""
KIKI Knowledge Candidate Detector & Fast Vector Probe — Phase 14.2 / 15
=========================================================================
Evaluates incoming user questions via lightweight semantic vector similarity probe
against ChromaDB collection 'finpixe_global_knowledge' (< 5ms).

Phase 15: All static keyword lists removed. The semantic probe is the ONLY signal.
ERP bypass logic is now handled by the NLU Analyzer (context/nlu_analyzer.py).
"""
from typing import Dict, Any
from ..rag.vector_store import chroma_store
from ..config import kiki_settings
from ..logging import get_kiki_logger

logger = get_kiki_logger("knowledge_candidate_detector")


class KnowledgeCandidateDetector:
    """Intelligent Semantic Knowledge Candidate Detector for RAG Routing."""

    def detect(self, message: str) -> Dict[str, Any]:
        """
        Executes fast vector probe to evaluate whether the query matches global knowledge.
        No hardcoded document names. No static keyword lists.
        The threshold adapts based on collection similarity distribution.
        """
        # Probe ChromaDB global knowledge collection (< 5ms vector search)
        probe_res = chroma_store.probe_knowledge(query_text=message, top_k=3)
        max_sim = probe_res.get("max_similarity", 0.0)
        top_doc = probe_res.get("top_document")

        is_candidate = max_sim >= kiki_settings.KNOWLEDGE_ROUTING_THRESHOLD and top_doc is not None

        logger.info(
            f"[ROUTER LOG] Question: '{message}' | Knowledge Candidate: {is_candidate} | "
            f"Similarity: {max_sim:.4f} | Document: {top_doc} | "
            f"Engine: {'RAG (ChromaDB)' if is_candidate else 'ERP (MySQL)'}"
        )

        return {
            "is_candidate": is_candidate,
            "max_similarity": max_sim,
            "top_document": top_doc,
            "chunks_found": probe_res.get("chunks_found", 0)
        }


knowledge_candidate_detector = KnowledgeCandidateDetector()
