"""
KIKI Semantic Chunker Module — Phase 17.4 Hardened
====================================================
Splits document text into semantic chunks with headings, section tracking,
and page numbers where genuinely available.

Phase 17.4 changes:
  - Reads page_metadata_available from doc_data
  - When page_metadata_available=False: sets chunk page_number=None
    (DOCX, TXT, MD, CSV, HTML cannot provide real physical page numbers)
  - When page_metadata_available=True: carries real page_num from PDF
  - Propagates page_metadata_available flag into every chunk metadata dict
"""
import re
import uuid
from typing import Dict, Any, List


class SemanticChunker:
    """Enterprise Semantic Chunker for RAG document processing."""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(
        self,
        doc_data: Dict[str, Any],
        doc_id: str,
        tenant_id: str,
        department: str = "General",
        security_level: str = "Internal"
    ) -> List[Dict[str, Any]]:
        """
        Splits loaded document pages into semantic chunks with rich structural metadata.

        Phase 17.4: page_number is None when the loader cannot determine physical pages
        (DOCX, TXT, MD, CSV, HTML). It is only set for PDFs where pypdf provides real pages.
        """
        filename = doc_data["filename"]
        pages = doc_data.get("pages", [])
        # Phase 17.4: propagate availability flag from loader output
        page_metadata_available = doc_data.get("page_metadata_available", False)

        chunks = []
        current_heading = "General Overview"

        for p_info in pages:
            page_num = p_info["page"]
            text = p_info["text"]

            # Detect Markdown / Document Headings (# Heading or SECTION)
            lines = text.split("\n")
            paragraph_buffer = []

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#") or (stripped.isupper() and len(stripped) < 60):
                    current_heading = re.sub(r'^[#\s]+', '', stripped)

                paragraph_buffer.append(line)
                combined = "\n".join(paragraph_buffer)

                if len(combined) >= self.chunk_size:
                    chunk_id = f"chk_{doc_id[:8]}_{uuid.uuid4().hex[:8]}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "filename": filename,
                        # Phase 17.4: None when not physically available
                        "page_number": page_num if page_metadata_available else None,
                        "page_metadata_available": page_metadata_available,
                        "section_heading": current_heading,
                        "text": combined.strip(),
                        "tenant_id": tenant_id,
                        "department": department,
                        "security_level": security_level,
                    })
                    # Maintain overlap window
                    paragraph_buffer = paragraph_buffer[-2:] if len(paragraph_buffer) >= 2 else []

            if paragraph_buffer:
                combined = "\n".join(paragraph_buffer).strip()
                if combined:
                    chunk_id = f"chk_{doc_id[:8]}_{uuid.uuid4().hex[:8]}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "filename": filename,
                        # Phase 17.4: None when not physically available
                        "page_number": page_num if page_metadata_available else None,
                        "page_metadata_available": page_metadata_available,
                        "section_heading": current_heading,
                        "text": combined,
                        "tenant_id": tenant_id,
                        "department": department,
                        "security_level": security_level,
                    })

        return chunks


semantic_chunker = SemanticChunker()
