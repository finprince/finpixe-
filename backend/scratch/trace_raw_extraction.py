import sys
import django
import os
import json

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

r = InvoiceTempOCR.objects.filter(supplier_invoice_no='EIS/25-26/688').order_by('-id').first()
if not r:
    r = InvoiceTempOCR.objects.order_by('-id').first()

print(f"Record id={r.id}  invoice={r.supplier_invoice_no!r}")
d = r.extracted_data or {}

# Inspect _raw_extraction — the pre-normalization AI output
raw_ext = d.get('_raw_extraction')
print(f"\n_raw_extraction type: {type(raw_ext)}")
if isinstance(raw_ext, str):
    try:
        raw_ext = json.loads(raw_ext)
        print("_raw_extraction is a JSON string — parsed successfully")
    except Exception as e:
        print(f"  Could not parse as JSON: {e}")
        print(f"  First 500 chars: {raw_ext[:500]}")
        raw_ext = None

if isinstance(raw_ext, dict):
    print(f"_raw_extraction keys: {list(raw_ext.keys())}")
    items_raw = raw_ext.get('items') or raw_ext.get('line_items') or []
    print(f"\nRaw extraction items count: {len(items_raw)}")
    for idx, it in enumerate(items_raw[:6]):
        print(f"\n  raw_item[{idx}] keys: {list(it.keys()) if isinstance(it, dict) else type(it)}")
        if isinstance(it, dict):
            print(f"    description: {it.get('description','')[:40]!r}")
            print(f"    qty: {it.get('quantity') or it.get('qty')}  rate: {it.get('rate')}")
            print(f"    taxable_value: {it.get('taxable_value')}")
            print(f"    discount_percent: {it.get('discount_percent')!r}")
            print(f"    discount_amount:  {it.get('discount_amount')!r}")
            disc_keys = {k: v for k, v in it.items() if 'disc' in k.lower()}
            print(f"    Discount keys: {disc_keys}")
elif raw_ext is not None:
    print(f"_raw_extraction content (first 800 chars): {str(raw_ext)[:800]}")
else:
    print("_raw_extraction is None or missing")

# Also check _forensics key
forensics = d.get('_forensics')
if forensics:
    print(f"\n_forensics type: {type(forensics)}")
    if isinstance(forensics, dict):
        print(f"_forensics keys: {list(forensics.keys())[:20]}")
