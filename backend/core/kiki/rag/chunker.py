"""
KIKI Semantic Chunker Module — Phase 17.4 Hardened & Deterministic Chunk IDs
=============================================================================
Splits document text into semantic chunks with headings, section tracking,
deterministic chunk IDs (content hash), and page numbers where genuinely available.

Phase 17.4 & Phase 19 changes:
  - Deterministic chunk IDs using SHA-256 content hashes (prevents duplicate chunk ID generation on re-index)
  - Reads page_metadata_available from doc_data
  - When page_metadata_available=False: sets chunk page_number=None
  - When page_metadata_available=True: carries real page_num from PDF
"""
import re
import hashlib
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
        Splits loaded document pages into semantic chunks with rich structural metadata
        and deterministic SHA-256 chunk IDs.
        """
        filename = doc_data["filename"]
        pages = doc_data.get("pages", [])
        page_metadata_available = doc_data.get("page_metadata_available", False)

        chunks = []
        current_heading = "General Overview"
        chunk_counter = 0

        for p_info in pages:
            page_num = p_info["page"]
            text = p_info["text"]

            lines = text.split("\n")
            paragraph_buffer = []

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#") or (stripped.isupper() and len(stripped) < 60):
                    current_heading = re.sub(r'^[#\s]+', '', stripped)

                paragraph_buffer.append(line)
                combined = "\n".join(paragraph_buffer)

                if len(combined) >= self.chunk_size:
                    chunk_counter += 1
                    chunk_text = combined.strip()
                    hash_input = f"{filename}_{page_num}_{chunk_counter}_{chunk_text}"
                    content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:10]
                    chunk_id = f"chk_{doc_id[:8]}_{content_hash}"

                    chunks.append({
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "filename": filename,
                        "page_number": page_num if page_metadata_available else None,
                        "page_metadata_available": page_metadata_available,
                        "section_heading": current_heading,
                        "text": chunk_text,
                        "tenant_id": tenant_id,
                        "department": department,
                        "security_level": security_level,
                    })
                    paragraph_buffer = paragraph_buffer[-2:] if len(paragraph_buffer) >= 2 else []

            if paragraph_buffer:
                combined = "\n".join(paragraph_buffer).strip()
                if combined:
                    chunk_counter += 1
                    hash_input = f"{filename}_{page_num}_{chunk_counter}_{combined}"
                    content_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:10]
                    chunk_id = f"chk_{doc_id[:8]}_{content_hash}"

                    chunks.append({
                        "chunk_id": chunk_id,
                        "document_id": doc_id,
                        "filename": filename,
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
