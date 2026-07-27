from typing import List, Dict, Any, Optional
from ..models.dto import EvidencePackage
from ..utils.logger import kiki_logger


class EvidenceValidator:
    """
    Component — Evidence Validator
    Verifies that generated responses are strictly supported by executed SQL query results.
    Prevents LLM hallucinations when zero database rows are returned.
    """

    @classmethod
    def validate_and_ground_response(
        cls,
        final_response: str,
        evidences: List[EvidencePackage],
        question: str
    ) -> str:
        """
        Validates final response against evidence packages.
        If no evidence packages exist or all queries returned 0 rows, returns a non-hallucinated fallback.
        """
        if not evidences:
            kiki_logger.warning("[EVIDENCE VALIDATOR] Zero evidence packages gathered. Returning ungrounded fallback.")
            return "I could not determine the requested information from the available database records."

        total_rows = sum(len(e.rows) for e in evidences)
        if total_rows == 0:
            kiki_logger.info("[EVIDENCE VALIDATOR] All queries returned 0 rows. Grounding response.")
            return f"I could not find any transaction records matching '{question}' in the database for the requested period."

        return final_response
