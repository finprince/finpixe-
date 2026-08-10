"""
KIKI Reciprocal Rank Fusion (RRF) Engine — Phase 17
===================================================
Concrete implementation of BaseFusionEngine. Merges Dense Vector search and BM25 Sparse search result lists
using formula: RRF(d) = SUM_m ( 1 / (k + r_m(d)) ) where k=60.
"""
from typing import Dict, Any, List
from ..interfaces.fusion import BaseFusionEngine
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("rrf_fusion_engine")


class RRFFusionEngine(BaseFusionEngine):
    """Reciprocal Rank Fusion Engine for Dense + Sparse Hybrid Search."""

    def fuse_results(
        self,
        result_lists: List[List[Dict[str, Any]]],
        top_k: int = 10,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """Fuses multiple ranked candidate lists into a single consolidated list."""
        if not result_lists:
            return []

        # Map chunk_id -> dict containing accumulated RRF score & chunk payload
        fused_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}

        for list_idx, rank_list in enumerate(result_lists):
            for rank_pos, chunk in enumerate(rank_list):
                cid = chunk.get("chunk_id") or chunk.get("text", "")[:30]
                if not cid:
                    continue

                if cid not in chunk_map:
                    chunk_map[cid] = dict(chunk)
                    fused_scores[cid] = 0.0

                # RRF Formula: 1 / (rrf_k + rank_pos + 1)
                rrf_score = 1.0 / (rrf_k + rank_pos + 1)
                fused_scores[cid] += rrf_score

        # Build fused list
        fused_list = []
        for cid, score in fused_scores.items():
            chunk = chunk_map[cid]
            chunk["rrf_score"] = round(score, 6)
            # Map score to normalized confidence range [0.5, 0.99]
            chunk["confidence"] = round(min(0.99, max(0.50, score * 30.0)), 4)
            fused_list.append(chunk)

        fused_list.sort(key=lambda x: x["rrf_score"], reverse=True)
        logger.info(f"[RRF FUSION] Fused {len(result_lists)} result lists ({len(fused_list)} candidate chunks) down to top {top_k}.")
        return fused_list[:top_k]


rrf_fusion_engine = RRFFusionEngine()
