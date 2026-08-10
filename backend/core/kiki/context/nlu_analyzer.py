"""
KIKI LLM Semantic NLU Analyzer — Phase 15 V3 Architecture
===========================================================
Uses local Ollama to semantically understand user intent, resolve coreferences,
detect topic switches, and rewrite follow-up questions. Returns pure semantic JSON.

Strict V3 Rule:
The LLM performs ONLY natural language understanding (coreference, entity/topic resolution, question rewriting).
It returns ZERO engine, intent, tool, routing, workflow, or navigation fields.
The Application Backend is the sole authority for Execution Planning.
"""
import json
from typing import Dict, Any, Optional, Set
from ..providers import ProviderFactory
from ..config import kiki_settings
from ..logging import get_kiki_logger

logger = get_kiki_logger("nlu_analyzer")

# ─────────────────────────────────────────────────────────────────────────────
# Phase 17.4 — Structural NLU Bypass Signal Detector
# NO business keyword routing. Purely structural / conversational dependency.
# ─────────────────────────────────────────────────────────────────────────────

# Pronouns and relative references that require coreference resolution
_COREF_TOKENS: Set[str] = {
    "it", "its", "that", "this", "those", "these", "they", "them",
    "he", "she", "his", "her", "their", "itself",
}
_COREF_PHRASES = (
    "the above", "the previous", "the last one", "as before",
    "the workflow", "the algorithm", "the policy", "that module",
    "the document", "how does it", "what is it", "where is it",
)


def needs_nlu(message: str, current_entity: Optional[str] = None) -> bool:
    """
    Determines whether NLU (Ollama) is required for this message.

    Returns True (NLU needed) when:
      1. Message contains pronouns or relative references (coreference signals)
      2. Session has an active current_entity (follow-up conversational context)

    Returns False (NLU safe to skip) when:
      - Message is fully self-contained with no pronoun/reference ambiguity
      - No active session entity to resolve against

    IMPORTANT: This function uses ONLY structural/conversational signals.
    It does NOT check for business domain keywords (Sales, Inventory, GST, etc.).
    Business content must NEVER influence this routing decision.
    """
    msg_lower = message.lower().strip()
    words = set(msg_lower.split())

    # Signal 1: pronoun tokens in the message
    if words & _COREF_TOKENS:
        return True

    # Signal 2: relative reference phrases
    if any(phrase in msg_lower for phrase in _COREF_PHRASES):
        return True

    # Signal 3: active session entity means follow-up is possible
    if current_entity:
        return True

    return False

# ─────────────────────────────────────────────────────────────────
# NLU System Prompt — Pure Semantic Understanding ONLY (V3 Schema)
# Target: <200 tokens output | No chain-of-thought | JSON only
# ─────────────────────────────────────────────────────────────────
NLU_SYSTEM_PROMPT = """\
You are a semantic NLU analyzer for an enterprise ERP AI assistant called KIKI.
Analyze the user message and conversation history. Return ONLY valid JSON. No explanation, no markdown, no reasoning.

JSON Schema (return exactly this structure):
{
  "resolved_entity": "<the primary subject/entity being discussed — NEVER null if identifiable>",
  "resolved_topic": "<topic/domain label or null>",
  "rewritten_question": "<fully self-contained question — all pronouns and relative references replaced>",
  "clarification_required": false,
  "clarification_message": null,
  "confidence": 0.95
}

ENTITY EXTRACTION RULES:
1. ALWAYS set resolved_entity to the main subject of the message.
   Examples:
   - "What is AST-RIM Optimizer?" → resolved_entity = "AST-RIM Optimizer"
   - "Explain leave policy" → resolved_entity = "Leave Policy"
   - "Tell me about GST" → resolved_entity = "GST"
   - "Show today sales" → resolved_entity = "Sales"

COREFERENCE & REFERENCE RESOLUTION RULES:
2. If message contains pronouns (it, its, that, this, those, these, he, she, they, them, the above, the previous, the workflow, the algorithm, the policy, the document) AND Current Entity is available in context:
   - Replace the pronoun with Current Entity in rewritten_question.
   - Example: Current Entity = "AST-RIM Optimizer", message = "What is the core algorithm for that?"
     → rewritten_question = "What is the core algorithm for AST-RIM Optimizer?"

3. If message is a follow-up date/filter refinement (e.g. "What about yesterday?", "Show only Chennai branch", "Last month"):
   - Combine with the previous question topic in rewritten_question.
   - Example: History = "Show today sales", message = "What about yesterday?"
     → rewritten_question = "Show yesterday sales"

AMBIGUITY RULE:
4. Set clarification_required = true ONLY when ALL of these are true:
   - Message is a ambiguous pronoun question ("Explain the algorithm", "How to install it?")
   - Current Entity is None (no prior context)
   - Write a helpful clarification_message asking the user to specify the component.

5. rewritten_question must be 100% self-contained — no pronouns, no "that", no "it".
6. Output maximum 180 tokens. Do not include intent, engine, tool, or routing fields.\
"""


class NLUAnalyzer:
    """LLM-powered semantic Natural Language Understanding layer for KIKI."""

    def analyze(
        self,
        message: str,
        history_summary: str,
        current_entity: Optional[str] = None,
        current_document: Optional[str] = None,
        current_domain: str = "UNKNOWN"
    ) -> Dict[str, Any]:
        """
        Calls local Ollama to semantically understand the message.
        Returns pure semantic JSON (V3 schema) — never selects engines or tools.
        """
        context_block = (
            f"Current Entity: {current_entity or 'None'}\n"
            f"Current Document: {current_document or 'None'}\n"
            f"Current Domain: {current_domain}\n"
            f"Conversation History:\n{history_summary}"
        )

        user_prompt = (
            f"Context:\n{context_block}\n\n"
            f"New User Message: \"{message}\"\n\n"
            f"Return Pure Semantic JSON:"
        )

        logger.info(
            f"[NLU ANALYZER] Analyzing: '{message}' | "
            f"Current Entity: {current_entity} | Domain: {current_domain}"
        )

        try:
            provider = ProviderFactory.get_llm_provider()
            result = provider.generate_json(
                model=kiki_settings.ROUTER_MODEL,
                prompt=user_prompt,
                system_prompt=NLU_SYSTEM_PROMPT
            )

            if result and isinstance(result, dict) and "rewritten_question" in result:
                logger.info(
                    f"[NLU ANALYZER V3] Entity: {result.get('resolved_entity')} | "
                    f"Topic: {result.get('resolved_topic')} | "
                    f"Rewritten: '{result.get('rewritten_question')}' | "
                    f"Clarification: {result.get('clarification_required')} | "
                    f"Confidence: {result.get('confidence')}"
                )
                return result

        except Exception as e:
            logger.warning(f"[NLU ANALYZER] LLM call failed, using deterministic fallback: {str(e)}")

        # Deterministic Fallback (when Ollama offline)
        return self._deterministic_fallback(message, current_entity)

    def _deterministic_fallback(self, message: str, current_entity: Optional[str]) -> Dict[str, Any]:
        """Fallback when LLM is unavailable."""
        msg_lower = message.lower().strip()
        coreference_tokens = {"it", "its", "that", "this", "those", "these", "they", "them"}
        words = set(msg_lower.split())
        has_coref = bool(words & coreference_tokens) or any(
            phrase in msg_lower for phrase in
            ["the above", "the previous", "the workflow", "the algorithm", "the policy", "that module"]
        )

        if has_coref and current_entity:
            rewritten = message
            for token in ["that", "it", "its", "this", "those", "these", "they", "them"]:
                rewritten = rewritten.replace(f" {token} ", f" {current_entity} ")
                rewritten = rewritten.replace(f" {token}?", f" {current_entity}?")
            return {
                "resolved_entity": current_entity,
                "resolved_topic": None,
                "rewritten_question": rewritten,
                "clarification_required": False,
                "clarification_message": None,
                "confidence": 0.85
            }

        if has_coref and not current_entity:
            return {
                "resolved_entity": None,
                "resolved_topic": None,
                "rewritten_question": message,
                "clarification_required": True,
                "clarification_message": "Could you clarify which entity or module you are referring to?",
                "confidence": 0.40
            }

        return {
            "resolved_entity": None,
            "resolved_topic": None,
            "rewritten_question": message,
            "clarification_required": False,
            "clarification_message": None,
            "confidence": 0.80
        }


nlu_analyzer = NLUAnalyzer()
