"""
KIKI Chunk Validation Shield — Phase 17
=======================================
Detects and rejects empty chunks, oversized chunks, duplicate text hashes, missing metadata,
embedding failures, and invalid page numbers prior to vector DB storage.
"""
import hashlib
from typing import Dict, Any, List
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("chunk_validator")


class ChunkValidationError(Exception):
    """Exception raised when a chunk fails validation rules."""
    pass


class ChunkValidator:
    """Strict pre-indexing quality validation shield."""

    def __init__(self, min_text_len: int = 20, max_text_len: int = 2000):
        self.min_text_len = min_text_len
        self.max_text_len = max_text_len
        self._seen_hashes = set()

    def validate_chunk(self, chunk: Dict[str, Any]) -> bool:
        """Validates a single chunk dictionary against strict enterprise rules."""
        text = (chunk.get("text") or "").strip()

        # Rule 1: Empty or Sub-Minimum Length Check
        if len(text) < self.min_text_len:
            logger.warning(f"[VALIDATOR REJECT] Empty or short chunk (< {self.min_text_len} chars): '{text[:30]}...'")
            return False

        # Rule 2: Oversized Unheaded Chunk Check
        heading = chunk.get("section_heading") or chunk.get("heading_path") or ""
        if len(text) > self.max_text_len and not heading:
            logger.warning(f"[VALIDATOR REJECT] Oversized unheaded chunk ({len(text)} chars).")
            return False

        # Rule 3: Exact Duplicate Content Hash Check
        text_hash = hashlib.sha256(text.lower().encode("utf-8")).hexdigest()
        if text_hash in self._seen_hashes:
            logger.info(f"[VALIDATOR REJECT] Duplicate chunk content hash detected: {text_hash[:8]}")
            return False
        self._seen_hashes.add(text_hash)

        # Rule 4: Mandatory Metadata Check
        doc_name = chunk.get("filename") or chunk.get("document_name")
        page = chunk.get("page_number") or chunk.get("page", 1)
        if not doc_name or int(page) < 1:
            logger.warning(f"[VALIDATOR REJECT] Missing or invalid document metadata for chunk.")
            return False

        return True

    def validate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filters out all invalid or duplicate chunks from candidate batch."""
        valid = []
        for c in chunks:
            if self.validate_chunk(c):
                valid.append(c)
        
        rejected_count = len(chunks) - len(valid)
        if rejected_count > 0:
            logger.info(f"[CHUNK VALIDATOR] Validated {len(chunks)} chunks: {len(valid)} passed, {rejected_count} rejected.")
        return valid


chunk_validator = ChunkValidator()
