"""
KIKI Citation Builder Module — Phase 17.4 Hardened
====================================================
Builds user-friendly citations for the chat UI.
Developer diagnostics (chunk IDs, similarity scores) are logged only — never shown in the UI.

Phase 17.4 changes:
  - Fake "Page 1" citations removed for DOCX and other non-PDF documents.
  - page_metadata_available flag controls whether page number is shown.
  - Citation format:
      * PDF with real pages: "• Doc — Section, Page X"
      * DOCX/TXT/etc:        "• Doc — Section"  (no page)
"""
from typing import Dict, Any, List
from ..logging import get_kiki_logger

logger = get_kiki_logger("citation_builder")


class CitationBuilder:
    """Enterprise Citation Builder — clean user-facing sources, full diagnostics in logs."""

    def build_citations(self, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Builds structured citation objects.

        Phase 17.4:
          - Only includes page_number in citation when page_metadata_available=True
            AND page_number is not None.
          - Never fabricates page numbers for DOCX/TXT/MD documents.
        """
        citations = []
        seen_doc_sections: set = set()

        # Log full developer diagnostics
        logger.info(
            f"[CITATION DIAGNOSTICS] Building citations from {len(retrieved_chunks)} chunks:"
        )
        for idx, chunk in enumerate(retrieved_chunks):
            meta = chunk.get("metadata", {})
            logger.info(
                f"  [{idx+1}] Doc: {meta.get('filename')} | "
                f"Page: {meta.get('page_number')} (available={meta.get('page_metadata_available')}) | "
                f"Section: {meta.get('section_heading')} | "
                f"Chunk: {chunk.get('chunk_id')} | "
                f"Conf: {chunk.get('confidence', 0.0)*100:.1f}%"
            )

        # Build deduplicated user-facing citations
        for chunk in retrieved_chunks:
            meta = chunk.get("metadata", {})
            doc_name = meta.get("filename", "Internal Knowledge Document")

            # Phase 17.4: only use page number when genuinely available
            # page_number=-1 is the ChromaDB sentinel for "not available" (ChromaDB rejects None)
            page_meta_ok = meta.get("page_metadata_available", False)
            raw_page = meta.get("page_number")
            # Treat None and -1 both as "page not available"
            page_number = raw_page if (
                page_meta_ok and raw_page is not None and raw_page != -1
            ) else None

            section = meta.get("section_heading", "General Overview")

            dedup_key = f"{doc_name}|{section}"
            if dedup_key in seen_doc_sections:
                continue
            seen_doc_sections.add(dedup_key)

            citations.append({
                "document_name": doc_name,
                "page_number": page_number,           # None when not available
                "page_metadata_available": page_meta_ok,
                "section_heading": section,
                # Internal fields for API serialisation — never displayed in chat UI
                "_chunk_id": chunk.get("chunk_id", ""),
                "_confidence": chunk.get("confidence", 0.0),
                "_text_snippet": chunk.get("text", "")[:200],
            })

        return citations

    def format_citation_markdown(self, citations: List[Dict[str, Any]]) -> str:
        """
        Formats deduplicated citations into a clean, user-friendly 'Sources' section.

        Phase 17.4 format rules:
          • Doc — Section, Page X   (only when page_metadata_available=True & page_number set)
          • Doc — Section            (DOCX / TXT / MD — no page claim)
          • Doc                      (no section either — bare minimum)

        No chunk IDs, confidence %, or internal metadata are ever exposed.
        """
        if not citations:
            return ""

        md_lines = ["\n\n---\n**Sources:**"]
        for cite in citations:
            doc = cite["document_name"].replace(".md", "").replace("_", " ")
            page = cite.get("page_number")
            page_ok = cite.get("page_metadata_available", False)
            section = cite.get("section_heading", "")

            has_real_section = section and section not in ("General Overview", "General")
            has_real_page = page_ok and page is not None

            if has_real_page and has_real_section:
                md_lines.append(f"• {doc} — {section}, Page {page}")
            elif has_real_page:
                md_lines.append(f"• {doc} — Page {page}")
            elif has_real_section:
                md_lines.append(f"• {doc} — {section}")
            else:
                md_lines.append(f"• {doc}")

        return "\n".join(md_lines)


citation_builder = CitationBuilder()
