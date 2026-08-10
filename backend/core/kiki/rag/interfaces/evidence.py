"""
KIKI Base Evidence Builder Interface — Phase 17
================================================
SOLID abstract interface for building grounded Evidence objects and citations.
Consolidates evidence object construction and grounded prompt assembly.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from core.kiki.evidence.model import Evidence


class BaseEvidenceBuilder(ABC):
    """Abstract Base Class for structured Evidence package construction."""

    @abstractmethod
    def build_evidence(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        trace_data: Optional[Dict[str, Any]] = None
    ) -> Evidence:
        """Converts retrieved candidate chunks into standardized Evidence DTO."""
        pass

    @abstractmethod
    def build_grounded_prompt(self, query: str, context_string: str) -> str:
        """Builds strict grounded LLM reasoning prompt."""
        pass
