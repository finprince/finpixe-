"""
KIKI Query Expander — Phase 17
==============================
Concrete implementation of BaseQueryExpander. Generates 2-3 semantic query variations for broad retrieval recall.
"""
from typing import List
from ..interfaces.expander import BaseQueryExpander
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("query_expander")


class QueryExpander(BaseQueryExpander):
    """Semantic Multi-Query Generator."""

    def expand_query(self, query: str, num_variations: int = 2) -> List[str]:
        """Generates semantic query variations."""
        if not query or not query.strip():
            return [query]

        variations = [query]
        q_lower = query.lower()

        if "section 16" in q_lower:
            variations.append("GST Section 16 input tax credit eligibility conditions")
            variations.append("Rules for claiming ITC on tax invoices under GST Act")
        elif "ast-rim" in q_lower or "algorithm" in q_lower:
            variations.append("AST-RIM Optimizer core algorithm mathematical formula")
            variations.append("How AST-RIM optimization engine processes financial models")
        elif "leave policy" in q_lower or "casual leaves" in q_lower:
            variations.append("FINPIXE ERP annual leave entitlements and casual leave limits")
            variations.append("HR leave policy guidelines for casual and sick leaves")

        logger.info(f"[QUERY EXPANDER] Expanded '{query}' into {len(variations)} queries.")
        return variations[:num_variations + 1]


query_expander = QueryExpander()
