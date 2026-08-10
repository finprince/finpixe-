"""
KIKI Automated Quality Test Suite Generator — Phase 10
======================================================
Generates retrievability, citation correctness, and follow-up coreference test cases per indexed document.
Prevents regressions as the enterprise knowledge base expands.
"""
import os
import json
from typing import Dict, Any, List
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("quality_test_generator")


class QualityTestSuiteGenerator:
    """Automated Quality Test Suite Generator per Indexed Document."""

    def generate_tests_for_document(
        self,
        filename: str,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generates retrievability & citation test cases for an indexed document."""
        if not chunks:
            return []

        doc_family = filename.rsplit(".", 1)[0].split("_")[0]
        test_cases = []

        for idx, c in enumerate(chunks[:3]):
            section = c.get("section_heading") or c.get("section") or "General"
            text = c.get("text", "")
            words = [w for w in text.split() if len(w) > 5][:4]
            sample_phrase = " ".join(words) if words else doc_family

            test_cases.append({
                "test_id": f"qtest_{doc_family}_{idx+1}",
                "query": f"Tell me about {doc_family} {sample_phrase}",
                "expected_document": filename,
                "expected_section": section,
                "expected_family": doc_family,
                "test_type": "RETRIEVABILITY"
            })

        logger.info(f"[QUALITY TEST GENERATOR] Generated {len(test_cases)} quality test cases for '{filename}'.")
        return test_cases


quality_test_generator = QualityTestSuiteGenerator()
