"""
KIKI Knowledge Retriever Facade — Phase 17
===========================================
Backward-compatible retriever facade delegating to the single entry-point RetrievalFacade.
"""
from typing import Dict, Any, List, Optional
from .facade import retrieval_facade
from .provider import KnowledgeProvider
from .vector_store import chroma_store
from ..evidence.model import Evidence
from ..logging import get_kiki_logger

logger = get_kiki_logger("knowledge_retriever")


class KnowledgeRetriever:
    """Backward-compatible KnowledgeRetriever facade delegating to RetrievalFacade."""

    def __init__(self, provider: KnowledgeProvider = None):
        self.provider = provider or chroma_store

    def retrieve(
        self,
        query: str,
        tenant_id: str = "global",
        top_k: int = 8,
        department: Optional[str] = None,
        min_confidence: float = 0.30,
        provider: Optional[KnowledgeProvider] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves matching candidate chunks via RetrievalFacade."""
        evidence = self.retrieve_evidence(
            query=query,
            tenant_id=tenant_id,
            top_k=top_k,
            department=department,
            min_confidence=min_confidence
        )
        return evidence.payload.get("chunks", [])

    def retrieve_evidence(
        self,
        query: str,
        tenant_id: str = "global",
        top_k: int = 8,
        department: Optional[str] = None,
        min_confidence: float = 0.30
    ) -> Evidence:
        """Retrieves grounded Evidence object via RetrievalFacade."""
        context = {"department": department, "min_confidence": min_confidence}
        return retrieval_facade.retrieve(
            query=query,
            context=context,
            tenant_id=tenant_id
        )


knowledge_retriever = KnowledgeRetriever()

