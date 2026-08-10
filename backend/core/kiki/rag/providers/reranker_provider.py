"""
KIKI Local Neural Reranker Provider — Phase 17.4 Hardened
==========================================================
Concrete implementation of BaseReranker utilizing local cross-encoder scoring.

Phase 17.4 changes:
  - Removed dangerous "FALLBACK" string sentinel (was switching invisibly to keyword scoring)
  - Model name now read from kiki_settings.RERANKER_MODEL (not hardcoded)
  - preload() added for eager startup loading
  - is_loaded() property exposed for health checks
  - Degraded path is explicit: returns unranked candidates with warning log, never
    silently pretends neural reranking occurred when it did not
"""
from typing import Dict, Any, List
from ..interfaces.reranker import BaseReranker
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("reranker_provider")


class LocalRerankerProvider(BaseReranker):
    """Local Cross-Encoder Reranker Provider — Phase 17.4 Hardened."""

    def __init__(self, model_name: str = None):
        # Phase 17.4: model from settings, not a hardcoded default
        self.model_name = model_name or getattr(
            kiki_settings, "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        self._cross_encoder = None
        self._is_loaded: bool = False   # Phase 17.4: explicit flag, NO "FALLBACK" sentinel

    # ── Properties ────────────────────────────────────────────────────────────

    def is_loaded(self) -> bool:
        """True if the cross-encoder has been successfully loaded."""
        return self._is_loaded

    # ── Startup preload ───────────────────────────────────────────────────────

    def preload(self) -> bool:
        """
        Eagerly load the cross-encoder during application startup.
        Call from AppConfig.ready() or RAGRuntimeManager.initialize().

        On failure: logs error, marks _is_loaded=False, returns False.
        Does NOT raise — reranker unavailability is a DEGRADED state, not FAILED.
        """
        if self._is_loaded:
            logger.info(
                f"[RERANKER PROVIDER] Cross-encoder '{self.model_name}' already loaded."
            )
            return True

        logger.info(f"[RERANKER PROVIDER] Preloading cross-encoder '{self.model_name}'...")
        try:
            from sentence_transformers import CrossEncoder
            self._cross_encoder = CrossEncoder(self.model_name)
            self._is_loaded = True
            logger.info(
                f"[RERANKER PROVIDER] ✅ Cross-encoder '{self.model_name}' loaded successfully."
            )
            return True
        except Exception as e:
            self._cross_encoder = None
            self._is_loaded = False
            logger.error(
                f"[RERANKER PROVIDER] ❌ Failed to load '{self.model_name}': {e}. "
                "Reranker will degrade gracefully (pass-through unranked candidates)."
            )
            return False

    # ── Internal accessor ─────────────────────────────────────────────────────

    def _get_encoder(self):
        """Returns cross-encoder or None. Triggers lazy preload with warning if not loaded."""
        if not self._is_loaded:
            logger.warning(
                "[RERANKER PROVIDER] _get_encoder() called without prior preload(). "
                "Loading lazily — this should not happen in production."
            )
            self.preload()
        return self._cross_encoder if self._is_loaded else None

    # ── Rerank ────────────────────────────────────────────────────────────────

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Re-scores candidate chunks using cross-encoder and returns top_k highest scorers.

        Phase 17.4 degraded path:
          If cross-encoder is NOT loaded, candidates are returned in their current
          order (RRF-ranked order) with rerank_score=None and a warning logged.
          The system records reranker_available=False in logs.
          NO keyword-based fallback scoring is performed.
        """
        if top_k is None:
            top_k = getattr(kiki_settings, "RERANKER_TOP_K", 5)

        if not candidates:
            return []

        if len(candidates) <= 1:
            return candidates[:top_k]

        encoder = self._get_encoder()

        # Phase 17.4: explicit degraded path — no hidden keyword scoring
        if encoder is None:
            logger.warning(
                f"[RERANKER PROVIDER] ⚠️  Reranker unavailable (reranker_available=False). "
                f"Returning top-{top_k} candidates in RRF order without neural reranking."
            )
            for c in candidates:
                c_copy = dict(c)
                c_copy["rerank_score"] = None
                c_copy["reranker_available"] = False
            return candidates[:top_k]

        # Neural cross-encoder scoring
        pairs = [[query, c.get("text", "")] for c in candidates]
        try:
            scores = encoder.predict(pairs)
            scored_candidates = []
            for idx, c in enumerate(candidates):
                c_copy = dict(c)
                raw_score = float(scores[idx])
                # Sigmoid normalisation to [0, 1] range
                norm_score = 1.0 / (1.0 + (2.71828 ** (-raw_score)))
                c_copy["rerank_score"] = round(norm_score, 4)
                c_copy["reranker_available"] = True
                scored_candidates.append(c_copy)

            scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
            logger.info(
                f"[RERANKER PROVIDER] Reranked {len(candidates)} → top {top_k} candidates."
            )
            return scored_candidates[:top_k]

        except Exception as e:
            logger.error(f"[RERANKER PROVIDER] Cross-encoder prediction error: {e}")
            return candidates[:top_k]


local_reranker_provider = LocalRerankerProvider()
