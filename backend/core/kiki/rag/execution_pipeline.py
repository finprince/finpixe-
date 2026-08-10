"""
KIKI RAG Execution Pipeline — Phase 17.4 Production Hardened
==============================================================
Executes scheduled retrieval stages using concurrent ThreadPoolExecutor for parallel Dense + Sparse search.
Enforces strict Collection Scope Equivalence between Dense and Sparse streams before RRF fusion.

Phase 17.4 P0.1 Fix:
  - Dense and Sparse retrieval share the exact same retrieval scope (GLOBAL, USER, or ALL_ALLOWED)
  - Dense targets matching Chroma collection(s); Sparse targets matching BM25 engine(s)
  - Before RRF: validates dense_scope == sparse_scope. Blocks RRF on mismatch (RRF_BLOCKED_COLLECTION_SCOPE_MISMATCH)
"""
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional

from .settings import rag_settings
from .planner import RetrievalExecutionPlan, retrieval_planner
from .pipeline.rewriter import scoped_query_rewriter
from .pipeline.expander import query_expander
from .pipeline.sparse_engine import get_bm25_engine
from .pipeline.fusion_engine import rrf_fusion_engine
from .pipeline.parent_child import parent_child_expander
from .pipeline.compressor_engine import context_compressor_engine
from .pipeline.evidence_builder import evidence_builder
from .providers.chroma_provider import ChromaVectorStoreProvider
from .providers.embedding_provider import bge_embedding_provider
from .providers.reranker_provider import local_reranker_provider
from .observability.tracer import RetrievalTrace
from core.kiki.evidence.model import Evidence
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("execution_pipeline")


class ExecutionPipeline:
    """Enterprise RAG Stage Executor with Scope-Aligned Dense+Sparse Search."""

    def _resolve_retrieval_scope(
        self, tenant_id: str, plan: RetrievalExecutionPlan, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Resolves explicit retrieval scope:
          GLOBAL:      search developer global knowledge only
          USER:        search tenant/user uploaded documents only
          ALL_ALLOWED: search both global knowledge and user documents
        """
        explicit_scope = (context or {}).get("search_scope") or getattr(plan, "search_scope", None)
        if explicit_scope in ("GLOBAL", "USER", "ALL_ALLOWED"):
            return explicit_scope

        if tenant_id in ("global", "system", getattr(kiki_settings, "GLOBAL_KNOWLEDGE_TENANT_ID", "global")):
            return "GLOBAL"

        # Default for authenticated tenant requests with access to global knowledge
        return "ALL_ALLOWED"

    def execute_plan(
        self,
        query: str,
        plan: RetrievalExecutionPlan,
        context: Optional[Dict[str, Any]] = None,
        tenant_id: str = "global"
    ) -> Evidence:
        """Executes scheduled retrieval stages with strict Dense==Sparse scope alignment."""
        trace_id = f"trace_rag_{uuid.uuid4().hex[:8]}"
        pipeline_t0 = time.time()

        # 1. Resolve explicit search scope (GLOBAL, USER, or ALL_ALLOWED)
        search_scope = self._resolve_retrieval_scope(tenant_id, plan, context)
        global_coll = getattr(kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge")
        user_coll = getattr(kiki_settings, "PRIMARY_COLLECTION_NAME", "kiki_knowledge_documents")

        if search_scope == "GLOBAL":
            dense_target_collections = [global_coll]
            sparse_target_collections = [global_coll]
        elif search_scope == "USER":
            dense_target_collections = [user_coll]
            sparse_target_collections = [user_coll]
        else:  # ALL_ALLOWED
            dense_target_collections = [global_coll, user_coll]
            sparse_target_collections = [global_coll, user_coll]

        trace = RetrievalTrace(
            trace_id=trace_id,
            original_query=query,
            planner_reason=plan.planner_reason,
            top_k=plan.top_k,
            bm25_enabled=plan.enable_bm25_sparse,
            reranker_enabled=plan.enable_reranker
        )

        # Log trace scope telemetry
        logger.info(
            f"[EXECUTION PIPELINE] Executing plan for '{query[:50]}' | Scope: {search_scope} | "
            f"Dense Collections: {dense_target_collections} | Sparse Collections: {sparse_target_collections}"
        )

        # 2. Query Rewrite (Scoped Coreference Resolution)
        effective_query = query
        if plan.enable_query_rewrite and rag_settings.ENABLE_QUERY_REWRITE:
            t0 = time.time()
            hist_summary = (context or {}).get("history_summary", "")
            curr_entity = (context or {}).get("current_entity")
            effective_query = scoped_query_rewriter.rewrite(
                query=query,
                history_summary=hist_summary,
                current_entity=curr_entity
            )
            trace.rewrite_latency_ms = round((time.time() - t0) * 1000, 2)
        trace.rewritten_query = effective_query

        # 3. Multi-Query Expansion
        queries_to_search = [effective_query]
        if plan.enable_multi_query and rag_settings.ENABLE_MULTI_QUERY:
            t0 = time.time()
            queries_to_search = query_expander.expand_query(effective_query, num_variations=2)
            trace.expansion_latency_ms = round((time.time() - t0) * 1000, 2)
        trace.expanded_queries = queries_to_search

        # 4. Parallel Dense + Sparse Retrieval (ThreadPoolExecutor)
        dense_scope_tag = search_scope
        sparse_scope_tag = search_scope

        def run_dense():
            t0 = time.time()
            res = []
            for coll_name in dense_target_collections:
                provider = ChromaVectorStoreProvider(collection_name=coll_name)
                for q in queries_to_search:
                    q_vec = bge_embedding_provider.embed_text(q)
                    chunks = provider.query_vectors(q_vec, top_k=plan.top_k)
                    for c in chunks:
                        c["source_collection"] = coll_name
                        c["retrieval_stream"] = "dense"
                    res.extend(chunks)
            lat = round((time.time() - t0) * 1000, 2)
            return res, lat

        def run_sparse():
            if not (plan.enable_bm25_sparse and rag_settings.ENABLE_BM25):
                return [], 0.0
            t0 = time.time()
            res = []
            for coll_name in sparse_target_collections:
                engine = get_bm25_engine(coll_name)
                for q in queries_to_search:
                    chunks = engine.search_sparse(q, top_k=plan.top_k)
                    for c in chunks:
                        c["source_collection"] = coll_name
                        c["retrieval_stream"] = "sparse"
                    res.extend(chunks)
            lat = round((time.time() - t0) * 1000, 2)
            return res, lat

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_dense = executor.submit(run_dense)
            future_sparse = executor.submit(run_sparse)

            dense_results, trace.dense_latency_ms = future_dense.result()
            sparse_results, trace.sparse_latency_ms = future_sparse.result()

        trace.dense_candidates_count = len(dense_results)
        trace.sparse_candidates_count = len(sparse_results)

        # 5. Phase 17.4 RRF Fusion Safety Check: Dense Scope == Sparse Scope
        if dense_scope_tag != sparse_scope_tag:
            logger.error(
                f"[RRF SAFETY] ❌ RRF_BLOCKED_COLLECTION_SCOPE_MISMATCH: "
                f"dense_scope='{dense_scope_tag}', sparse_scope='{sparse_scope_tag}' | "
                "Refusing to fuse mismatched retrieval corpora."
            )
            # Return un-fused dense results only as fallback
            fused_candidates = dense_results[:plan.top_k * 2]
        else:
            t0 = time.time()
            candidate_lists = []
            if dense_results:
                candidate_lists.append(dense_results)
            if sparse_results:
                candidate_lists.append(sparse_results)

            fused_candidates = rrf_fusion_engine.fuse_results(
                candidate_lists, top_k=plan.top_k * 2
            )
            trace.fusion_latency_ms = round((time.time() - t0) * 1000, 2)
        
        trace.fused_candidates_count = len(fused_candidates)

        if not fused_candidates:
            trace.total_pipeline_latency_ms = round((time.time() - pipeline_t0) * 1000, 2)
            return evidence_builder.build_evidence(query=query, chunks=[], trace_data=trace.to_dict())

        # 6. Cross-Encoder Reranker
        reranked_candidates = fused_candidates
        if plan.enable_reranker and rag_settings.ENABLE_RERANKER:
            t0 = time.time()
            reranked_candidates = local_reranker_provider.rerank(
                query=effective_query,
                candidates=fused_candidates,
                top_k=plan.top_k
            )
            trace.rerank_latency_ms = round((time.time() - t0) * 1000, 2)
        trace.reranked_candidates_count = len(reranked_candidates)

        # 7. Parent-Child Expansion & Context Compression
        selected_chunks = reranked_candidates[:plan.top_k]
        if plan.enable_parent_child and rag_settings.ENABLE_PARENT_CHILD:
            selected_chunks = parent_child_expander.expand_chunks(selected_chunks)

        if plan.enable_compression and rag_settings.ENABLE_CONTEXT_COMPRESSION:
            t0 = time.time()
            selected_chunks = context_compressor_engine.compress_chunks(effective_query, selected_chunks)
            trace.compression_latency_ms = round((time.time() - t0) * 1000, 2)

        trace.final_selected_count = len(selected_chunks)
        trace.total_pipeline_latency_ms = round((time.time() - pipeline_t0) * 1000, 2)

        # 8. Build Grounded Evidence Package
        trace_data = trace.to_dict()
        trace_data["retrieval_scope"] = search_scope
        trace_data["dense_collections"] = dense_target_collections
        trace_data["sparse_collections"] = sparse_target_collections
        trace_data["scope_aligned"] = (dense_scope_tag == sparse_scope_tag)

        evidence_obj = evidence_builder.build_evidence(
            query=effective_query,
            chunks=selected_chunks,
            trace_data=trace_data
        )

        logger.info(
            f"[EXECUTION PIPELINE] Completed trace '{trace_id}' in {trace.total_pipeline_latency_ms}ms | "
            f"Scope: {search_scope} | Dense: {len(dense_results)}, Sparse: {len(sparse_results)} -> Selected: {len(selected_chunks)}"
        )

        return evidence_obj


execution_pipeline = ExecutionPipeline()
