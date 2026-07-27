from typing import Dict, List, Any
from ..models.dto import QueryResultData, EvidencePackage


class EvidenceBuilder:
    """
    Component 6 — Evidence Builder
    Passively packages raw SQL query results and execution metadata into an EvidencePackage DTO.
    Strictly performs NO reasoning, NO percentage calculations, and NO business conclusions.
    """

    @classmethod
    def build_evidence(
        cls,
        step_number: int,
        step_description: str,
        query: str,
        query_result: QueryResultData
    ) -> EvidencePackage:
        """
        Packages QueryResultData into an immutable EvidencePackage DTO.
        """
        metadata = {
            "row_count": query_result.row_count,
            "execution_time_ms": query_result.execution_time_ms,
            "status": query_result.status,
            "timestamp": query_result.timestamp
        }

        return EvidencePackage(
            step_number=step_number,
            step_description=step_description,
            query=query,
            rows=query_result.rows,
            metadata=metadata
        )
