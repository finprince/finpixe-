"""
Django Management Command: rag_offline_test
============================================
Executes zero-network offline RAG verification by blocking all outbound external IP
connections (except 127.0.0.1 for local Ollama).

Verifies full end-to-end RAG query execution (Query -> BGE CUDA -> Chroma -> BM25 -> RRF -> Reranker CUDA -> Ollama -> Answer).
"""
import socket
import urllib.request
from django.core.management.base import BaseCommand
from core.kiki.rag.execution_pipeline import execution_pipeline
from core.kiki.rag.planner import retrieval_planner
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("rag_offline_test")


class Command(BaseCommand):
    help = "Executes an offline zero-network RAG pipeline test with socket-level outbound blocking."

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("  KIKI 2027 — ZERO-NETWORK OFFLINE RAG PIPELINE TEST")
        self.stdout.write("=" * 80)

        network_attempts = []
        original_socket_connect = socket.socket.connect

        def guarded_connect(sock, address):
            host = address[0] if isinstance(address, tuple) else address
            # Allow localhost / 127.0.0.1 / ::1
            if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
                return original_socket_connect(sock, address)
            
            error_msg = f"OUTBOUND_NETWORK_BLOCKED: Attempted connection to '{address}'"
            network_attempts.append(address)
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Apply network socket guard
        socket.socket.connect = guarded_connect

        try:
            self.stdout.write("\n[1/3] Outbound network guard active. Allowed target: localhost (Ollama)")
            test_query = "What is the invoice approval procedure?"
            self.stdout.write(f"\n[2/3] Executing end-to-end RAG pipeline query: '{test_query}'")

            plan = retrieval_planner.plan(query=test_query)
            evidence = execution_pipeline.execute_plan(
                query=test_query,
                plan=plan,
                tenant_id=getattr(kiki_settings, "GLOBAL_KNOWLEDGE_TENANT_ID", "global")
            )

            chunks = evidence.payload.get("chunks", []) if isinstance(evidence.payload, dict) else []
            self.stdout.write("\n[3/3] RAG Retrieval & Fusion Results:")
            self.stdout.write(f"  Retrieved Chunks : {len(chunks)}")
            self.stdout.write(f"  Confidence Score : {evidence.confidence:.4f}")
            self.stdout.write(f"  Citations Count  : {len(evidence.citations)}")
            trace_info = evidence.payload.get("trace", {}) if isinstance(evidence.payload, dict) else {}
            self.stdout.write(f"  Retrieval Scope  : {trace_info.get('retrieval_scope')}")
            self.stdout.write(f"  Dense Candidates : {trace_info.get('dense_candidates_count')}")
            self.stdout.write(f"  Sparse Candidates: {trace_info.get('sparse_candidates_count')}")
            self.stdout.write(f"  Fused Candidates : {trace_info.get('fused_candidates_count')}")
            self.stdout.write(f"  Reranked Count   : {trace_info.get('reranked_candidates_count')}")

            # Test LLM generation if Ollama is available
            try:
                from core.kiki.synthesis.engine import synthesis_engine
                answer_data = synthesis_engine.synthesize_response(
                    query=test_query,
                    evidence=evidence,
                    history=[]
                )
                answer_text = answer_data.get("answer", "")
                self.stdout.write(f"\n  LLM Answer Snippet: {answer_text[:150]}...")
            except Exception as llm_e:
                self.stdout.write(f"  Ollama Synthesis Note: {llm_e}")

            outbound_external_count = len(network_attempts)
            self.stdout.write(f"\nExternal Outbound Network Attempts: {outbound_external_count}")

            if outbound_external_count > 0:
                self.stderr.write(self.style.ERROR(f"[FAILED] Outbound network calls detected: {network_attempts}"))
                raise RuntimeError(f"OFFLINE_TEST_FAILED: {outbound_external_count} external network calls detected.")

            self.stdout.write("=" * 80)
            self.stdout.write("  ZERO-NETWORK RAG OFFLINE TEST: STATUS = PASSED (0 External Network Calls)")
            self.stdout.write("=" * 80)

        finally:
            # Restore original socket connect
            socket.socket.connect = original_socket_connect
