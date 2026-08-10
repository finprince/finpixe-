"""
KIKI KnowledgeProvider Abstract Interface — Phase 15 V3
=========================================================
Provider-agnostic abstraction for unstructured knowledge vector databases.
Decouples the Core Planner and Knowledge Capability from specific vector DB implementations
(ChromaDB, Qdrant, Milvus, Weaviate, etc.).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class KnowledgeProvider(ABC):
    """Abstract Vector Storage & Similarity Probe Provider Interface."""

    @abstractmethod
    def probe_vector(self, query_text: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Executes fast vector similarity probe (< 5ms).
        Returns dict containing max_similarity, top_document, top_family, and is_candidate.
        """
        pass

    @abstractmethod
    def query_global(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Queries global knowledge collection and returns raw metadata-enriched candidate chunks.
        """
        pass

    @abstractmethod
    def query_tenant(
        self,
        query_text: str,
        tenant_id: str,
        top_k: int = 10,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Queries multi-tenant isolated knowledge collection.
        """
        pass
