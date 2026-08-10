"""
KIKI BGE Local Embedding Provider — Phase 17.4 Hardened
========================================================
Concrete implementation of BaseEmbeddingProvider with dynamic model identity discovery.
Enforces single source of truth from kiki_settings.EMBEDDING_MODEL.
Exposes actual runtime metadata (dimension, distance_metric, normalized, device, loaded).

Phase 17.4 changes:
  - Added preload() for eager startup loading (eliminates request-time cold start)
  - Model name normalised ONCE in __init__, never silently transformed at request time
  - is_loaded() property exposed for health checks
  - On load failure: RuntimeError raised — no silent model substitution
"""
from typing import List
from ..interfaces.embedding import BaseEmbeddingProvider
from ..interfaces.capabilities import ProviderCapabilities
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("bge_embedding_provider")

_SHORTNAME_MAP = {
    "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    "bge-base-en-v1.5": "BAAI/bge-base-en-v1.5",
    "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
}


def _resolve_model_name(raw: str) -> str:
    """Resolve short alias to canonical HuggingFace model ID (done once at startup)."""
    if not raw:
        return raw
    return _SHORTNAME_MAP.get(raw.strip(), raw.strip())


class BGEEmbeddingProvider(BaseEmbeddingProvider):
    """BGE Dense Vector Embedding Provider with Dynamic Identity Discovery.

    Phase 17.4: model name is resolved ONCE in __init__. preload() triggers
    eager model loading at startup. No model construction happens during user requests.
    """

    def __init__(self, model_name: str = None):
        # Resolve model name at construction time — never silently transformed later
        raw_model = model_name or getattr(kiki_settings, "EMBEDDING_MODEL", None)
        self.model_name = _resolve_model_name(raw_model)
        self.distance_metric = getattr(kiki_settings, "EMBEDDING_DISTANCE_METRIC", "cosine")
        self.normalized = getattr(kiki_settings, "EMBEDDING_NORMALIZED", True)
        self._encoder = None
        self._dim = None
        self._loaded = False

    # ── Properties ────────────────────────────────────────────────────────────

    def is_loaded(self) -> bool:
        """True if the underlying model has been successfully loaded."""
        return self._loaded

    # ── Startup preload ───────────────────────────────────────────────────────

    def preload(self) -> bool:
        """
        Eagerly load the embedding model during application startup.
        Must be called from AppConfig.ready() or RAGRuntimeManager.initialize().

        Returns True on success. Raises RuntimeError on failure (no silent fallback).
        """
        if self._loaded:
            logger.info(
                f"[EMBEDDING PROVIDER] Model '{self.model_name}' already loaded "
                f"(dim={self._dim}). Skipping preload."
            )
            return True

        if not self.model_name:
            raise RuntimeError(
                "[EMBEDDING PROVIDER] EMBEDDING_MODEL is not configured. "
                "Set KIKI_EMBEDDING_MODEL environment variable or kiki_settings.EMBEDDING_MODEL."
            )

        logger.info(f"[EMBEDDING PROVIDER] Preloading model '{self.model_name}'...")
        try:
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.model_name)
            self._dim = self._encoder.get_sentence_embedding_dimension()
            self._loaded = True
            logger.info(
                f"[EMBEDDING PROVIDER] ✅ Loaded '{self.model_name}' "
                f"| Dim: {self._dim} | Device: {self._encoder.device}"
            )
            return True
        except Exception as e:
            self._encoder = None
            self._dim = None
            self._loaded = False
            msg = f"[EMBEDDING PROVIDER] ❌ Failed to load '{self.model_name}': {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    # ── Internal lazy accessor (kept for backwards compat — calls preload) ────

    def _get_encoder(self):
        """Returns the loaded encoder. Calls preload() if not yet loaded."""
        if not self._loaded:
            # During user requests this should already be loaded by preload().
            # If not (e.g. unit test context), load lazily and log a warning.
            logger.warning(
                "[EMBEDDING PROVIDER] _get_encoder() called without prior preload(). "
                "Loading lazily — this should not happen in production."
            )
            self.preload()
        return self._encoder

    # ── Provider interface ────────────────────────────────────────────────────

    def capabilities(self) -> ProviderCapabilities:
        dim = self._dim if self._dim is not None else 0
        return ProviderCapabilities(
            provider_name="bge_local",
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
        embedding = encoder.encode(text, normalize_embeddings=self.normalized)
        return embedding.tolist()

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        if not documents:
            return []
        encoder = self._get_encoder()
        if not encoder or not self._loaded:
            raise RuntimeError(
                f"[EMBEDDING PROVIDER] Model '{self.model_name}' is not loaded. "
                "Call preload() during application startup."
            )
        embeddings = encoder.encode(
            documents, normalize_embeddings=self.normalized, batch_size=32
        )
        return embeddings.tolist()


bge_embedding_provider = BGEEmbeddingProvider()
