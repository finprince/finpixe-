"""
KIKI Base Embedding Provider Interface — Phase 17
=================================================
SOLID abstract interface for local & remote text embedding models (BGE, Nomic, E5, Ollama, OpenAI).
"""
from abc import ABC, abstractmethod
from typing import List
from .capabilities import ProviderCapabilities


class BaseEmbeddingProvider(ABC):
    """Abstract Base Class for text embedding providers."""

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Returns ProviderCapabilities for dimension, batch size, and distance metric."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates dense embedding vector for a single query text."""
        pass

    @abstractmethod
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generates dense embedding vectors for a batch of document texts."""
        pass
