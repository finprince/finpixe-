"""
RIM CROSS-DOCUMENT RECONCILIATION — ISOLATED EXTRACTION ARCHITECTURE
Core design principle: System 1 extracts each document in a SEPARATE,
isolated API call. System 2 is the ONLY component that ever sees both
numbers simultaneously. This prevents the LLM from "cooperatively hallucinating"
an agreement between the two documents.
"""

import os, json, re, base64
from PIL import Image, ImageDraw
from openai import OpenAI

os.environ["OPENAI_API_KEY"] = "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"
client = OpenAI()

# ============================================================
# GROUND TRUTH
# Statement 1: Dec 2023  | Opening: 12,500 | Closing: 25,405
# Statement 2: Jan 2024  | Opening must = 25,405 (Statement 1 closing)
# ============================================================
STMT1_OPENING = 12500.00
STMT1_TXNS = [
    {"date": "05.12.2023", "desc": "SWIFT INCOMING - ACME CORP USA",      "debit": 0.00,    "credit": 4500.00},
    {"date": "08.12.2023", "desc": "WIRE TRANSFER - SUPPLIER PAYMENT",     "debit": 1200.00, "credit": 0.00},
    {"date": "12.12.2023", "desc": "SWIFT INCOMING - CLIENT DELTA",        "debit": 0.00,    "credit": 3200.00},
    {"date": "15.12.2023", "desc": "FX CONVERSION USD-TRY",                "debit": 2800.00, "credit": 0.00},
    {"date": "19.12.2023", "desc": "SWIFT INCOMING - GLOBAL TRADERS LTD", "debit": 0.00,    "credit": 6000.00},
    {"date": "22.12.2023", "desc": "BANK FEES AND COMMISSION",             "debit": 45.00,   "credit": 0.00},
    {"date": "26.12.2023", "desc": "WIRE TRANSFER - RENT PAYMENT",        "debit": 1800.00, "credit": 0.00},
]
STMT1_TRUE_CLOSING = round(STMT1_OPENING + sum(t["credit"]-t["debit"] for t in STMT1_TXNS), 2)

STMT2_OPENING = STMT1_TRUE_CLOSING  # Must match Statement 1 closing
STMT2_TXNS = [
    {"date": "02.01.2024", "desc": "SWIFT INCOMING - EXPORT REVENUE",     "debit": 0.00,    "credit": 8500.00},
    {"date": "07.01.2024", "desc": "PAYROLL USD TRANSFER",                 "debit": 3500.00, "credit": 0.00},
    {"date": "11.01.2024", "desc": "SWIFT INCOMING - PARTNER CORP",       "debit": 0.00,    "credit": 2750.00},
    {"date": "15.01.2024", "desc": "FX CONVERSION USD-EUR",               "debit": 4200.00, "credit": 0.00},
    {"date": "18.01.2024", "desc": "SWIFT INCOMING - DIVIDEND PAYMENT",   "debit": 0.00,    "credit": 1500.00},
]
STMT2_TRUE_CLOSING = round(STMT2_OPENING + sum(t["credit"]-t["debit"] for t in STMT2_TXNS), 2)

# ============================================================
# HALLUCINATION: Statement 1, Row 3 — "3200" misread as "3700"
# This corrupts Statement 1's closing balance by +500
# Statement 2's opening will NOT match — caught by System 2
# ============================================================
STMT1_HALLUCINATED_TXNS = [
    {"date": "05.12.2023", "desc": "SWIFT INCOMING - ACME CORP USA",      "debit": 0.00,    "credit": 4500.00},
    {"date": "08.12.2023", "desc": "WIRE TRANSFER - SUPPLIER PAYMENT",     "debit": 1200.00, "credit": 0.00},
    {"date": "12.12.2023", "desc": "SWIFT INCOMING - CLIENT DELTA",        "debit": 0.00,    "credit": 3700.00},  # HALLUCINATION: 3200 -> 3700
    {"date": "15.12.2023", "desc": "FX CONVERSION USD-TRY",                "debit": 2800.00, "credit": 0.00},
    {"date": "19.12.2023", "desc": "SWIFT INCOMING - GLOBAL TRADERS LTD", "debit": 0.00,    "credit": 6000.00},
    {"date": "22.12.2023", "desc": "BANK FEES AND COMMISSION",             "debit": 45.00,   "credit": 0.00},
    {"date": "26.12.2023", "desc": "WIRE TRANSFER - RENT PAYMENT",        "debit": 1800.00, "credit": 0.00},
]
STMT1_HALLUCINATED_CLOSING = round(STMT1_OPENING + sum(t["credit"]-t["debit"] for t in STMT1_HALLUCINATED_TXNS), 2)

# ============================================================
# GENERATE STATEMENT IMAGES
# ============================================================
def generate_statement_image(title, period, opening, txns, closing, path):
    img = Image.new("RGB", (860, 60 + len(txns)*22 + 80), color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0,0,860,55], fill=(20,60,120))
    draw.text((15,8),  "TURKIYE FINANS KATILIM BANKASI - USD ACCOUNT STATEMENT", fill="white")
    draw.text((15,28), f"{title} | Period: {period} | Opening Balance: {opening:,.2f}", fill=(180,220,255))
    y = 62
    draw.rectangle([0,y,860,y+20], fill=(230,236,245))
    draw.text((10,y+3),"Date",         fill="black")
    draw.text((110,y+3),"Description", fill="black")
    draw.text((560,y+3),"Debit",       fill="black")
    draw.text((680,y+3),"Credit",      fill="black")
    draw.text((790,y+3),"Balance",     fill="black")
    y += 24
    bal = opening
    for i,t in enumerate(txns):
        bal = round(bal + t["credit"] - t["debit"], 2)
        bg = (248,248,252) if i%2==0 else (255,255,255)
        draw.rectangle([0,y,860,y+20], fill=bg)
        draw.text((10, y+3), t["date"],                              fill=(50,50,50))
        draw.text((110,y+3), t["desc"][:48],                         fill=(50,50,50))
        draw.text((560,y+3), f"{t['debit']:,.2f}"  if t["debit"]  else "-", fill=(180,30,30))
        draw.text((680,y+3), f"{t['credit']:,.2f}" if t["credit"] else "-", fill=(30,130,30))
        draw.text((790,y+3), f"{bal:,.2f}",                          fill=(30,30,120))
        y += 22
    y += 8
    draw.line([0,y,860,y], fill=(180,180,200))
    y += 6
    draw.text((10,y), f"Closing Balance: {closing:,.2f}", fill=(20,60,120))
    img.save(path)

S1_PATH = r"c:\ast-rim-optimizer\stmt1_dec2023.png"
S2_PATH = r"c:\ast-rim-optimizer\stmt2_jan2024.png"
generate_statement_image("Statement 1 (Dec 2023)", "01.12.2023-31.12.2023",
    STMT1_OPENING, STMT1_HALLUCINATED_TXNS, STMT1_HALLUCINATED_CLOSING, S1_PATH)
generate_statement_image("Statement 2 (Jan 2024)", "01.01.2024-31.01.2024",
    STMT2_OPENING, STMT2_TXNS, STMT2_TRUE_CLOSING, S2_PATH)

# ============================================================
# SYSTEM 1: ISOLATED EXTRACTION (one document per API call)
# ============================================================
def extract_statement_isolated(image_path, label):
    """
    ISOLATED EXTRACTION: System 1 sees ONLY this document.
    It has zero knowledge of any other statement.
    """
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    prompt = """
You are a financial data extractor. Extract ONLY what you see in THIS document.
Do not infer or assume any values. Output ONLY valid JSON:
{
  "opening_balance": float,
  "closing_balance": float,
  "transactions": [
    {"date": "string", "description": "string", "debit": float, "credit": float}
  ]
}
Rules: debit and credit are always positive floats. Use 0.0 if not applicable.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:image/png;base64,{b64}", "detail": "high"}}
        ]}],
        temperature=0.0, max_tokens=2000
    )
    content = response.choices[0].message.content or ""
    match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
    json_str = match.group(1) if match else content
    obj = re.search(r'\{.*\}', json_str, re.DOTALL)
    data = json.loads(obj.group(0).strip() if obj else json_str.strip())
    print(f"[SYSTEM 1 - {label}] Extracted independently.")
    print(f"[SYSTEM 1 - {label}]   Opening : {data.get('opening_balance'):,.2f}")
    print(f"[SYSTEM 1 - {label}]   Closing : {data.get('closing_balance'):,.2f}")
    print(f"[SYSTEM 1 - {label}]   Rows    : {len(data.get('transactions',[]))}")
    return data

# ============================================================
# SYSTEM 2: CROSS-DOCUMENT FIREWALL
# ============================================================
def cross_document_firewall(stmt1_data, stmt2_data):
    """
    System 2 is the ONLY place that sees both statements.
    It compares independently-extracted numbers deterministically.
    """
    s1_closing = round(stmt1_data.get("closing_balance", 0), 2)
    s2_opening = round(stmt2_data.get("opening_balance", 0), 2)
    discrepancy = round(s2_opening - s1_closing, 2)

    audit = {
        "statement1_extracted_closing": s1_closing,
        "statement2_extracted_opening": s2_opening,
        "discrepancy":                  discrepancy,
        "ground_truth_s1_closing":      STMT1_TRUE_CLOSING,
        "ground_truth_s2_opening":      STMT2_OPENING,
        "hallucinated_s1_closing":      STMT1_HALLUCINATED_CLOSING
    }
    if abs(discrepancy) < 0.02:
        return True, audit
    else:
        return False, audit

# ============================================================
# THE RIM CROSS-DOCUMENT LOOP
# ============================================================
print("="*65)
print("  RIM CROSS-DOCUMENT RECONCILIATION")
print("  Isolated Extraction Architecture")
print("="*65)
print(f"\n[GROUND TRUTH]")
print(f"  Statement 1 True Closing:   {STMT1_TRUE_CLOSING:,.2f}")
print(f"  Statement 2 True Opening:   {STMT2_OPENING:,.2f}  (must match)")
print(f"  Hallucinated S1 Closing:    {STMT1_HALLUCINATED_CLOSING:,.2f}  (+500 error from misread digit)")
print(f"\n[DESIGN]")
print(f"  System 1 Call A: sees ONLY Statement 1 image. API call ends.")
print(f"  System 1 Call B: sees ONLY Statement 2 image. Has ZERO knowledge of Call A.")
print(f"  System 2: the ONLY entity that ever sees both numbers. Compares in pure Python.")

print(f"\n{'='*65}")
print(f"  STEP 1: ISOLATED EXTRACTION")
print(f"{'='*65}\n")
stmt1 = extract_statement_isolated(S1_PATH, "Statement 1 (Dec 2023)")
print()
stmt2 = extract_statement_isolated(S2_PATH, "Statement 2 (Jan 2024)")

print(f"\n{'='*65}")
print(f"  STEP 2: SYSTEM 2 CROSS-DOCUMENT FIREWALL")
print(f"{'='*65}\n")
print(f"[SYSTEM 2] Comparing independently extracted values...")
print(f"[SYSTEM 2]   Statement 1 Extracted Closing: {stmt1.get('closing_balance'):,.2f}")
print(f"[SYSTEM 2]   Statement 2 Extracted Opening: {stmt2.get('opening_balance'):,.2f}")

passed, audit = cross_document_firewall(stmt1, stmt2)

print(f"[SYSTEM 2]   ----------------------------------------")
print(f"[SYSTEM 2]   Discrepancy:                    {audit['discrepancy']:,.2f}")
print(f"[SYSTEM 2]   Ground Truth S1 Closing:        {audit['ground_truth_s1_closing']:,.2f}")
print(f"[SYSTEM 2]   Hallucinated S1 Closing was:    {audit['hallucinated_s1_closing']:,.2f}")

if passed:
    print(f"\n[STATUS] APPROVED - Cross-document balances match perfectly.")
else:
    print(f"\n[STATUS] BLOCKED - Cross-document mismatch detected!")
    print(f"[STATUS] Statement 1 closing does NOT equal Statement 2 opening.")
    print(f"[STATUS] A hallucinated digit in Statement 1 has been caught.")
    print(f"[STATUS] The LLM COULD NOT cooperatively hallucinate an agreement")
    print(f"[STATUS] because Statement 2 was extracted in an isolated API call.")
    print(f"[STATUS] Flagging both statements for human review.")

print(f"\n{'='*65}")
print(f"  FULL AUDIT TRAIL")
print(f"{'='*65}")
print(json.dumps(audit, indent=2))
