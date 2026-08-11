"""
KIKI Local Neural Reranker Provider — Phase 19 Hardened
========================================================
Concrete implementation of BaseReranker utilizing local cross-encoder scoring
on NVIDIA CUDA GPU.

Phase 19 CUDA & Offline Enforcements:
  - Loads CrossEncoder from local path (backend/models/rag/reranker/ms-marco-MiniLM-L-6-v2/) with local_files_only=True.
  - Enforces CUDA execution (cuda:0).
  - Fail-fast with GPU_REQUIRED_UNAVAILABLE if CUDA is required but unavailable.
"""
import os
import torch
from pathlib import Path
from typing import Dict, Any, List
from ..interfaces.reranker import BaseReranker
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("reranker_provider")


class LocalRerankerProvider(BaseReranker):
    """Local Cross-Encoder Reranker Provider with CUDA Acceleration & Zero-Network Offline Mode."""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or getattr(
            kiki_settings, "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        self.target_device = getattr(kiki_settings, "RERANKER_DEVICE", "cuda")
        self._cross_encoder = None
        self._is_loaded: bool = False
        self._device = None

    def is_loaded(self) -> bool:
        return self._is_loaded

    def preload(self) -> bool:
        """
        Eagerly load the cross-encoder onto CUDA during application startup.
        Loads strictly from local model directory with zero network calls.
        """
        if self._is_loaded:
            logger.info(f"[RERANKER PROVIDER] Cross-encoder '{self.model_name}' already loaded on {self._device}.")
            return True

        # Check CUDA requirement
        cuda_ok = torch.cuda.is_available()
        if self.target_device == "cuda" and not cuda_ok:
            if getattr(kiki_settings, "RAG_REQUIRE_GPU", True) and not getattr(kiki_settings, "DEVELOPMENT_ALLOW_CPU_FALLBACK", False):
                raise RuntimeError(
                    "[RERANKER PROVIDER] ❌ GPU_REQUIRED_UNAVAILABLE: CUDA is required for CrossEncoder reranker "
                    "but no usable CUDA device was detected."
                )
            logger.warning("[RERANKER PROVIDER] CUDA unavailable. Falling back to CPU for development mode.")
            actual_device = "cpu"
        else:
            actual_device = "cuda" if cuda_ok else "cpu"

        # Determine local model path
        base_models = Path(getattr(kiki_settings, "LOCAL_MODELS_DIR", "backend/models/rag"))
        local_rerank_path = base_models / "reranker" / "ms-marco-MiniLM-L-6-v2"

        if local_rerank_path.exists() and (local_rerank_path / "model.safetensors").exists():
            model_target = str(local_rerank_path)
            local_files_only = True
            logger.info(f"[RERANKER PROVIDER] Loading reranker from local directory: {local_rerank_path}")
        else:
            model_target = self.model_name
            local_files_only = getattr(kiki_settings, "HF_LOCAL_ONLY", True)
            logger.info(f"[RERANKER PROVIDER] Preloading cross-encoder '{self.model_name}'...")

        try:
            from sentence_transformers import CrossEncoder

            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

            self._cross_encoder = CrossEncoder(
                model_target,
                device=actual_device,
                local_files_only=local_files_only
            )
            self._device = str(self._cross_encoder.model.device)
            self._is_loaded = True
            logger.info(f"[RERANKER PROVIDER] ✅ Cross-encoder '{self.model_name}' loaded on {self._device}.")
            return True
        except Exception as e:
            self._cross_encoder = None
            self._is_loaded = False
            self._device = None
            msg = f"[RERANKER PROVIDER] ❌ Failed to load '{self.model_name}': {e}"
            logger.error(msg)
            if getattr(kiki_settings, "RAG_REQUIRE_GPU", True):
                raise RuntimeError(msg) from e
            return False

    def _get_encoder(self):
        if not self._is_loaded:
            logger.warning(
                "[RERANKER PROVIDER] _get_encoder() called without prior preload(). "
                "Loading lazily — this should not happen in production."
            )
            self.preload()
        return self._cross_encoder if self._is_loaded else None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        if top_k is None:
            top_k = getattr(kiki_settings, "RERANKER_TOP_K", 5)

        if not candidates:
            return []

        if len(candidates) <= 1:
            return candidates[:top_k]

        encoder = self._get_encoder()

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

        # Neural cross-encoder scoring on CUDA GPU
        pairs = [[query, c.get("text", "")] for c in candidates]
        try:
            scores = encoder.predict(pairs, batch_size=32)
            scored_candidates = []
            for idx, c in enumerate(candidates):
                c_copy = dict(c)
                raw_score = float(scores[idx])
                norm_score = 1.0 / (1.0 + (2.71828 ** (-raw_score)))
                c_copy["rerank_score"] = round(norm_score, 4)
                c_copy["reranker_available"] = True
                scored_candidates.append(c_copy)

            scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
            logger.info(
                f"[RERANKER PROVIDER] Reranked {len(candidates)} → top {min(top_k, len(scored_candidates))} candidates on {self._device}."
            )
            return scored_candidates[:top_k]
        except Exception as e:
            logger.error(f"[RERANKER PROVIDER] Reranking exception on {self._device}: {e}")
            return candidates[:top_k]


local_reranker_provider = LocalRerankerProvider()
