"""
Fast Intent Router Classifier — Phase 15
=========================================
Classifies user prompts into core intent categories.

Phase 15 Note:
The NLU analyzer (ConversationContextManager) already provides engine_hint BEFORE
this classifier is called. The orchestrator uses NLU engine_hint as primary signal.
This classifier remains as a secondary validator — its primary active function is
the Phase 14.2 semantic vector probe for KNOWLEDGE vs. ERP routing.

All hardcoded business keyword lists have been removed. The system is now fully semantic.
"""
import re
from typing import Dict, Any
from ..providers import ProviderFactory
from ..config import kiki_settings
from ..ontology import ontology_graph
from ..logging import get_kiki_logger

logger = get_kiki_logger("intent_router")


class IntentClassifier:
    """Classifies user intent via semantic vector probe and ontology graph."""

    SYSTEM_PROMPT = (
        "You are an intent classification system for an ERP platform. "
        "Classify the user message into one of these intent types: "
        "['NAVIGATION', 'KPI_QUERY', 'ANOMALY_INVESTIGATION', 'HELP', 'WORKFLOW_ACTION']. "
        "Respond ONLY with a JSON object: {\"intent\": \"...\", \"domain\": \"...\", \"confidence\": 0.95}"
    )

    def classify(self, message: str) -> Dict[str, Any]:
        """
        Classify the (NLU-rewritten) user message.
        Primary path: Semantic vector probe (Phase 14.2 KnowledgeCandidateDetector).
        Fallback: Ontology graph + LLM.
        """
        msg_lower = message.lower().strip()

        # 1. Semantic Vector Knowledge Probe — Phase 14.2 (No hardcoded keywords)
        from .knowledge_candidate_detector import knowledge_candidate_detector
        probe_res = knowledge_candidate_detector.detect(message)
        if probe_res.get("is_candidate"):
            return {
                "intent": "KNOWLEDGE",
                "domain": "Statutory Knowledge",
                "confidence": probe_res.get("max_similarity", 0.90),
                "top_document": probe_res.get("top_document")
            }

        # 2. LLM Semantic Classification (ERP domain routing)
        try:
            provider = ProviderFactory.get_llm_provider()
            res = provider.generate_json(
                model=kiki_settings.ROUTER_MODEL,
                prompt=f"User Message: '{message}'",
                system_prompt=self.SYSTEM_PROMPT
            )
            if res and "intent" in res:
                if not res.get("domain") or res["domain"] in ["General", "ERP"]:
                    res["domain"] = ontology_graph.resolve_domain_for_term(message) or "Sales"
                return res
        except Exception as e:
            logger.warning(f"Ollama intent router fallback triggered: {str(e)}")

        # 3. Ontology Graph Fallback (deterministic schema-aware domain resolution)
        domain = ontology_graph.resolve_domain_for_term(message) or "Sales"
        if any(a_kw in msg_lower for a_kw in ["why", "mismatch", "difference", "discrepancy", "error"]):
            return {"intent": "ANOMALY_INVESTIGATION", "domain": domain, "confidence": 0.85}

        return {"intent": "KPI_QUERY", "domain": domain, "confidence": 0.80}


intent_classifier = IntentClassifier()
