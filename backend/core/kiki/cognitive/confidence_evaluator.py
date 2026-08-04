from typing import Dict, Any, Optional
from ..utils.logger import kiki_logger

class ConfidenceEvaluator:
    """
    Component — Confidence Evaluator
    Determines execution confidence (HIGH, MEDIUM, LOW) based on query clarity,
    schema matching, and evidence completeness.

    Rules:
    - High Confidence: Clear intent, direct metric or valid evidence retrieved.
    - Medium Confidence: Valid data retrieved but query contained ambiguity (e.g. timeframe implied).
    - Low Confidence: Intent is vague ("tell me", "check") or data returned empty/ambiguous.
    """

    @classmethod
    def evaluate(cls, intent: str, question: str, engine_output: Optional[Dict[str, Any]]=None, evidences: Optional[list]=None) -> str:
        clean_q = question.strip().lower()
        if intent == 'CLARIFICATION' or clean_q in {'tell me', 'show me', 'check', 'display', 'what'}:
            return 'LOW'
        if engine_output:
            if engine_output.get('status') == 'AMBIGUOUS' or (engine_output.get('row_count') == 0 and intent not in ['GREETING', 'HELP', 'NAVIGATION']):
                return 'MEDIUM'
            if engine_output.get('confidence') == 1.0 or engine_output.get('reply') or engine_output.get('total_purchase') is not None:
                return 'HIGH'
        if evidences and len(evidences) > 0:
            return 'HIGH'
        if intent in {'NAVIGATION', 'GREETING', 'SMALL_TALK', 'HELP', 'KPI_QUERY'}:
            return 'HIGH'
        return 'MEDIUM'