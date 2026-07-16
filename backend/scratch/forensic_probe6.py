"""
Forensic Probe 6: Find the raw Qwen/AI extraction output BEFORE normalization.
Checks _raw_text, _lineage, _forensics, and the line_items field in DB.
"""
import json
from ocr_pipeline.models import InvoiceTempOCR

staging = InvoiceTempOCR.objects.get(id=1009250)
ext = staging.extracted_data or {}

print("=== FORENSIC PROBE 6: Pre-normalization Qwen output ===\n")

# --- _lineage: usually tracks what the raw AI returned ---
print("=== _lineage ===")
lin = ext.get('_lineage') or {}
print(json.dumps(lin, indent=2, default=str)[:4000])

# --- _forensics ---
print("\n=== _forensics ===")
foren = ext.get('_forensics') or {}
print(json.dumps(foren, indent=2, default=str)[:4000])

# --- line_items (may have the pre-normalization list) ---
print("\n=== line_items ===")
li = ext.get('line_items') or []
for i, itm in enumerate(li):
    print(f"\n  Line Item [{i}]:")
    print(json.dumps(itm, indent=4, default=str))

# --- _raw_text (full, not truncated) ---
print("\n=== _raw_text (first 3000 chars) ===")
raw_txt = ext.get('_raw_text') or ''
print(raw_txt[:3000])

# --- _doc_validation ---
print("\n=== _doc_validation ===")
dv = ext.get('_doc_validation') or {}
print(json.dumps(dv, indent=2, default=str)[:2000])

# --- Look for other DB model fields that may have raw data ---
print("\n=== InvoiceTempOCR MODEL FIELDS ===")
print(f"  raw_extraction: {getattr(staging, 'raw_extraction', '<<ATTR NOT EXISTS>>')}")
print(f"  raw_ai_output: {getattr(staging, 'raw_ai_output', '<<ATTR NOT EXISTS>>')}")
print(f"  qwen_output: {getattr(staging, 'qwen_output', '<<ATTR NOT EXISTS>>')}")
print(f"  page_data: {getattr(staging, 'page_data', '<<ATTR NOT EXISTS>>')}")
print(f"  raw_items: {getattr(staging, 'raw_items', '<<ATTR NOT EXISTS>>')}")
print(f"  items (field): {getattr(staging, 'items', '<<ATTR NOT EXISTS>>')}")

# --- Check all model field names ---
print("\n=== ALL MODEL FIELDS ===")
print([f.name for f in staging._meta.fields])

# --- The CRITICAL question: what is stored as total_amount vs taxable_value in item?
print("\n=== ITEM FIELD ANALYSIS ===")
items = ext.get('items') or []
for i, item in enumerate(items):
    print(f"\nItem[{i}] ALL FIELDS:")
    for k, v in sorted(item.items()):
        print(f"  {k}: {v!r}")

print("\n=== PROBE 6 COMPLETE ===")
