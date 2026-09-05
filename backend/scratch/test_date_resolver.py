import os
import sys
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.kiki.tools.date_resolver import date_resolver

test_cases = [
    "How much sales did I make this month?",
    "What were my sales last month?",
    "Show me today's sales.",
    "What were my purchases in August?",
    "Show sales for August 2026",
    "What were my sales in FY 2025-26?",
    "Show purchases for FY 2024-25",
    "What was my profit last financial year?",
    "Sales from 1 August to 15 August",
    "Sales from 2026-08-01 to 2026-08-15",
    "Show purchases between 1 April and 30 April",
    "What were Q1 sales?",
    "Show sales for yesterday"
]

ref = datetime.date(2026, 9, 2)
print("=== DATE RESOLVER TESTS (Reference: 2026-09-02) ===")
for q in test_cases:
    res = date_resolver.resolve_date_range(q, ref_date=ref)
    print(f"Query: '{q}'\n  -> Result: {res}\n")
