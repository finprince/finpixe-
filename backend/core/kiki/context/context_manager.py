"""
KIKI Conversation Context Manager — Phase 15 V3
=================================================
Orchestrates NLU semantic analysis, conversation state, coreference resolution,
and question rewriting. Inserts BEFORE all routing engines.

Pipeline:
  Message → NLU Analyzer → Update Session State → Return ContextResult (Pure Semantic Context)
"""
from dataclasses import dataclass
from typing import Optional, Any
from .session_store import session_store

from .conversation_state import ConversationTurn
from .nlu_analyzer import nlu_analyzer, needs_nlu
from ..config import kiki_settings
from ..logging import get_kiki_logger
from datetime import datetime

logger = get_kiki_logger("context_manager")


@dataclass
class ContextResult:
    """Output of the Conversation Context Manager passed to the AI Orchestrator Planner."""
    session_id: str
    original_question: str
    rewritten_question: str          # Fully self-contained question (all pronouns/references resolved)
    was_rewritten: bool
    resolved_entity: Optional[str]
    resolved_document: Optional[str]
    resolved_topic: Optional[str]
    clarification_required: bool
    clarification_message: Optional[str]
    confidence: float
    conversation_state: Optional[Any] = None



class ConversationContextManager:
    """
    Single entry point for all conversation context operations.
    Integrates NLU analysis, session state management, and question rewriting.
    """

    def process(self, message: str, session_id: str, tenant_id: str) -> ContextResult:
        """
        Main processing pipeline.
        Returns a ContextResult whose rewritten_question is used by the Capability Planner.
        """
        # 1. Load or create session state
        state = session_store.get_or_create(session_id=session_id, tenant_id=tenant_id)

        # 2. Build compact history summary for NLU prompt
        max_history = getattr(kiki_settings, "NLU_MAX_HISTORY_TURNS", 5)
        history_summary = state.get_history_summary(last_n=max_history)

        # 3. Phase 17.4 — Structural NLU bypass
        #    Skip expensive Ollama call for self-contained queries with no coref dependency.
        #    Decision is STRUCTURAL only (pronouns, session entity) — no keyword routing.
        bypass_enabled = getattr(kiki_settings, "NLU_BYPASS_ENABLED", True)
        nlu_required = needs_nlu(message, current_entity=state.current_entity)

        if bypass_enabled and not nlu_required:
            logger.info(
                f"[CONTEXT MANAGER] NLU bypass: query is self-contained, "
                f"no coreference/session entity detected. Skipping Ollama NLU."
            )
            nlu_result = nlu_analyzer._deterministic_fallback(message, state.current_entity)
        else:
            # 3a. Call Local Ollama NLU Analyzer (Pure Semantic Understanding V3 Schema)
            nlu_result = nlu_analyzer.analyze(
                message=message,
                history_summary=history_summary,
                current_entity=state.current_entity,
                current_document=state.current_document,
                current_domain=state.current_domain
            )

        rewritten = nlu_result.get("rewritten_question") or message
        was_rewritten = (rewritten.strip().lower() != message.strip().lower())
        resolved_entity = nlu_result.get("resolved_entity") or state.current_entity
        resolved_document = nlu_result.get("resolved_document") or state.current_document
        resolved_topic = nlu_result.get("resolved_topic") or state.current_topic
        clarification_required = nlu_result.get("clarification_required", False)
        clarification_message = nlu_result.get("clarification_message")
        confidence = nlu_result.get("confidence", 0.80)

        logger.info(
            f"[CONTEXT LOG V3] Session: {session_id} | Turn: {len(state.turns) + 1}\n"
            f"  Original Question  : {message}\n"
            f"  Rewritten Question : {rewritten}\n"
            f"  Was Rewritten      : {was_rewritten}\n"
            f"  Resolved Entity    : {resolved_entity}\n"
            f"  Resolved Document  : {resolved_document}\n"
            f"  Resolved Topic     : {resolved_topic}\n"
            f"  Clarification      : {clarification_required}\n"
            f"  Confidence         : {confidence}"
        )

        # 4. Update session state (only if NOT asking for clarification)
        if not clarification_required:
            state.update_context(nlu_result)
            turn = ConversationTurn(
                turn_index=len(state.turns),
                original_question=message,
                rewritten_question=rewritten,
                intent="SEMANTIC_ANALYSIS",
                engine_hint="DYNAMIC_PLANNER",
                resolved_entity=resolved_entity,
                resolved_topic=resolved_topic,
                resolved_document=resolved_document,
                domain=state.current_domain,
                timestamp=datetime.utcnow()
            )
            max_turns = getattr(kiki_settings, "MAX_CONTEXT_TURNS", 10)
            state.add_turn(turn, max_turns=max_turns)
            session_store.save(state)

        return ContextResult(
            session_id=session_id,
            original_question=message,
            rewritten_question=rewritten,
            was_rewritten=was_rewritten,
            resolved_entity=resolved_entity,
            resolved_document=resolved_document,
            resolved_topic=resolved_topic,
            clarification_required=clarification_required,
            clarification_message=clarification_message,
            confidence=confidence,
            conversation_state=state
        )



conversation_context_manager = ConversationContextManager()
