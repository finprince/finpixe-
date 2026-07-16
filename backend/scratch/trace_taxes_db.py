import sys
import django
import os
import json

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

# Focus on invoice EIS/25-26/688
r = InvoiceTempOCR.objects.filter(supplier_invoice_no='EIS/25-26/688').order_by('-id').first()
if not r:
    print("Record EIS/25-26/688 not found!")
    sys.exit(1)

d = r.extracted_data or {}
print(f"Record ID: {r.id}")
print(f"Invoice Number: {r.supplier_invoice_no}")
print(f"Vendor Name: {r.vendor_name if hasattr(r, 'vendor_name') else d.get('vendor_name')}")
print(f"Validation Status: {r.validation_status}")

print("\n--- HEADER TAX FIELDS ---")
header_keys = [
    'cgst', 'sgst', 'igst', 'total_cgst', 'total_sgst', 'total_igst',
    'total_taxable_value', 'taxable_value', 'total_amount', 'total_invoice_value'
]
for k in header_keys:
    print(f"  Header {k}: {d.get(k)} (raw extraction: {d.get('_raw_extraction', {}).get('header', {}).get(k)})")

print("\n--- LINE ITEMS TAX FIELDS ---")
items = d.get('items', [])
raw_items = d.get('_raw_extraction', {}).get('items', [])

print(f"Normalized items count: {len(items)}")
print(f"Raw extraction items count: {len(raw_items)}")

for idx, (it, raw_it) in enumerate(zip(items[:4], raw_items[:4])):
    print(f"\nItem {idx}: {it.get('description', '')[:30]}")
    fields = [
        'gst_rate', 'gstRate', 'tax_rate',
        'cgst_rate', 'cgst_amount', 'cgst',
        'sgst_rate', 'sgst_amount', 'sgst',
        'igst_rate', 'igst_amount', 'igst',
        'cess_rate', 'cess_amount', 'cess',
        'taxable_value', 'amount', 'invoice_value', 'total_amount'
    ]
    print("  Normalized keys:")
    for f in fields:
        if f in it:
            print(f"    {f}: {it.get(f)}")
    print("  Raw extraction keys:")
    for f in fields:
        if f in raw_it:
            print(f"    {f}: {raw_it.get(f)}")
