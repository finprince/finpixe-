"""
Base Embedding Provider Interface
=================================
Abstract interface for text embedding models.
"""
from abc import ABC, abstractmethod
from typing import List

class BaseEmbeddingProvider(ABC):
    
    @abstractmethod
    def embed_texts(self, texts: List[str], model: str = None) -> List[List[float]]:
        """Generate dense vector embeddings for a list of text strings."""
        pass

    @abstractmethod
    def embed_query(self, query: str, model: str = None) -> List[float]:
        """Generate dense vector embedding for a single search query string."""
        pass
