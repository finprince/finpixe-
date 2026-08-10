"""
KIKI Base Reranker Provider Interface — Phase 17
================================================
SOLID abstract interface for neural cross-encoder candidate chunk reranking.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseReranker(ABC):
    """Abstract Base Class for cross-encoder rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Re-scores and re-ranks candidate chunks using cross-encoder relevance scoring."""
        pass
