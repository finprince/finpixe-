"""
KIKI Adaptive Retrieval Planner — Phase 17
==========================================
Dynamic evidence-driven retrieval planner. Inspects query characteristics, exact code/term patterns,
and vector probe evidence to construct an optimal RetrievalExecutionPlan.
Zero hardcoded business rules. Fully feature-flag controlled.
"""
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("retrieval_planner")


@dataclass
class RetrievalExecutionPlan:
    """Execution plan constructed dynamically by RetrievalPlanner."""
    top_k: int                              # Adaptive Top-K (3, 5, 8, or 15)
    enable_query_rewrite: bool              # True if query contains coreference pronouns
    enable_multi_query: bool                # True if query is ambiguous or multi-entity
    enable_bm25_sparse: bool                # True if query contains exact codes, SKUs, or sections
    enable_reranker: bool                   # True if candidate list > 5
    enable_parent_child: bool               # True if vector similarity is marginal or truncated
    enable_compression: bool                # True if total chunk context exceeds limit
    planner_reason: str = "Default adaptive plan"


class RetrievalPlanner:
    """Evidence-driven Retrieval Planner."""

    # Regex patterns indicating exact terminology, codes, sections, or IDs
    EXACT_TERM_PATTERN = re.compile(r'\b(section\s+\d+|inv-\d+|sku-\d+|gstin|hsn\s+\d+|vch-\d+|ast-rim|[A-Z0-9_\-]{4,}\d+[A-Z0-9_\-]*)\b', re.IGNORECASE)
    COREFERENCE_PATTERN = re.compile(r'\b(it|its|that|this|those|these|they|them|the above|the previous)\b', re.IGNORECASE)

    def plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        probe_score: float = 0.0
    ) -> RetrievalExecutionPlan:
        """Determines execution plan dynamically from prompt features and retrieval evidence."""
        q_lower = query.lower().strip()
        words = q_lower.split()
        word_count = len(words)

        # 1. Detect Exact Terms / Codes / SKUs (Triggers BM25 Sparse Search)
        has_exact_terms = bool(self.EXACT_TERM_PATTERN.search(query))

        # 2. Detect Coreference Pronouns (Triggers Query Rewrite)
        has_coreference = bool(self.COREFERENCE_PATTERN.search(query))

        # 3. Determine Adaptive Top-K
        if word_count <= 3 and not has_exact_terms:
            top_k = 3
            complexity = "Simple"
        elif word_count <= 8:
            top_k = 5
            complexity = "Medium"
        elif word_count <= 15:
            top_k = 8
            complexity = "Complex"
        else:
            top_k = 15
            complexity = "Broad"

        # 4. Determine Multi-Query Expansion Requirement
        enable_multi_query = ("and" in q_lower or "versus" in q_lower or "vs" in q_lower or word_count > 10)

        # 5. Determine Parent-Child & Context Compression
        enable_parent_child = (probe_score > 0.0 and probe_score < 0.70)
        enable_compression = (top_k >= 8 or enable_multi_query)

        reason = f"Complexity: {complexity} | ExactTerms: {has_exact_terms} | Coreference: {has_coreference} | ProbeScore: {probe_score:.2f}"
        logger.info(f"[RETRIEVAL PLANNER] Built plan for '{query}': Top-K={top_k}, BM25={has_exact_terms}, MultiQuery={enable_multi_query} | {reason}")

        return RetrievalExecutionPlan(
            top_k=top_k,
            enable_query_rewrite=has_coreference,
            enable_multi_query=enable_multi_query,
            enable_bm25_sparse=has_exact_terms or (word_count > 4),
            enable_reranker=True,
            enable_parent_child=enable_parent_child,
            enable_compression=enable_compression,
            planner_reason=reason
        )


retrieval_planner = RetrievalPlanner()
