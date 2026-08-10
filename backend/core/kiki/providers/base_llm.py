"""
Base LLM Provider Interface
===========================
Abstract interface for LLM operations.
"""
from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, List, Optional

class BaseLLMProvider(ABC):
    
    @abstractmethod
    def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stop_sequences: Optional[List[str]] = None
    ) -> str:
        """Generate a complete text completion."""
        pass

    @abstractmethod
    def generate_json(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a structured JSON completion."""
        pass

    @abstractmethod
    def stream(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Generator[str, None, None]:
        """Stream completion tokens as a generator."""
        pass
