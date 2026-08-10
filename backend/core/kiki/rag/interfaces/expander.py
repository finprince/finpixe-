"""
KIKI Base Query Expander Interface — Phase 17
==============================================
SOLID abstract interface for multi-query semantic variations generation.
"""
from abc import ABC, abstractmethod
from typing import List


class BaseQueryExpander(ABC):
    """Abstract Base Class for semantic multi-query expanders."""

    @abstractmethod
    def expand_query(self, query: str, num_variations: int = 2) -> List[str]:
        """Generates semantic query variations for broad retrieval recall."""
        pass
