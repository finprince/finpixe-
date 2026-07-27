import json
from typing import Dict, Any

PLANNING_SYSTEM_PROMPT = """You are an expert ERP Investigator. Build a step-by-step reasoning plan to investigate a business question. DO NOT write SQL or database queries in this plan."""

def build_planning_prompt(question: str, understanding_dict: Dict[str, Any]) -> str:
    return f"""Question: "{question}"
Understanding: {json.dumps(understanding_dict)}

Create a step-by-step investigation plan.
Return ONLY a JSON object with keys:
- "goal": "..."
- "steps": [
    {{"step_number": 1, "description": "Locate target entity records", "objective": "Find customer ID"}},
    {{"step_number": 2, "description": "Compare sales totals across periods", "objective": "Determine variance"}}
  ]
"""
