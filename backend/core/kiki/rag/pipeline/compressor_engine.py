"""
KIKI Contextual Sentence Compressor — Phase 17.1 Zero Hardcode Architecture
=============================================================================
Concrete implementation of BaseContextCompressor.
Dynamic Token Budget Aware Compression: Bypasses sentence stripping when total context
fits within safe_evidence_budget, preserving complementary multi-chunk factual context.
"""
from typing import Dict, Any, List
from ..interfaces.compressor import BaseContextCompressor
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("context_compressor")


class ContextCompressorEngine(BaseContextCompressor):
    """Token Budget Aware Contextual Compressor Engine."""

    def compress_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        max_sentences_per_chunk: int = 6
    ) -> List[Dict[str, Any]]:
        """Compresses retrieved chunks only when context budget is exceeded."""
        if not chunks:
            return []

        max_model_context_tokens = getattr(kiki_settings, "RAG_MAX_CONTEXT_TOKENS", 4096)
        response_reserve_tokens = getattr(kiki_settings, "RAG_RESPONSE_RESERVE_TOKENS", 512)
        safe_evidence_budget = max(1000, max_model_context_tokens - response_reserve_tokens - 1000)

        # Estimate total word token budget
        total_evidence_tokens = sum(len(c.get("text", "").split()) * 1.3 for c in chunks)

        if total_evidence_tokens <= safe_evidence_budget:
            logger.info(
                f"[CONTEXT COMPRESSOR] Total evidence tokens ({total_evidence_tokens:.0f}) "
                f"<= safe budget ({safe_evidence_budget:.0f}). Bypassing sentence compression."
            )
            return chunks

        logger.info(f"[CONTEXT COMPRESSOR] Evidence ({total_evidence_tokens:.0f} tokens) exceeds budget ({safe_evidence_budget:.0f}). Compressing...")
        query_terms = set(query.lower().split())
        compressed_chunks = []

        for c in chunks:
            text = c.get("text", "")
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            if len(sentences) <= max_sentences_per_chunk:
                compressed_chunks.append(c)
                continue

            matching = []
            for s in sentences:
                s_words = set(s.lower().split())
                score = len(query_terms & s_words)
                matching.append((score, s))

            matching.sort(key=lambda x: x[0], reverse=True)
            selected_sentences = [m[1] for m in matching[:max_sentences_per_chunk]]
            c_copy = dict(c)
            c_copy["text"] = ". ".join(selected_sentences) + "."
            compressed_chunks.append(c_copy)

        return compressed_chunks


context_compressor_engine = ContextCompressorEngine()
