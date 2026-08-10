"""
KIKI Base Context Compressor Interface — Phase 17
=================================================
SOLID abstract interface for contextual sentence extraction & token compression prior to LLM synthesis.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseContextCompressor(ABC):
    """Abstract Base Class for contextual evidence sentence compressors."""

    @abstractmethod
    def compress_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        max_sentences_per_chunk: int = 4
    ) -> List[Dict[str, Any]]:
        """Filters non-relevant sentences from retrieved chunks prior to LLM prompt assembly."""
        pass
