"""
AI Provider Abstraction Layer
=============================
Provides a pluggable interface for AI extraction providers.
Current sole provider: MistralStructuredProvider.
"""
from .base import BaseAIProvider
from .mistral_structured_provider import MistralStructuredProvider

__all__ = ["BaseAIProvider", "MistralStructuredProvider"]
