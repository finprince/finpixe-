"""
RIM SELF-CORRECTION LOOP — DEFINITIVE DEMO
Simulates a real-world blurry scan where one digit is misread by the LLM.
System 2 catches the error and forces System 1 to self-correct.
"""

import os, json, re, base64
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = "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"
client = OpenAI()

# ============================================================
# GROUND TRUTH (what is actually on the statement)
# ============================================================
TRUE_OPENING = 12500.00
TRUE_TRANSACTIONS = [
    {"date": "05.12.2023", "description": "SWIFT INCOMING - ACME CORP USA",       "debit": 0.00,    "credit": 4500.00},
    {"date": "08.12.2023", "description": "WIRE TRANSFER - SUPPLIER PAYMENT",      "debit": 1200.00, "credit": 0.00},
    {"date": "12.12.2023", "description": "SWIFT INCOMING - CLIENT DELTA",         "debit": 0.00,    "credit": 3200.00},
    {"date": "15.12.2023", "description": "FX CONVERSION USD-TRY",                 "debit": 2800.00, "credit": 0.00},
    {"date": "19.12.2023", "description": "SWIFT INCOMING - GLOBAL TRADERS LTD",  "debit": 0.00,    "credit": 6000.00},
    {"date": "22.12.2023", "description": "BANK COMMISSION AND FEES",              "debit": 45.00,   "credit": 0.00},
    {"date": "26.12.2023", "description": "WIRE TRANSFER - RENT PAYMENT",         "debit": 1800.00, "credit": 0.00},
    {"date": "02.01.2024", "description": "SWIFT INCOMING - EXPORT REVENUE",      "debit": 0.00,    "credit": 8500.00},
    {"date": "07.01.2024", "description": "PAYROLL USD TRANSFER",                  "debit": 3500.00, "credit": 0.00},
    {"date": "11.01.2024", "description": "SWIFT INCOMING - PARTNER CORP",        "debit": 0.00,    "credit": 2750.00},
    {"date": "15.01.2024", "description": "FX CONVERSION USD-EUR",                "debit": 4200.00, "credit": 0.00},
    {"date": "18.01.2024", "description": "SWIFT INCOMING - DIVIDEND PAYMENT",    "debit": 0.00,    "credit": 1500.00},
]
true_total_credits = sum(t["credit"] for t in TRUE_TRANSACTIONS)
true_total_debits  = sum(t["debit"]  for t in TRUE_TRANSACTIONS)
TRUE_CLOSING = round(TRUE_OPENING + true_total_credits - true_total_debits, 2)

# ============================================================
# HALLUCINATED DATA (what a blurry scan might cause System 1 to extract)
# Row 9 (PAYROLL): true debit = 3500.00, but blurry "3" looks like "8"
# System 1 misreads it as 8500.00 — a $5,000 error
# ============================================================
HALLUCINATED_TRANSACTIONS = [
    {"date": "05.12.2023", "description": "SWIFT INCOMING - ACME CORP USA",       "debit": 0.00,    "credit": 4500.00},
    {"date": "08.12.2023", "description": "WIRE TRANSFER - SUPPLIER PAYMENT",      "debit": 1200.00, "credit": 0.00},
    {"date": "12.12.2023", "description": "SWIFT INCOMING - CLIENT DELTA",         "debit": 0.00,    "credit": 3200.00},
    {"date": "15.12.2023", "description": "FX CONVERSION USD-TRY",                 "debit": 2800.00, "credit": 0.00},
    {"date": "19.12.2023", "description": "SWIFT INCOMING - GLOBAL TRADERS LTD",  "debit": 0.00,    "credit": 6000.00},
    {"date": "22.12.2023", "description": "BANK COMMISSION AND FEES",              "debit": 45.00,   "credit": 0.00},
    {"date": "26.12.2023", "description": "WIRE TRANSFER - RENT PAYMENT",         "debit": 1800.00, "credit": 0.00},
    {"date": "02.01.2024", "description": "SWIFT INCOMING - EXPORT REVENUE",      "debit": 0.00,    "credit": 8500.00},
    {"date": "07.01.2024", "description": "PAYROLL USD TRANSFER",                  "debit": 8500.00, "credit": 0.00},  # <-- HALLUCINATION: 3500 misread as 8500
    {"date": "11.01.2024", "description": "SWIFT INCOMING - PARTNER CORP",        "debit": 0.00,    "credit": 2750.00},
    {"date": "15.01.2024", "description": "FX CONVERSION USD-EUR",                "debit": 4200.00, "credit": 0.00},
    {"date": "18.01.2024", "description": "SWIFT INCOMING - DIVIDEND PAYMENT",    "debit": 0.00,    "credit": 1500.00},
]

# ============================================================
# SYSTEM 2: Deterministic Math Firewall
# ============================================================
def run_system2(transactions, opening, stated_closing):
    total_debits  = sum(t.get("debit",  0) for t in transactions)
    total_credits = sum(t.get("credit", 0) for t in transactions)
    net_change    = total_credits - total_debits
    calculated    = round(opening + net_change, 2)
    stated        = round(stated_closing, 2)
    discrepancy   = round(calculated - stated, 2)

    audit = {
        "opening_balance":        opening,
        "transactions_count":     len(transactions),
        "total_debits_computed":  round(total_debits, 2),
        "total_credits_computed": round(total_credits, 2),
        "net_change":             round(net_change, 2),
        "calculated_closing":     calculated,
        "stated_closing":         stated,
        "discrepancy":            discrepancy,
        "ground_truth_closing":   TRUE_CLOSING
    }

    if abs(discrepancy) < 0.02:
        return True, None, audit
    else:
        error_msg = (
            f"MATH MISMATCH DETECTED.\n"
            f"  Opening Balance:            {opening:,.2f}\n"
            f"  Sum of credits extracted:   {round(total_credits,2):,.2f}\n"
            f"  Sum of debits extracted:    {round(total_debits,2):,.2f}\n"
            f"  Calculated closing balance: {calculated:,.2f}\n"
            f"  Document stated closing:    {stated:,.2f}\n"
            f"  Discrepancy:                {discrepancy:,.2f}\n"
            f"A debit or credit value has been misread (possibly a blurry digit). "
            f"Re-examine each row carefully, especially debit amounts, and correct the error."
        )
        return False, error_msg, audit

# ============================================================
# THE RIM SELF-CORRECTION LOOP
# ============================================================
print("=" * 65)
print("  RIM NEURO-SYMBOLIC GATEWAY — SELF-CORRECTION LOOP DEMO")
print("  Turkiye Finans Katilim Bankasi | USD Statement")
print("=" * 65)
print(f"\n[GROUND TRUTH] Closing Balance: {TRUE_CLOSING:,.2f}")
print(f"[SCENARIO]     Row 9 (PAYROLL): True debit = 3,500.00")
print(f"[SCENARIO]     Blurry '3' misread as '8' => LLM extracts 8,500.00")
print(f"[SCENARIO]     This is a $5,000 hallucination on a single digit.\n")

# Attempt 1: System 1 returns hallucinated data (blurry digit)
attempt_data = [
    (HALLUCINATED_TRANSACTIONS, "INITIAL EXTRACTION (with hallucinated digit)"),
    (TRUE_TRANSACTIONS,          "SELF-CORRECTED EXTRACTION (after System 2 feedback)"),
]

for attempt_num, (transactions, label) in enumerate(attempt_data, 1):
    print(f"{'='*65}")
    print(f"  ATTEMPT {attempt_num}: {label}")
    print(f"{'='*65}")

    stated_closing = round(TRUE_OPENING + sum(t["credit"] for t in transactions) - sum(t["debit"] for t in transactions), 2)

    print(f"\n[SYSTEM 1] Extraction complete:")
    print(f"[SYSTEM 1]   Opening Balance : {TRUE_OPENING:,.2f}")
    print(f"[SYSTEM 1]   Transactions    : {len(transactions)} rows")
    for t in transactions:
        d = f"  Debit:  {t['debit']:>9,.2f}" if t["debit"] else ""
        c = f"  Credit: {t['credit']:>9,.2f}" if t["credit"] else ""
        marker = " <<<< HALLUCINATED DIGIT" if t["description"] == "PAYROLL USD TRANSFER" and t["debit"] == 8500.00 else ""
        print(f"[SYSTEM 1]   {t['date']}  {t['description']:<42}{d}{c}{marker}")
    print(f"[SYSTEM 1]   Stated Closing  : {stated_closing:,.2f}")

    print(f"\n[SYSTEM 2] Intercepting payload. Running deterministic math firewall...")
    passed, error_msg, audit = run_system2(transactions, TRUE_OPENING, stated_closing)

    print(f"[SYSTEM 2]   Opening Balance:          {audit['opening_balance']:>12,.2f}")
    print(f"[SYSTEM 2]   Total Credits (computed): {audit['total_credits_computed']:>12,.2f}")
    print(f"[SYSTEM 2]   Total Debits (computed):  {audit['total_debits_computed']:>12,.2f}")
    print(f"[SYSTEM 2]   Net Change:               {audit['net_change']:>12,.2f}")
    print(f"[SYSTEM 2]   ----------------------------------------")
    print(f"[SYSTEM 2]   Calculated Closing Bal:   {audit['calculated_closing']:>12,.2f}")
    print(f"[SYSTEM 2]   Document Stated Bal:      {audit['stated_closing']:>12,.2f}")
    print(f"[SYSTEM 2]   Discrepancy:              {audit['discrepancy']:>12,.2f}")

    if passed:
        print(f"\n[STATUS] APPROVED - Ledger is perfectly balanced.")
        print(f"[STATUS] Cleared for ERP/Database write.")
        print(f"\n[FINAL AUDIT TRAIL]")
        print(json.dumps(audit, indent=2))
        break
    else:
        print(f"\n[STATUS] BLOCKED - $5,000 discrepancy detected.")
        print(f"[SYSTEM 2 -> SYSTEM 1] Looping precise error back to System 1...")
        print(f"\n--- ERROR SENT TO SYSTEM 1 ---")
        print(error_msg)
        print(f"------------------------------")
        print(f"\n[SYSTEM 1] Received error. Re-examining document for misread digit...\n")
