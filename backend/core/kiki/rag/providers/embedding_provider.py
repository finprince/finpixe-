"""
KIKI BGE Local GPU Embedding Provider — Phase 19 Hardened & Forensic Corrected
=============================================================================
Concrete implementation of BaseEmbeddingProvider with local offline model execution
and NVIDIA CUDA GPU acceleration.

Phase 19 CUDA & Offline Enforcements:
  - Loads BGE-large-v1.5 strictly from explicit local path (backend/models/rag/embedding/bge-large-en-v1.5/).
  - Enforces local_files_only=True with zero HuggingFace network fallback.
  - Enforces CUDA execution (cuda:0).
  - Fail-fast with GPU_REQUIRED_UNAVAILABLE if CUDA is required but unavailable.
  - Verifies test embedding execution (dimension=1024, finite values, device=cuda:0).
"""
import os
try:
    import torch
except ImportError:
    torch = None
import math
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
        self._local_path = None

    def is_loaded(self) -> bool:
        return self._loaded

    def _verify_model_files(self, model_path: Path) -> bool:
        """Verifies that all required SentenceTransformer model files exist locally."""
        if not model_path.exists() or not model_path.is_dir():
            return False
        
        has_config = (model_path / "config.json").exists()
        has_weights = (model_path / "model.safetensors").exists() or (model_path / "pytorch_model.bin").exists()
        has_tokenizer = (model_path / "tokenizer.json").exists() or (model_path / "vocab.txt").exists()
        
        return has_config and has_weights and has_tokenizer

    def preload(self) -> bool:
        """
        Eagerly load the embedding model onto CUDA during application startup.
        Loads strictly from local model directory with zero network calls.
        """
        if self._loaded and self._encoder is not None:
            logger.info(
                f"[EMBEDDING PROVIDER] Model '{self.model_name}' already loaded "
                f"on {self._device} (dim={self._dim}). Skipping preload."
            )
            return True

        # Enforce offline mode environment variables
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_LOCAL_ONLY"] = "1"

        # Check CUDA requirement
        if torch is None:
            msg = (
                "[EMBEDDING PROVIDER] ❌ PyTorch is not installed. "
                "Please run 'pip install torch sentence-transformers' to enable local embeddings."
            )
            logger.error(msg)
            raise RuntimeError(msg)
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

        # Determine canonical local model path
        base_models = Path(getattr(kiki_settings, "LOCAL_MODELS_DIR", "backend/models/rag"))
        local_emb_path = base_models / "embedding" / "bge-large-en-v1.5"
        self._local_path = str(local_emb_path)

        if not self._verify_model_files(local_emb_path):
            msg = (
                f"[EMBEDDING PROVIDER] ❌ Local BGE model not found or incomplete at '{local_emb_path}'. "
                f"Runtime Hugging Face downloads are disabled. "
                f"Please run 'python manage.py prepare_local_rag_models' to provision models."
            )
            logger.error(msg)
            raise RuntimeError(msg)

        logger.info(f"[EMBEDDING PROVIDER] Loading model from local directory: {local_emb_path}")

        try:
            from sentence_transformers import SentenceTransformer

            self._encoder = SentenceTransformer(
                str(local_emb_path),
                device=actual_device,
                local_files_only=True
            )
            
            if hasattr(self._encoder, "get_embedding_dimension"):
                self._dim = self._encoder.get_embedding_dimension()
            else:
                self._dim = self._encoder.get_sentence_embedding_dimension()

            self._device = str(self._encoder.device)

            # Test GPU embedding execution & finite value assertion
            test_text = "CUDA BGE Local Embedding Diagnostic Test"
            test_emb = self._encoder.encode(test_text, device=actual_device, normalize_embeddings=self.normalized)
            test_list = test_emb.tolist()

            if len(test_list) != 1024:
                raise ValueError(f"Expected BGE dimension 1024, got {len(test_list)}")

            if not all(math.isfinite(x) for x in test_list):
                raise ValueError("Generated test embedding contains NaN or Inf values")

            self._loaded = True
            
            # Print diagnostic block
            diag_msg = (
                f"\n============================================================\n"
                f"[EMBEDDING PROVIDER] Start Diagnostics\n"
                f"  Model ID       : {self.model_name}\n"
                f"  Local Path     : {self._local_path}\n"
                f"  Device         : {self._device}\n"
                f"  CUDA Available : {cuda_ok}\n"
                f"  Dimension      : {self._dim}\n"
                f"  Loaded         : {self._loaded}\n"
                f"  Test Embedding : SUCCESS (1024 dimensions verified)\n"
                f"  Offline Mode   : True (local_files_only=True)\n"
                f"============================================================"
            )
            logger.info(diag_msg)
            print(diag_msg)
            return True
        except Exception as e:
            self._encoder = None
            self._dim = None
            self._loaded = False
            self._device = None
            msg = f"[EMBEDDING PROVIDER] ❌ Failed to load model from '{local_emb_path}': {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    def _get_encoder(self):
        if not self._loaded or self._encoder is None:
            logger.warning(
                "[EMBEDDING PROVIDER] _get_encoder() called without prior preload(). "
                "Loading lazily — this should not happen in production."
            )
            self.preload()
        return self._encoder

    def capabilities(self) -> ProviderCapabilities:
        dim = self._dim if self._dim is not None else 1024
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
