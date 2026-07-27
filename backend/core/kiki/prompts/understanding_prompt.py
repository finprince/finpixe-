UNDERSTANDING_SYSTEM_PROMPT = """You are Kiki ERP Investigation Agent. Your task is to analyze business questions and extract intent, objective, entities, timeframe, and investigation scope into structured JSON."""

def build_understanding_prompt(question: str) -> str:
    return f"""Analyze the following business question:
"{question}"

Return ONLY a JSON object with these keys:
- "intent": (e.g. "Business Investigation", "Financial Summary", "Sales Audit")
- "objective": (Clear statement of what needs to be answered)
- "entities": (Array of customer/vendor/product names ONLY IF explicitly named in question, otherwise empty [])
- "timeframe": (e.g. "this month", "current_month", "overdue")
- "scope": (e.g. "sales, invoices, products")
"""

