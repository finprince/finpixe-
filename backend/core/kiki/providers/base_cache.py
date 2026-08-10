"""
Base Cache Provider Interface
=============================
Abstract interface for distributed key-value cache operations.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional

class BaseCacheProvider(ABC):

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value for key."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store key-value pair in cache with optional TTL seconds."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern (e.g. 'kiki:tenant:123:*')."""
        pass
