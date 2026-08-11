"""
KIKI BGE Local GPU Embedding Provider — Phase 19 Hardened
===========================================================
Concrete implementation of BaseEmbeddingProvider with local offline model execution
and NVIDIA CUDA GPU acceleration.

Phase 19 CUDA & Offline Enforcements:
  - Loads BGE-large-v1.5 from local path (backend/models/rag/embedding/bge-large-en-v1.5/) with local_files_only=True.
  - Enforces CUDA execution (cuda:0).
  - Fail-fast with GPU_REQUIRED_UNAVAILABLE if CUDA is required but unavailable.
  - Exposes actual runtime metadata (dimension, distance_metric, normalized, device, loaded).
"""
import os
import torch
from pathlib import Path
from typing import List
from ..interfaces.embedding import BaseEmbeddingProvider
from ..interfaces.capabilities import ProviderCapabilities
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("bge_embedding_provider")


class BGEEmbeddingProvider(BaseEmbeddingProvider):
    """BGE Dense Vector Embedding Provider with CUDA Acceleration & Zero-Network Offline Mode."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or getattr(kiki_settings, "EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
        self.distance_metric = getattr(kiki_settings, "EMBEDDING_DISTANCE_METRIC", "cosine")
        self.normalized = getattr(kiki_settings, "EMBEDDING_NORMALIZED", True)
        self.target_device = getattr(kiki_settings, "EMBEDDING_DEVICE", "cuda")
        self._encoder = None
        self._dim = None
        self._loaded = False
        self._device = None

    def is_loaded(self) -> bool:
        return self._loaded

    def preload(self) -> bool:
        """
        Eagerly load the embedding model onto CUDA during application startup.
        Loads strictly from local model directory with zero network calls.
        """
        if self._loaded:
            logger.info(
                f"[EMBEDDING PROVIDER] Model '{self.model_name}' already loaded "
                f"on {self._device} (dim={self._dim}). Skipping preload."
            )
            return True

        # Check CUDA requirement
        cuda_ok = torch.cuda.is_available()
        if self.target_device == "cuda" and not cuda_ok:
            if getattr(kiki_settings, "RAG_REQUIRE_GPU", True) and not getattr(kiki_settings, "DEVELOPMENT_ALLOW_CPU_FALLBACK", False):
                raise RuntimeError(
                    "[EMBEDDING PROVIDER] ❌ GPU_REQUIRED_UNAVAILABLE: CUDA is required for BGE embedding provider "
                    "but no usable CUDA device was detected."
                )
            logger.warning("[EMBEDDING PROVIDER] CUDA unavailable. Falling back to CPU for development mode.")
            actual_device = "cpu"
        else:
            actual_device = "cuda" if cuda_ok else "cpu"

        # Determine local model path
        base_models = Path(getattr(kiki_settings, "LOCAL_MODELS_DIR", "backend/models/rag"))
        local_emb_path = base_models / "embedding" / "bge-large-en-v1.5"

        if local_emb_path.exists() and (local_emb_path / "model.safetensors").exists():
            model_target = str(local_emb_path)
            local_files_only = True
            logger.info(f"[EMBEDDING PROVIDER] Loading model from local directory: {local_emb_path}")
        else:
            model_target = self.model_name
            local_files_only = getattr(kiki_settings, "HF_LOCAL_ONLY", True)
            logger.info(f"[EMBEDDING PROVIDER] Preloading model '{self.model_name}'...")

        try:
            from sentence_transformers import SentenceTransformer
            
            # Enforce offline mode environment variables
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

            self._encoder = SentenceTransformer(
                model_target,
                device=actual_device,
                local_files_only=local_files_only
            )
            
            # Modern API: get_embedding_dimension() instead of deprecated get_sentence_embedding_dimension()
            if hasattr(self._encoder, "get_embedding_dimension"):
                self._dim = self._encoder.get_embedding_dimension()
            else:
                self._dim = self._encoder.get_sentence_embedding_dimension()

            self._device = str(self._encoder.device)
            self._loaded = True
            logger.info(
                f"[EMBEDDING PROVIDER] ✅ Loaded '{self.model_name}' "
                f"| Dim: {self._dim} | Device: {self._device}"
            )
            return True
        except Exception as e:
            self._encoder = None
            self._dim = None
            self._loaded = False
            self._device = None
            msg = f"[EMBEDDING PROVIDER] ❌ Failed to load '{self.model_name}': {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    def _get_encoder(self):
        if not self._loaded:
            logger.warning(
                "[EMBEDDING PROVIDER] _get_encoder() called without prior preload(). "
                "Loading lazily — this should not happen in production."
            )
            self.preload()
        return self._encoder

    def capabilities(self) -> ProviderCapabilities:
        dim = self._dim if self._dim is not None else 0
        return ProviderCapabilities(
            provider_name="bge_local_gpu",
            dimension=dim,
            distance_metric=self.distance_metric,
            max_batch_size=32,
            supports_filtering=True,
            supports_quantization=False,
            model_id=self.model_name or "",
            normalized=self.normalized
        )

    def embed_text(self, text: str) -> List[float]:
        encoder = self._get_encoder()
        if not encoder or not self._loaded:
            raise RuntimeError(
                f"[EMBEDDING PROVIDER] Model '{self.model_name}' is not loaded. "
                "Call preload() during application startup."
            )
        embedding = encoder.encode(text, device=self._device, normalize_embeddings=self.normalized)
        return embedding.tolist()

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        if not documents:
            return []
        encoder = self._get_encoder()
        if not encoder or not self._loaded:
            raise RuntimeError(
                f"[EMBEDDING PROVIDER] Model '{self.model_name}' is not loaded."
            )
        embeddings = encoder.encode(
            documents,
            device=self._device,
            batch_size=32,
            normalize_embeddings=self.normalized
        )
        return embeddings.tolist()


bge_embedding_provider = BGEEmbeddingProvider()
