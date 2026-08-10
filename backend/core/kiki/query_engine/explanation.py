"""
Query Explanation & Evidence Builder
====================================
Synthesizes tabular query results into natural language explanations and Evidence Package DTOs.
"""
from typing import Dict, Any, List

class QueryExplanationEngine:
    """Transforms raw DB tabular outputs into Evidence Package DTOs."""

    def build_evidence_package(
        self,
        domain_name: str,
        query_results: List[Dict[str, Any]],
        user_message: str
    ) -> Dict[str, Any]:
        """Build structured Evidence Package DTO."""
        row_count = len(query_results)
        
        summary = f"Retrieved {row_count} records for {domain_name} domain."
        if row_count == 0:
            summary = f"No matching records found for {domain_name} domain query."

        return {
            "summary": summary,
            "domain": domain_name,
            "record_count": row_count,
            "sample_records": query_results[:10],
            "confidence": "HIGH" if row_count > 0 else "MEDIUM"
        }

explanation_engine = QueryExplanationEngine()
