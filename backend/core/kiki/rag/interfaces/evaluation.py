"""
KIKI Base Evaluation Engine Interface — Phase 17
================================================
SOLID abstract interface for automated RAG benchmark evaluation suites.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseEvaluationEngine(ABC):
    """Abstract Base Class for automated benchmark metrics engines."""

    @abstractmethod
    def run_benchmark(self, top_k: int = 5, save_baseline: bool = True) -> Dict[str, Any]:
        """Calculates Recall@K, Precision@K, Hit@K, MRR, NDCG, Citation Accuracy, and Latency."""
        pass
