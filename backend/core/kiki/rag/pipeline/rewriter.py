"""
KIKI Scoped Query Rewriter — Phase 17
=====================================
Concrete implementation of BaseQueryRewriter.
Strict Scope: Resolves pronouns ('it', 'that', 'this') and omitted entities in multi-turn dialogues.
MUST NOT perform domain classification, intent routing, reasoning, or answer generation.
"""
from typing import Optional
from ..interfaces.rewriter import BaseQueryRewriter
from core.kiki.context.nlu_analyzer import nlu_analyzer
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("scoped_query_rewriter")


class ScopedQueryRewriter(BaseQueryRewriter):
    """Pure Coreference Pronoun & Follow-up Query Rewriter."""

    def rewrite(
        self,
        query: str,
        history_summary: str = "",
        current_entity: Optional[str] = None
    ) -> str:
        """
        Resolves coreference pronouns and omitted entity references.
        Returns pure rewritten query string.
        """
        if not query or not query.strip():
            return query

        msg_lower = query.lower().strip()
        coref_tokens = {"it", "its", "that", "this", "those", "these", "they", "them"}
        words = set(msg_lower.split())
        has_coref = bool(words & coref_tokens) or any(
            phrase in msg_lower for phrase in
            ["the above", "the previous", "the workflow", "the algorithm", "the policy", "that module", "casual leaves", "which section"]
        )

        if not has_coref and not history_summary:
            return query

        # Delegate coreference resolution to NLU analyzer pure JSON schema
        try:
            nlu_res = nlu_analyzer.analyze(
                message=query,
                history_summary=history_summary,
                current_entity=current_entity
            )
            rewritten = nlu_res.get("rewritten_question") or query
            logger.info(f"[QUERY REWRITER] Original: '{query}' -> Rewritten: '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.warning(f"[QUERY REWRITER] Coreference rewrite exception: {str(e)}")

        # Deterministic fallback pronoun substitution
        if current_entity and has_coref:
            rewritten = query
            for token in ["that", "it", "its", "this", "those", "these", "they", "them"]:
                rewritten = rewritten.replace(f" {token} ", f" {current_entity} ")
                rewritten = rewritten.replace(f" {token}?", f" {current_entity}?")
            for phrase in ["the algorithm", "the policy", "the workflow", "the module"]:
                if phrase in rewritten.lower():
                    rewritten = rewritten.replace(phrase, current_entity)
            return rewritten

        return query


scoped_query_rewriter = ScopedQueryRewriter()
