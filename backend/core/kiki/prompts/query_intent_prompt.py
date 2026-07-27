import json
from typing import Dict, Any, List

QUERY_INTENT_SYSTEM_PROMPT = """You are Kiki Query Intent Generator. Your task is to output a structured QueryIntent JSON specifying what database information is needed for the current investigation step. DO NOT write raw SQL."""

def build_query_intent_prompt(
    question: str,
    understanding_dict: Dict[str, Any],
    schemas: List[Dict[str, Any]],
    evidences: List[Dict[str, Any]],
    current_step: int
) -> str:
    return f"""User Question: "{question}"
Understanding: {json.dumps(understanding_dict)}
Relevant Table Schemas Available: {json.dumps(schemas)}
Evidence Gathered So Far: {json.dumps(evidences)}
Current Step Number: {current_step}

Return ONLY a JSON object representing the QueryIntent:
{{
  "objective": "Retrieve metric totals for question",
  "target_tables": ["vouchers"],
  "entity": null,
  "metrics": ["total_amount"],
  "period": ["current_month"],
  "group_by": [],
  "order_by": [],
  "limit": 50,
  "search_terms": ["sales", "vouchers"]
}}

STRICT RULE: Set "entity": null UNLESS the user's question explicitly mentions a specific customer, vendor, or product name! Do NOT invent entity names.
"""
