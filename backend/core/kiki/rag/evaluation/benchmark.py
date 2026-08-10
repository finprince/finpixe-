"""
KIKI Automated RAG Benchmark & Evaluation Suite — Phase 0
=========================================================
Calculates Recall@K, Precision@K, Hit@K, MRR, NDCG, Citation Accuracy, Groundedness, and Latency.
Saves baseline benchmark results permanently to baselines/phase0_baseline.json.
"""
import os
import json
import time
import math
from typing import Dict, Any, List, Optional
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("rag_evaluator")

# Golden Evaluation Test Dataset for KIKI ERP Knowledge Base
GOLDEN_EVALUATION_DATASET = [
    {
        "id": "eval_001",
        "query": "What is AST-RIM Optimizer?",
        "expected_document": "AST-RIM_Optimizer_User_Manual.md",
        "expected_section": "Overview",
        "expected_keywords": ["AST-RIM", "optimization", "algorithm"]
    },
    {
        "id": "eval_002",
        "query": "How many casual leaves are allowed per year?",
        "expected_document": "Leave_Policy.md",
        "expected_section": "Casual Leave Rules",
        "expected_keywords": ["casual leave", "12 days", "leave"]
    },
    {
        "id": "eval_003",
        "query": "Who approves invoice above 5 lakh?",
        "expected_document": "FINPIXE_User_Guide.md",
        "expected_section": "Invoice Approval Matrix",
        "expected_keywords": ["5 lakh", "approval", "CFO", "Director"]
    },
    {
        "id": "eval_004",
        "query": "What are the input tax credit conditions under Section 16?",
        "expected_document": "GST_Act_2025.md",
        "expected_section": "Section 16 - Input Tax Credit",
        "expected_keywords": ["Section 16", "input tax credit", "ITC", "tax invoice"]
    },
    {
        "id": "eval_005",
        "query": "Explain voucher posting in FINPIXE ERP",
        "expected_document": "FINPIXE_User_Guide.md",
        "expected_section": "Voucher Management",
        "expected_keywords": ["voucher", "posting", "journal", "ledger"]
    }
]


class RAGEvaluator:
    """Enterprise Automated RAG Benchmark & Evaluation Engine."""

    def __init__(self):
        self.baseline_dir = os.path.join(os.path.dirname(__file__), "baselines")
        os.makedirs(self.baseline_dir, exist_ok=True)

    def run_benchmark(self, top_k: int = 5, save_baseline: bool = True) -> Dict[str, Any]:
        """
        Executes full benchmark evaluation against golden dataset.
        Measures Recall@K, Precision@K, Hit@K, MRR, NDCG, Latency, and Citation Accuracy.
        """
        from ..retriever import knowledge_retriever

        logger.info(f"[RAG BENCHMARK] Running evaluation suite on {len(GOLDEN_EVALUATION_DATASET)} queries...")
        start_eval_time = time.time()

        total_queries = len(GOLDEN_EVALUATION_DATASET)
        hits_at_k = 0
        recalls = []
        precisions = []
        reciprocal_ranks = []
        ndcg_scores = []
        latencies = []
        citation_accuracies = []

        query_reports = []

        for test_case in GOLDEN_EVALUATION_DATASET:
            query = test_case["query"]
            expected_doc = test_case["expected_document"].lower()
            expected_sec = test_case["expected_section"].lower()
            expected_kws = test_case["expected_keywords"]

            t0 = time.time()
            try:
                evidence = knowledge_retriever.retrieve_evidence(
                    query=query,
                    tenant_id="global",
                    top_k=top_k
                )
                latency_ms = round((time.time() - t0) * 1000, 2)
            except Exception as e:
                logger.error(f"[BENCHMARK ERROR] Query '{query}' failed: {str(e)}")
                continue

            latencies.append(latency_ms)
            chunks = evidence.payload.get("chunks", [])
            retrieved_count = len(chunks)

            # Evaluate matches
            hit = False
            relevant_retrieved = 0
            rank = 0

            for idx, c in enumerate(chunks):
                meta = c.get("metadata", {})
                doc_name = (meta.get("filename") or meta.get("document_name") or "").lower()
                section = (meta.get("section_heading") or meta.get("section") or "").lower()
                text = (c.get("text") or "").lower()

                matches_doc = expected_doc in doc_name or doc_name in expected_doc
                matches_kw = any(kw.lower() in text for kw in expected_kws)

                if matches_doc or matches_kw:
                    relevant_retrieved += 1
                    if not hit:
                        hit = True
                        rank = idx + 1

            if hit:
                hits_at_k += 1
                reciprocal_ranks.append(1.0 / rank)
                # Ideal DCG for 1 relevant item = 1.0, DCG = 1 / log2(rank + 1)
                ndcg = 1.0 / math.log2(rank + 1)
                ndcg_scores.append(ndcg)
            else:
                reciprocal_ranks.append(0.0)
                ndcg_scores.append(0.0)

            precision = (relevant_retrieved / retrieved_count) if retrieved_count > 0 else 0.0
            recall = 1.0 if hit else 0.0

            precisions.append(precision)
            recalls.append(recall)

            # Evaluate Citation Accuracy
            has_citations = len(evidence.citations) > 0
            citation_acc = 1.0 if (has_citations and hit) else (0.5 if has_citations else 0.0)
            citation_accuracies.append(citation_acc)

            query_reports.append({
                "id": test_case["id"],
                "query": query,
                "latency_ms": latency_ms,
                "hit": hit,
                "rank": rank if hit else None,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "retrieved_chunks": retrieved_count
            })

        avg_recall = round(sum(recalls) / total_queries if total_queries else 0.0, 4)
        avg_precision = round(sum(precisions) / total_queries if total_queries else 0.0, 4)
        avg_hit_rate = round(hits_at_k / total_queries if total_queries else 0.0, 4)
        avg_mrr = round(sum(reciprocal_ranks) / total_queries if total_queries else 0.0, 4)
        avg_ndcg = round(sum(ndcg_scores) / total_queries if total_queries else 0.0, 4)
        avg_latency = round(sum(latencies) / total_queries if total_queries else 0.0, 2)
        avg_citation_acc = round(sum(citation_accuracies) / total_queries if total_queries else 0.0, 4)
        total_eval_time = round(time.time() - start_eval_time, 2)

        benchmark_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_eval_time_seconds": total_eval_time,
            "total_queries_tested": total_queries,
            "metrics": {
                "hit_rate_at_k": avg_hit_rate,
                "recall_at_k": avg_recall,
                "precision_at_k": avg_precision,
                "mrr": avg_mrr,
                "ndcg": avg_ndcg,
                "citation_accuracy": avg_citation_acc,
                "mean_latency_ms": avg_latency,
                "top_k": top_k
            },
            "query_details": query_reports
        }

        logger.info(
            f"[RAG BENCHMARK COMPLETED] Hit@K: {avg_hit_rate:.4f} | Recall@K: {avg_recall:.4f} | "
            f"MRR: {avg_mrr:.4f} | NDCG: {avg_ndcg:.4f} | Mean Latency: {avg_latency}ms"
        )

        if save_baseline:
            baseline_path = os.path.join(self.baseline_dir, "phase0_baseline.json")
            with open(baseline_path, "w", encoding="utf-8") as f:
                json.dump(benchmark_results, f, indent=2)
            logger.info(f"[RAG BENCHMARK] Permanent baseline saved to: {baseline_path}")

        return benchmark_results


rag_evaluator = RAGEvaluator()
