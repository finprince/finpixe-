"""
KIKI Provider Capabilities Data Model — Phase 17
=================================================
Provider-agnostic capabilities discovery model exposing dimension, distance metrics,
supported batching, normalization, and supported file types.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ProviderCapabilities:
    """Standardized metadata describing vector DB or embedding model capabilities."""
    provider_name: str
    dimension: int                          # e.g., 1024 for BGE-Large, 768 for Nomic
    distance_metric: str                    # "cosine" | "euclidean" | "dot_product"
    max_batch_size: int                     # Maximum safe batch size for embedding/indexing
    supports_filtering: bool                # True if metadata filtering is natively supported
    supports_quantization: bool             # True if scalar/binary quantization is supported
    model_id: str = ""
    normalized: bool = True
    supported_file_types: List[str] = field(default_factory=lambda: [".md", ".pdf", ".txt", ".csv", ".html"])
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

