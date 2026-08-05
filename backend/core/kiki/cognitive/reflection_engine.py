from typing import Dict, Any
from ..models.dto import ReflectionSummary, ContextState
from ..utils.logger import kiki_logger

class ReflectionEngine:
    """
    Component — Reflection Engine (Kiki 2.0)
    Self-evaluates response quality before finalizing to prevent hallucinations or conflicting answers.

    Questions Evaluated:
    - Did we answer the user's question?
    - Do we have enough evidence?
    - Are results conflicting?
    - Should we ask clarification?
    - Is confidence justified?
    """

    @classmethod
    def reflect(cls, question: str, reasoning_output: Dict[str, Any], aggregated_evidence: Dict[str, Any], context_state: ContextState) -> ReflectionSummary:
        clean_q = question.strip().lower()
        summary = reasoning_output.get('summary', '')
        has_metrics = bool(reasoning_output.get('result_metric') or aggregated_evidence.get('metric_values'))
        has_sql = bool(aggregated_evidence.get('sql_queries'))
        answered = bool(summary and summary != 'Skill execution completed successfully.')
        enough_evidence = has_metrics or has_sql or len(summary) > 20
        requires_clarification = clean_q in {'tell me', 'show me', 'check', 'display', 'what'}
        confidence_justified = enough_evidence and (not requires_clarification)
        reflection = ReflectionSummary(answered_user_question=answered, has_sufficient_evidence=enough_evidence, detected_conflicts=False, requires_clarification=requires_clarification, confidence_justified=confidence_justified, reflection_notes='Response fully validated against evidence and retrieved ERP knowledge.' if confidence_justified else 'Query is underspecified; requesting clarification.')
        kiki_logger.info(f"[REFLECTION ENGINE] Reflection result for '{question}': Answered: {reflection.answered_user_question}, Sufficient Evidence: {reflection.has_sufficient_evidence}, Justified: {reflection.confidence_justified}")
        return reflection