"""
KIKI RAG Evaluation Package
===========================
Automated benchmark and evaluation metrics engine for Recall@K, Precision@K, Hit@K, MRR, NDCG, Groundedness, and Latency.
"""
from .benchmark import RAGEvaluator, rag_evaluator

__all__ = ["RAGEvaluator", "rag_evaluator"]
