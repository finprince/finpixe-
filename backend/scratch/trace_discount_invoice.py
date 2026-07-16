import sys
import django
import os
import json

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

# Focus on invoice EIS/25-26/688 - the one with 45%, 55%, 30%, 25% discounts
r = InvoiceTempOCR.objects.filter(supplier_invoice_no='EIS/25-26/688').order_by('-id').first()
if not r:
    # Try partial match
    qs = InvoiceTempOCR.objects.filter(supplier_invoice_no__icontains='688').order_by('-id')
    print(f"No exact match for 'EIS/25-26/688'. Partial matches: {[x.supplier_invoice_no for x in qs[:5]]}")
    r = qs.first()

if not r:
    print("Record not found. Showing last record instead.")
    r = InvoiceTempOCR.objects.order_by('-id').first()

print(f"Examining record id={r.id}  invoice={r.supplier_invoice_no!r}")
print(f"Status: {r.status}  validation_status: {r.validation_status}")

d = r.extracted_data or {}
print(f"\nTop-level keys in extracted_data: {list(d.keys())}")

# Show assembled_exports structure
ae = d.get('assembled_exports') or []
if ae:
    print(f"\nassembled_exports count: {len(ae)}")
    ae0 = ae[0]
    print(f"assembled_exports[0] keys: {list(ae0.keys())}")
    ae_items = ae0.get('items') or []
    print(f"\nassembled_exports[0].items count: {len(ae_items)}")
    for idx, it in enumerate(ae_items[:6]):
        print(f"\n  AE item[{idx}] ALL KEYS: {list(it.keys())}")
        print(f"    description: {it.get('description','')[:40]!r}")
        print(f"    qty: {it.get('qty')}  rate: {it.get('rate')}  taxable_value: {it.get('taxable_value')}")
        print(f"    discount_percent: {it.get('discount_percent')!r}")
        print(f"    discount_amount:  {it.get('discount_amount')!r}")
        print(f"    discount_pct:     {it.get('discount_pct')!r}")
        print(f"    discount:         {it.get('discount')!r}")
        # Also look for any other discount-like key
        disc_keys = {k: v for k, v in it.items() if 'disc' in k.lower() or 'discount' in k.lower()}
        if disc_keys:
            print(f"    ALL discount keys: {disc_keys}")

# Also look at top-level items
items = d.get('items') or []
if items:
    print(f"\n\nTop-level items count: {len(items)}")
    for idx, it in enumerate(items[:6]):
        print(f"\n  item[{idx}] ALL KEYS: {list(it.keys())}")
        print(f"    description: {it.get('description','')[:40]!r}")
        print(f"    discount_percent: {it.get('discount_percent')!r}")
        print(f"    discount_amount:  {it.get('discount_amount')!r}")
        disc_keys = {k: v for k, v in it.items() if 'disc' in k.lower()}
        if disc_keys:
            print(f"    ALL discount keys: {disc_keys}")

# Check for any raw_extraction or pre-normalization data
print(f"\n\nLooking for raw extraction data...")
for key in ['raw_extraction', 'raw_response', 'pre_normalization', 'original_extraction', 'raw_items']:
    if d.get(key):
        print(f"  Found key: {key}")
        val = d[key]
        if isinstance(val, dict):
            print(f"    keys: {list(val.keys())}")
        elif isinstance(val, list):
            print(f"    length: {len(val)}")
