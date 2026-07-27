"""
Prompts package for Kiki AI ERP Agent.
Contains specialized prompt generators for each LLM reasoning phase.
"""
from .understanding_prompt import build_understanding_prompt, UNDERSTANDING_SYSTEM_PROMPT
from .planning_prompt import build_planning_prompt, PLANNING_SYSTEM_PROMPT
from .query_intent_prompt import build_query_intent_prompt, QUERY_INTENT_SYSTEM_PROMPT
from .evidence_prompt import build_evidence_prompt, EVIDENCE_SYSTEM_PROMPT
from .response_prompt import build_response_prompt, RESPONSE_SYSTEM_PROMPT

__all__ = [
    "build_understanding_prompt",
    "UNDERSTANDING_SYSTEM_PROMPT",
    "build_planning_prompt",
    "PLANNING_SYSTEM_PROMPT",
    "build_query_intent_prompt",
    "QUERY_INTENT_SYSTEM_PROMPT",
    "build_evidence_prompt",
    "EVIDENCE_SYSTEM_PROMPT",
    "build_response_prompt",
    "RESPONSE_SYSTEM_PROMPT",
]
