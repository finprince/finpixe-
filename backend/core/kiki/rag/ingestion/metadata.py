"""
KIKI Ingestion Metadata Generator — Phase 17.4 Hardened
=========================================================
Generates 16+ rich metadata fields per chunk.

Phase 17.4 changes:
  - "version" now reads from kiki_settings.SCHEMA_VERSION (was hardcoded "2025.1")
  - page / page_number: None when page_metadata_available=False (no fake "1")
  - page_metadata_available propagated into stored metadata
"""
import re
from typing import Dict, Any, List
from core.kiki.config import kiki_settings


class MetadataGenerator:
    """Rich automated metadata tags generator for indexed chunks."""

    def generate_metadata(
        self,
        chunk: Dict[str, Any],
        doc_id: str,
        filename: str,
        category: str = "General",
        tenant_id: str = "global",
        security_level: str = "Public"
    ) -> Dict[str, Any]:
        text = chunk.get("text", "")
        section = chunk.get("section_heading", "General")
        doc_family = filename.rsplit(".", 1)[0].split("_")[0]
        entity_name = filename.rsplit(".", 1)[0].replace("_", " ")

        # Phase 17.4: respect page_metadata_available flag from chunker
        page_meta_available = chunk.get("page_metadata_available", False)
        raw_page = chunk.get("page_number")   # may be None for DOCX/TXT
        page_value = raw_page if (page_meta_available and raw_page is not None) else None

        # Simple keyword extraction from chunk text
        words = re.findall(r'\b[A-Za-z0-9\-_]{4,}\b', text)
        stop_words = {
            "this", "that", "with", "from", "have", "which", "their",
            "there", "about", "would", "these", "other"
        }
        unique_kws = list(dict.fromkeys([w for w in words if w.lower() not in stop_words]))[:10]

        return {
            "document_id": doc_id,
            "document_name": filename,
            "document_family": doc_family,
            "entity": entity_name,
            "category": category,
            "department": category,
            "document_type": filename.split(".")[-1] if "." in filename else "text",
            "language": "en",
            # Phase 17.4: version from settings, never hardcoded
            "version": getattr(kiki_settings, "SCHEMA_VERSION", "2025.1"),
            "security_level": security_level,
            "heading_path": f"{doc_family} > {section}",
            "section": section,
            "section_heading": section,
            # Phase 17.4: None when page metadata is unavailable
            "page": page_value,
            "page_number": page_value,
            "page_metadata_available": page_meta_available,
            "parent_section": doc_family,
            "generated_keywords": ", ".join(unique_kws),
            "semantic_tags": f"{category},{doc_family}",
            "tenant_id": tenant_id,
        }


metadata_generator = MetadataGenerator()
