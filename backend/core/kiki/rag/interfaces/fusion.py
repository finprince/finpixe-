"""
KIKI Base Fusion Engine Interface — Phase 17
============================================
SOLID abstract interface for combining multi-source (Dense + Sparse) search results (e.g. Reciprocal Rank Fusion - RRF).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseFusionEngine(ABC):
    """Abstract Base Class for rank fusion engines."""

    @abstractmethod
    def fuse_results(
        self,
        result_lists: List[List[Dict[str, Any]]],
        top_k: int = 10,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """Merges multiple candidate result lists using Reciprocal Rank Fusion (RRF)."""
        pass
