"""
AI Kernel Central Orchestrator — Phase 18.5 Conversational UX Hardening
========================================================================
Single, non-bypassable entry point for KIKI AI Operating System requests.
Operates strictly as an AI Orchestrator Planner discovering capabilities via CapabilityRegistry.

Pipeline:
  1. User Message
  2. Conversational Greeting Check (Fast-path natural greeting without RAG overhead)
  3. ConversationContextManager (Session Store + Pure Semantic NLU via Ollama)
  4. AI Orchestrator Planner (CapabilityRegistry probe_all & plan_execution)
  5. Capability Execution (Knowledge, ERP Analytics, Workflow, Navigation plugins)
  6. EvidenceAggregator (Merges N Evidence objects & deduplicates citations)
  7. Return Clean REST API payload (Clean answer + clean structured citations array)
"""
import uuid
from typing import Dict, Any
from ..context import conversation_context_manager, session_store
from ..capabilities.base import ExecutionPolicy
from ..capabilities.registry import capability_registry
from ..capabilities.plugins import *  # Ensures plugins are registered
from ..evidence.aggregator import evidence_aggregator
from ..security import tenant_guard
from ..telemetry import metrics_collector
from ..config import kiki_settings
from ..logging import get_kiki_logger

GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "thanks", "thank you", "okay", "ok", "bye", "goodbye"}


class AIKernelOrchestrator:
    """Central AI Kernel Orchestrator Engine for KIKI 2027."""

    def process_request(self, message: str, request_user, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process incoming chat request synchronously using V3 Orchestration Pipeline."""
        trace_id = f"trace_{uuid.uuid4().hex[:8]}"
        tenant_context = tenant_guard.extract_context(request_user)
        tenant_id = tenant_context["tenant_id"]

        logger = get_kiki_logger("ai_kernel", trace_id=trace_id, tenant_id=tenant_id)
        logger.info(f"[AI KERNEL V3] Received request: '{message}'")

        metrics_collector.increment_counter("total_requests")

        # ── Conversational Greetings Fast-Path (No RAG Overhead) ─────────────────
        clean_msg = message.strip().lower().rstrip("!.,")
        if clean_msg in GREETINGS:
            logger.info(f"[KERNEL V3] Greeting detected: '{clean_msg}'. Returning natural conversational reply.")
            if clean_msg in {"thanks", "thank you"}:
                reply = "You're welcome! Let me know if you need any further assistance with FINPIXE ERP or your documents."
            elif clean_msg in {"bye", "goodbye"}:
                reply = "Goodbye! Have a great day ahead."
            else:
                reply = "Hello! I'm KIKI 2027, your local AI assistant. How can I help you today?"

            return {
                "id": trace_id,
                "intent": "CONVERSATIONAL",
                "domain": "General",
                "reply": reply,
                "citations": [],
                "action_cards": []
            }

        # ─────────────────────────────────────────────────────────────────────
        # 1. CONVERSATION CONTEXT & PURE SEMANTIC NLU (Local Ollama)
        # ─────────────────────────────────────────────────────────────────────
        session_id = (context_data or {}).get("session_id") or f"sess_{trace_id}"
        ctx = conversation_context_manager.process(
            message=message,
            session_id=session_id,
            tenant_id=tenant_id
        )

        logger.info(
            f"[KERNEL V3] Session: {session_id} | Original: '{message}' | "
            f"Rewritten: '{ctx.rewritten_question}' | Resolved Entity: {ctx.resolved_entity}"
        )

        # ── Ambiguity / Clarification Fast-Path ───────────────────────────
        if ctx.clarification_required:
            clarification_msg = ctx.clarification_message
            if isinstance(clarification_msg, list):
                clarification_msg = (
                    "Could you clarify which of the following you are referring to?\n" +
                    "\n".join(f"• {item}" for item in clarification_msg)
                )
            elif not clarification_msg:
                clarification_msg = "Could you please clarify your question? I need more context to provide an accurate answer."

            return {
                "id": trace_id,
                "intent": "CLARIFICATION",
                "domain": "General",
                "reply": clarification_msg,
                "citations": [],
                "action_cards": []
            }

        effective_message = ctx.rewritten_question

        # ─────────────────────────────────────────────────────────────────────
        # 2. CAPABILITY PROBING & AI ORCHESTRATOR PLANNING
        # The backend planner evaluates ALL capabilities dynamically via probe()
        # ─────────────────────────────────────────────────────────────────────
        probe_results = capability_registry.probe_all(effective_message, ctx)
        execution_policy, execution_plan = capability_registry.plan_execution(probe_results)

        logger.info(
            f"[AI PLANNER 16.1] Execution Policy: {execution_policy.value} | "
            f"Selected {len(execution_plan)} plugin(s): {[p.capability_name for p in execution_plan]}"
        )

        if execution_policy == ExecutionPolicy.REJECT:
            return {
                "id": trace_id,
                "intent": "REJECT",
                "domain": "General",
                "reply": "I am unable to process this request with available capabilities.",
                "citations": [],
                "action_cards": []
            }

        # ─────────────────────────────────────────────────────────────────────
        # 3. CAPABILITY EXECUTION & EVIDENCE AGGREGATION
        # Executes plugins, receives List[Evidence], merges payload & citations
        # ─────────────────────────────────────────────────────────────────────
        evidence_list = capability_registry.execute_plan(
            execution_plan=execution_plan,
            rewritten_question=effective_message,
            context=ctx,
            tenant_id=tenant_id
        )

        aggregated_output = evidence_aggregator.aggregate(execution_policy, evidence_list)

        # ─────────────────────────────────────────────────────────────────────
        # 4. MEMORY FEEDBACK TO CONVERSATION STATE
        # Update ConversationState with top retrieved document family/entity
        # ─────────────────────────────────────────────────────────────────────
        if evidence_list:
            top_ev = evidence_list[0]
            top_meta = top_ev.metadata
            state = session_store.get_or_create(session_id=session_id, tenant_id=tenant_id)
            if "top_document" in top_meta:
                state.current_document = top_meta["top_document"]
            if "domain" in top_meta:
                state.current_domain = top_meta["domain"]
            session_store.save(state)

        # Construct clean REST API response DTO
        top_intent = evidence_list[0].type if evidence_list else "GENERAL"
        top_domain = evidence_list[0].metadata.get("domain", "General") if evidence_list else "General"

        is_debug = (context_data or {}).get("debug", False) or getattr(kiki_settings, "DEBUG_RAG", False)

        res_payload = {
            "id": trace_id,
            "intent": top_intent,
            "domain": top_domain,
            "reply": aggregated_output["reply"],
            "citations": aggregated_output["citations"],
            "action_cards": aggregated_output["action_cards"]
        }

        # Include developer trace only when debug mode is explicitly active
        if is_debug:
            res_payload["evidence_package"] = aggregated_output["evidence_package"]
            res_payload["context_metadata"] = {
                "session_id": session_id,
                "original_question": message,
                "rewritten_question": effective_message,
                "was_rewritten": ctx.was_rewritten,
                "resolved_entity": ctx.resolved_entity,
                "execution_plan": [p.capability_name for p in execution_plan]
            }

        return res_payload


ai_kernel = AIKernelOrchestrator()
