import json
from typing import Dict, Any, List

RESPONSE_SYSTEM_PROMPT = """You are Kiki, an autonomous AI ERP Investigation Agent.
Generate a clear, accurate, evidence-backed answer for the user's question.
RULES:
1. Every answer MUST be supported by the provided structured evidence.
2. NEVER guess or hallucinate numbers or facts not present in evidence.
3. Structure your response with clear bullet points, key metrics, and evidence findings.
"""

def build_response_prompt(
    question: str,
    understanding_dict: Dict[str, Any],
    plan_dict: Dict[str, Any],
    evidences: List[Dict[str, Any]]
) -> str:
    return f"""Question: "{question}"
Understanding: {json.dumps(understanding_dict)}
Investigation Plan: {json.dumps(plan_dict)}
Gathered Evidence Packages: {json.dumps(evidences)}

Generate a comprehensive, evidence-backed final business response.
"""
