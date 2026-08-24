import os
import json
import re
import base64
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = "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"
client = OpenAI()

IMAGE_PATH = r"C:\Users\priya\.gemini\antigravity\brain\28daef6c-1072-44c5-9aec-2f6f2c6ac4ff\.user_uploaded\media_1787250570025.png"

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def call_system1(base64_img, previous_error=None):
    """System 1: LLM reads the blurry bank statement and extracts transactions."""
    error_context = ""
    if previous_error:
        error_context = f"""
IMPORTANT CORRECTION REQUIRED:
In your previous extraction, System 2 (the mathematical firewall) detected this error:
{previous_error}
Please re-examine the document very carefully. Focus on finding and fixing this specific discrepancy.
"""
    prompt = f"""
You are a precise financial data extractor. Look at this bank statement image carefully.

{error_context}

Extract the following and output ONLY valid JSON (no markdown, no explanation):
{{
  "bank_name": "string",
  "currency": "string",
  "opening_balance": float,
  "transactions": [
    {{"date": "string", "description": "string", "debit": float, "credit": float, "balance": float}}
  ],
  "closing_balance": float,
  "total_debits": float,
  "total_credits": float
}}

Rules:
- opening_balance is the balance BEFORE the first transaction
- closing_balance is the balance AFTER the last transaction
- debit values are positive floats (money going out)
- credit values are positive floats (money coming in)
- If a transaction has no debit, use 0.0. If no credit, use 0.0
- Extract ALL transactions visible in the statement
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{base64_img}",
                    "detail": "high"
                }}
            ]
        }],
        temperature=0.0,
        max_tokens=4000
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned empty content (possible safety filter block)")
    print(f"[SYSTEM 1 RAW PREVIEW]: {repr(content[:400])}")
    match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
    json_str = match.group(1) if match else content
    # Fallback: find the outermost JSON object in case LLM added surrounding text
    obj_match = re.search(r'\{.*\}', json_str, re.DOTALL)
    if obj_match:
        json_str = obj_match.group(0)
    return json.loads(json_str.strip())

def run_system2(data):
    """
    System 2: Deterministic Mathematical Firewall.
    Verifies the extracted data with hard math.
    Returns (passed: bool, error_message: str, audit: dict)
    """
    opening = data.get("opening_balance", 0)
    transactions = data.get("transactions", [])
    stated_closing = data.get("closing_balance", 0)

    total_debits = sum(t.get("debit", 0) for t in transactions)
    total_credits = sum(t.get("credit", 0) for t in transactions)
    net_change = total_credits - total_debits
    calculated_closing = round(opening + net_change, 2)
    stated_closing = round(stated_closing, 2)
    discrepancy = round(calculated_closing - stated_closing, 2)

    audit = {
        "opening_balance": opening,
        "total_transactions": len(transactions),
        "total_debits_computed": round(total_debits, 2),
        "total_credits_computed": round(total_credits, 2),
        "net_change": round(net_change, 2),
        "calculated_closing_balance": calculated_closing,
        "stated_closing_balance": stated_closing,
        "discrepancy": discrepancy
    }

    if abs(discrepancy) < 0.02:  # allow 2-cent floating point tolerance
        return True, None, audit
    else:
        error_msg = (
            f"MATH MISMATCH DETECTED.\n"
            f"Opening Balance: {opening}\n"
            f"Total Credits extracted: {round(total_credits, 2)}\n"
            f"Total Debits extracted: {round(total_debits, 2)}\n"
            f"Net Change: {round(net_change, 2)}\n"
            f"System 2 Calculated Closing Balance: {calculated_closing}\n"
            f"Document Stated Closing Balance: {stated_closing}\n"
            f"Discrepancy: {discrepancy}\n"
            f"This means the extracted transactions do not add up to the stated closing balance. "
            f"You may have missed a transaction, misread a debit as a credit, or misread a digit. "
            f"Re-examine carefully and fix the extraction."
        )
        return False, error_msg, audit

# ============================================================
# THE MAIN RIM LOOP
# ============================================================
print("=" * 60)
print("  RIM NEURO-SYMBOLIC GATEWAY — LIVE EXECUTION")
print("  Turkiye Finans Bank Statement | USD")
print("=" * 60)

MAX_RETRIES = 3
b64 = encode_image(IMAGE_PATH)
previous_error = None
data = None

for attempt in range(1, MAX_RETRIES + 1):
    print(f"\n--- ATTEMPT {attempt} ---")
    print(f"[SYSTEM 1] {'Initial extraction...' if attempt == 1 else 'Self-correcting based on System 2 error feedback...'}")

    try:
        data = call_system1(b64, previous_error)
        print(f"[SYSTEM 1] Extracted {len(data.get('transactions', []))} transactions.")
        print(f"[SYSTEM 1] Opening Balance: {data.get('opening_balance')}")
        print(f"[SYSTEM 1] Closing Balance (stated by LLM): {data.get('closing_balance')}")
    except Exception as e:
        print(f"[SYSTEM 1] PARSE ERROR: {e}")
        break

    print(f"\n[SYSTEM 2] Running deterministic math verification...")
    passed, error_msg, audit = run_system2(data)

    print(f"[SYSTEM 2] Opening Balance:           {audit['opening_balance']:>12.2f}")
    print(f"[SYSTEM 2] Total Credits (computed):  {audit['total_credits_computed']:>12.2f}")
    print(f"[SYSTEM 2] Total Debits (computed):   {audit['total_debits_computed']:>12.2f}")
    print(f"[SYSTEM 2] Net Change:                {audit['net_change']:>12.2f}")
    print(f"[SYSTEM 2] ----------------------------------------")
    print(f"[SYSTEM 2] Calculated Closing Bal:    {audit['calculated_closing_balance']:>12.2f}")
    print(f"[SYSTEM 2] Document Stated Bal:       {audit['stated_closing_balance']:>12.2f}")
    print(f"[SYSTEM 2] Discrepancy:               {audit['discrepancy']:>12.2f}")

    if passed:
        print(f"\n[STATUS] APPROVED - Ledger is mathematically balanced.")
        print(f"[STATUS] Safe to write to ERP/Database.")
        break
    else:
        print(f"\n[STATUS] BLOCKED - Discrepancy detected.")
        print(f"[SYSTEM 2 -> SYSTEM 1] Looping error back for self-correction...")
        previous_error = error_msg
        if attempt == MAX_RETRIES:
            print(f"\n[STATUS] FINAL BLOCK - Could not reconcile after {MAX_RETRIES} attempts.")
            print(f"[STATUS] Flagging for human review.")

print("\n" + "=" * 60)
print("  RIM AUDIT TRAIL (for Compliance Record)")
print("=" * 60)
if data:
    print(json.dumps(audit, indent=2))
