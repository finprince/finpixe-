import json
from typing import Dict, Any, List

EVIDENCE_SYSTEM_PROMPT = """You are Kiki Evidence Evaluator. Evaluate whether enough evidence has been collected to accurately answer the business question."""

def build_evidence_prompt(
    question: str,
    understanding_dict: Dict[str, Any],
    evidences: List[Dict[str, Any]],
    current_step: int,
    max_steps: int
) -> str:
    return f"""User Question: "{question}"
Understanding: {json.dumps(understanding_dict)}
Gathered Evidence Packages: {json.dumps(evidences)}
Step: {current_step} of {max_steps}

Do you have sufficient evidence to answer the question thoroughly?
Return ONLY a JSON object:
{{
  "has_enough_info": true / false,
  "reasoning": "Brief explanation of why info is complete or missing",
  "next_search_terms": ["products", "items"]
}}
"""
