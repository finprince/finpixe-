"""
Provider Factory & Registry
===========================
Factory registry providing dynamic instantiation of LLM, Embedding, Cache, and Vector providers.
"""
from typing import Dict, Type
from .base_llm import BaseLLMProvider
from .base_cache import BaseCacheProvider
from ..config import kiki_settings

class ProviderFactory:
    @classmethod
    def get_llm_provider(cls, provider_name: str = None) -> BaseLLMProvider:
        name = provider_name or kiki_settings.LLM_PROVIDER
        if name == "ollama":
            from ..runtime.ollama_client import OllamaClient
            return OllamaClient()
        raise ValueError(f"Unknown LLM Provider: '{name}'.")
