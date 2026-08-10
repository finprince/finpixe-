"""
KIKI Base Vector Store Provider Interface — Phase 17
====================================================
SOLID abstract interface for vector databases (ChromaDB, Qdrant, Milvus, pgvector, Weaviate, FAISS).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .capabilities import ProviderCapabilities


class BaseVectorStoreProvider(ABC):
    """Abstract Base Class for vector storage providers."""

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Returns ProviderCapabilities for underlying vector database."""
        pass

    @abstractmethod
    def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> int:
        """Stores dense embedding vectors, documents, and metadatas into storage collection."""
        pass

    @abstractmethod
    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Queries collection using dense query vector and returns top_k candidate matches."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Returns total document chunk count in vector store collection."""
        pass
