"""
Forensic Probe 5: Raw OCR/Qwen extraction data for staging id=1009250.
Shows raw OCR text, raw Qwen JSON, and traces each item field's extraction origin.
"""
import json
from ocr_pipeline.models import InvoiceTempOCR

staging = InvoiceTempOCR.objects.get(id=1009250)
ext = staging.extracted_data or {}

print("=== FORENSIC PROBE 5: Raw OCR/Qwen Extraction for id=1009250 ===\n")
print(f"Invoice: {staging.supplier_invoice_no}")
print(f"Validation Status: {staging.validation_status}")

# --- 1. Raw OCR Text ---
print("\n" + "="*70)
print("1. RAW OCR TEXT (_pdf_ocr_text)")
print("="*70)
ocr_text = ext.get('_pdf_ocr_text') or ext.get('_raw_text') or ''
if ocr_text:
    print(ocr_text[:8000])
else:
    print("[NOT FOUND]")

# --- 2. Raw Qwen JSON (before normalization) ---
print("\n" + "="*70)
print("2. RAW QWEN OUTPUT KEYS in extracted_data")
print("="*70)
print(f"Top-level keys: {list(ext.keys())}")

# Look for raw_qwen_output or similar
raw_keys = ['_raw_qwen', 'raw_qwen', '_qwen_raw', 'qwen_output', '_raw_ai_output', 
            '_ai_raw', 'raw_ai', '_raw_extraction', 'raw_extraction', '_source_json',
            '_raw_json', 'raw_response', '_raw_response', '_model_output']
for k in raw_keys:
    if k in ext:
        print(f"\nFound raw key: {k}")
        print(json.dumps(ext[k], indent=2, default=str)[:4000])

# --- 3. Assembled exports ---
print("\n" + "="*70)
print("3. ASSEMBLED EXPORTS (assembled_exports[0])")
print("="*70)
ae = ext.get('assembled_exports') or []
if ae:
    ae0 = ae[0]
    print(f"Keys in assembled_exports[0]: {list(ae0.keys())}")
    ae_items = ae0.get('items', [])
    print(f"\nItems in assembled_exports[0]: {len(ae_items)}")
    for i, itm in enumerate(ae_items):
        print(f"\n  [AE Item {i}]")
        print(json.dumps(itm, indent=4, default=str))
else:
    print("[NOT FOUND]")

# --- 4. Sections structure ---
print("\n" + "="*70)
print("4. SECTIONS STRUCTURE")
print("="*70)
sections = ext.get('sections', {})
print(f"Section keys: {list(sections.keys())}")
sec_items = sections.get('items', [])
print(f"Items in sections: {len(sec_items)}")
for i, itm in enumerate(sec_items):
    print(f"\n  [Section Item {i}]")
    print(json.dumps(itm, indent=4, default=str))

# --- 5. Top-level items ---
print("\n" + "="*70)
print("5. TOP-LEVEL ITEMS (ext['items'])")
print("="*70)
tl_items = ext.get('items', [])
print(f"Items at top level: {len(tl_items)}")
for i, itm in enumerate(tl_items):
    print(f"\n  [TL Item {i}]")
    print(json.dumps(itm, indent=4, default=str))

# --- 6. Pages assembled (_pages_assembled) ---
print("\n" + "="*70)
print("6. PAGES ASSEMBLED (_pages_assembled)")
print("="*70)
pages = ext.get('_pages_assembled') or []
if pages:
    p0 = pages[0]
    print(f"Keys: {list(p0.keys())}")
    p_items = p0.get('items', [])
    print(f"Items: {len(p_items)}")
    for i, itm in enumerate(p_items):
        print(f"\n  [Page Item {i}]")
        print(json.dumps(itm, indent=4, default=str))

# --- 7. Integrity check ---
print("\n" + "="*70)
print("7. INTERNAL CONSISTENCY CHECK for Item[0]")
print("="*70)
all_items = ext.get('items', [])
if not all_items and ae:
    all_items = ae[0].get('items', [])
if not all_items and sec_items:
    all_items = sec_items

if all_items:
    item = all_items[0]
    qty = float(item.get('qty') or item.get('quantity') or 0)
    rate = float(item.get('rate') or item.get('unit_price') or 0)
    dp = float(item.get('discount_percent') or item.get('discount_pct') or 0)
    da = float(item.get('discount_amount') or item.get('discount') or 0)
    tv = float(item.get('taxable_value') or 0)
    amt = float(item.get('amount') or item.get('total_amount') or item.get('line_total') or 0)
    
    gross = qty * rate
    print(f"qty={qty}  rate={rate}  gross={gross:.2f}")
    print(f"discount_percent={dp}  discount_amount={da}")
    print(f"taxable_value={tv}  amount={amt}")
    print(f"")
    print(f"=== CONSISTENCY ANALYSIS ===")
    print(f"gross - taxable_value = {gross - tv:.2f}  (implied discount amount)")
    if gross > 0:
        print(f"implied discount% = {(gross - tv)/gross * 100:.2f}%")
    if tv > 0:
        print(f"taxable_value / gross = {tv/gross:.4f}  (i.e. after {(1-tv/gross)*100:.2f}% discount)")
    print(f"")
    print(f"IF the invoice has 25% discount:")
    print(f"  expected taxable = {gross * 0.75:.2f}")
    print(f"  expected taxable at 25% = {gross * 0.75:.2f}  vs stored taxable_value={tv:.2f}")
    diff_25 = abs(gross * 0.75 - tv)
    print(f"  mismatch with stored value: {diff_25:.2f}")
    print(f"")
    print(f"ALL ITEM KEYS: {list(item.keys())}")

print("\n=== PROBE 5 COMPLETE ===")
