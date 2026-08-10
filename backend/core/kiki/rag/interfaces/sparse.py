"""
KIKI Base Sparse Retriever Interface — Phase 17
================================================
SOLID abstract interface for lexical/sparse search engines (BM25Okapi, Tantivy, Lucene).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseSparseRetriever(ABC):
    """Abstract Base Class for sparse lexical search engines."""

    @abstractmethod
    def index_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Indexes text chunks into sparse BM25 inverted index."""
        pass

    @abstractmethod
    def search_sparse(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Executes BM25 sparse keyword search and returns top_k matching chunks."""
        pass
