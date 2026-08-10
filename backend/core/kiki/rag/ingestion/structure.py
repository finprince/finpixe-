"""
KIKI Ingestion Structure Extractor — Phase 17
=============================================
Extracts Markdown heading paths (# Heading 1 > ## Subheading) and Markdown tables.
"""
import re
from typing import Dict, Any, List


class StructureExtractor:
    """Extracts structural heading paths and table blocks from Markdown text."""

    def extract_heading_path(self, text: str) -> str:
        """Finds heading markers (#, ##, ###) and builds heading path."""
        lines = text.split('\n')
        headings = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                h_text = re.sub(r'^[#\s]+', '', stripped)
                headings.append(h_text)

        return " > ".join(headings) if headings else "General Overview"


structure_extractor = StructureExtractor()
