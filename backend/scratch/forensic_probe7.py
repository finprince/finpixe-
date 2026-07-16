"""
Forensic Probe 7: Find what the AI returned BEFORE normalization for staging id=1009250.
Checks the reconciliation state and the exact taxable_value origin.
"""
import json
from ocr_pipeline.models import InvoiceTempOCR

staging = InvoiceTempOCR.objects.get(id=1009250)
ext = staging.extracted_data or {}

print("=== FORENSIC PROBE 7: Pre-normalization AI output ===\n")

# Header totals
print("=== HEADER TOTALS ===")
for k in ['total_taxable_value', 'total_invoice_value', 'total_cgst', 'total_sgst', 'total_igst', 'invoice_total']:
    print(f"  {k}: {ext.get(k)}")

# Find raw/pre/before keys
print("\n=== RAW/PRE-NORMALIZATION KEYS ===")
raw_like = [k for k in sorted(ext.keys()) if any(x in k.lower() for x in ['raw', 'pre', 'orig', 'recon', 'qwen', 'ai_', 'model', 'before'])]
for k in raw_like:
    v = ext[k]
    if isinstance(v, (dict, list)):
        print(f"  {k}: {json.dumps(v, default=str)[:500]}")
    else:
        print(f"  {k}: {repr(v)[:200]}")

# Calculate what the AI must have returned
print("\n=== INFERENCE: WHAT DID AI RETURN? ===")
items = ext.get('items') or []
if items:
    item = items[0]
    qty = item.get('qty', 0)
    rate = item.get('rate', 0)
    dp = item.get('discount_percent', 0)
    da = item.get('discount_amount', 0)
    tv = item.get('taxable_value', 0)
    ta = item.get('total_amount', 0)
    cgst = item.get('cgst', 0)
    sgst = item.get('sgst', 0)
    
    print(f"  stored item: qty={qty} rate={rate} disc_pct={dp} disc_amt={da}")
    print(f"  stored item: taxable_value={tv} total_amount={ta}")
    print(f"  stored item: cgst={cgst} sgst={sgst}")
    
    # The invoice shows: Amount=1946.25, Disc.%=25%
    # If AI set taxable_value = Amount - cgst - sgst:
    tv_from_amount_minus_gst = round(1946.25 - cgst - sgst, 2)
    print(f"\n  IF AI computed taxable_value = Amount - CGST - SGST:")
    print(f"  = 1946.25 - {cgst} - {sgst} = {tv_from_amount_minus_gst}")
    print(f"  Matches stored taxable_value={tv}? {abs(tv_from_amount_minus_gst - float(tv)) < 2}")
    
    # If total_amount = 2297 - round_off = 2296.57, and cgst+sgst = 350.32
    # taxable = 2296.57 - 350.32 = 1946.25... hmm that doesn't match 1597 either
    print(f"\n  Invoice total = 2297.00, cgst={cgst}, sgst={sgst}, round_off=0.43")
    tv_from_total = round(2297.00 - cgst - sgst - 0.43, 2)
    print(f"  IF taxable_value = total - cgst - sgst - roundoff = {tv_from_total}")
    
    print(f"\n  gross = qty*rate = {qty}*{rate} = {float(qty)*float(rate):.2f}")
    
# Check if discount is stored elsewhere
print("\n=== ALL DISCOUNT-RELATED KEYS IN EXT ===")
for k, v in ext.items():
    if 'discount' in str(k).lower() or 'disc' in str(k).lower():
        print(f"  {k}: {v}")

print("\n=== ITEM LINE_ITEMS (raw) ===")
li = ext.get('line_items') or []
for i, itm in enumerate(li):
    print(f"\n  Line Item {i}:")
    for k, v in sorted(itm.items()):
        print(f"    {k}: {v!r}")

# Check forensic log from _forensics dir
print("\n=== FORENSIC LOGS DIR ===")
import os
log_dir = r"c:\108\AI-accounting-0.03\backend\logs\forensic_20260710_150701"
if os.path.exists(log_dir):
    for f in os.listdir(log_dir)[:5]:
        print(f"  {f}")
else:
    print("  [NOT FOUND]")

print("\n=== PROBE 7 COMPLETE ===")
