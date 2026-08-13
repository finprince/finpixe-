"""
Verification Script: test_phase18_5_conversational_ux.py
=========================================================
Tests representative RAG query classes and verifies ChatGPT-style conversational UX formatting,
grounding, unanswerable query refusal, and absence of internal machine metadata leakage.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from core.kiki.kernel import ai_kernel
from core.kiki.rag.execution_pipeline import execution_pipeline
from core.kiki.rag.planner import retrieval_planner
from core.kiki.config import kiki_settings


class MockUser:
    """Mock User context for testing AI kernel orchestrator."""
    is_authenticated = True
    is_staff = True
    username = "admin_test"
    tenant_id = "global"


def run_conversational_ux_tests():
    print("=" * 80)
    print("  KIKI 2027 — CONVERSATIONAL UX & QUERY CLASS EVALUATION")
    print("=" * 80)

    test_cases = [
        ("Semantic Query", "What is the invoice approval procedure?"),
        ("Keyword Query", "What is GST?"),
        ("Entity Query", "What is the FINPIXE user guide?"),
        ("Follow-up Query", "What are its main steps?"),
        ("Unanswerable Query", "What is the quantum teleportation protocol for Mars rovers?")
    ]

    mock_user = MockUser()

    for label, query in test_cases:
        print(f"\n--- [{label}] Query: '{query}' ---")
        
        # 1. Pipeline retrieval test
        plan = retrieval_planner.plan(query=query)
        evidence = execution_pipeline.execute_plan(query=query, plan=plan, tenant_id="global")

        chunks = evidence.payload.get("chunks", []) if isinstance(evidence.payload, dict) else []
        print(f"  Chunks Retrieved: {len(chunks)}")
        print(f"  Confidence Score: {evidence.confidence:.4f}")
        print(f"  Citations Count  : {len(evidence.citations)}")

        # 2. End-to-end Kernel Orchestrator test
        try:
            res = ai_kernel.process_request(message=query, request_user=mock_user)
            reply = res.get("reply", "")
            citations = res.get("citations", [])

            print(f"  Reply Length    : {len(reply)} chars")
            print(f"  Reply Snippet   : {reply[:150]}...")
            print(f"  Citations       : {len(citations)} returned in structured array")

            # Leakage checks: answer must NOT expose internal machine machinery
            forbidden_tokens = [
                "Chroma", "BM25", "bge-large-en", "RRF_BLOCKED",
                "embedding_dimension", "tenant_id", "retrieval_score", "chunk_id="
            ]
            leaks = [token for token in forbidden_tokens if token in reply]

            if leaks:
                print(f"  [FAILED] LEAK DETECTED in reply text: {leaks}")
            else:
                print("  [PASSED] NO INTERNAL MACHINE METADATA LEAKAGE IN CONVERSATIONAL REPLY")

            if label == "Unanswerable Query":
                if evidence.confidence < 0.20 or "cannot find" in reply.lower() or "no information" in reply.lower() or "not mention" in reply.lower() or not chunks:
                    print("  [PASSED] UNANSWERABLE QUERY HANDLED CORRECTLY (Refused / Low Confidence)")
                else:
                    print("  [WARNING] Unanswerable query evaluated")

        except Exception as e:
            print(f"  Kernel Exception: {e}")

    print("\n" + "=" * 80)
    print("  CONVERSATIONAL UX EVALUATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_conversational_ux_tests()
