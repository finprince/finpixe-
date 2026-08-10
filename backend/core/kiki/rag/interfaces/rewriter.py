"""
KIKI Base Query Rewriter Interface — Phase 17
==============================================
SOLID abstract interface for coreference pronoun resolution and follow-up normalization.
Strict Rule: MUST NOT perform domain routing, intent classification, or reasoning.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseQueryRewriter(ABC):
    """Abstract Base Class for pure coreference question rewriters."""

    @abstractmethod
    def rewrite(
        self,
        query: str,
        history_summary: str = "",
        current_entity: Optional[str] = None
    ) -> str:
        """Resolves pronouns and omitted entities into a self-contained rewritten query string."""
        pass
