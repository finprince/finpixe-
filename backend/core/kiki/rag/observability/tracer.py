"""
KIKI Retrieval Trace & Observability Tracer — Phase 17
======================================================
Captures developer-only stage-by-stage latency, query rewrites, expanded queries, dense/sparse scores,
RRF fusion ranks, rerank scores, compression ratio, token counts, and errors per request.
Never exposed to end users.
"""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("retrieval_tracer")


@dataclass
class RetrievalTrace:
    """Developer-only diagnostic trace recording full retrieval pipeline execution metrics."""
    trace_id: str
    original_query: str
    rewritten_query: str = ""
    expanded_queries: List[str] = field(default_factory=list)
    planner_reason: str = ""
    top_k: int = 5
    bm25_enabled: bool = False
    reranker_enabled: bool = False
    
    # Candidate chunk counts & scores per stage
    dense_candidates_count: int = 0
    sparse_candidates_count: int = 0
    fused_candidates_count: int = 0
    reranked_candidates_count: int = 0
    final_selected_count: int = 0
    
    # Latency Breakdown (milliseconds)
    rewrite_latency_ms: float = 0.0
    expansion_latency_ms: float = 0.0
    dense_latency_ms: float = 0.0
    sparse_latency_ms: float = 0.0
    fusion_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    compression_latency_ms: float = 0.0
    total_pipeline_latency_ms: float = 0.0
    
    errors: List[str] = field(default_factory=list)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "original_query": self.original_query,
            "rewritten_query": self.rewritten_query,
            "expanded_queries": self.expanded_queries,
            "planner_reason": self.planner_reason,
            "top_k": self.top_k,
            "bm25_enabled": self.bm25_enabled,
            "reranker_enabled": self.reranker_enabled,
            "counts": {
                "dense": self.dense_candidates_count,
                "sparse": self.sparse_candidates_count,
                "fused": self.fused_candidates_count,
                "reranked": self.reranked_candidates_count,
                "final": self.final_selected_count
            },
            "latencies_ms": {
                "rewrite": self.rewrite_latency_ms,
                "expansion": self.expansion_latency_ms,
                "dense": self.dense_latency_ms,
                "sparse": self.sparse_latency_ms,
                "fusion": self.fusion_latency_ms,
                "rerank": self.rerank_latency_ms,
                "compression": self.compression_latency_ms,
                "total": self.total_pipeline_latency_ms
            },
            "errors": self.errors
        }
