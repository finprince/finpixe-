import sys
import os
import json

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.stdout.reconfigure(encoding='utf-8')
import django
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from ocr_pipeline.normalize import get_normalized_items

# Reprocess staging records to apply the backend normalize.py fix
invoice_numbers = ['EIS/25-26/688', 'EIS/25-26/698', 'EIS/25-26/926', 'EIS/25-26/934', 'EIS/25-26/957']
records = InvoiceTempOCR.objects.filter(supplier_invoice_no__in=invoice_numbers)

print("=" * 80)
print("RE-PROCESSING EXISTING INVOICES TO APPLY FIXED NORMALIZATION")
print("=" * 80)

for r in records:
    d = r.extracted_data or {}
    raw = d.get('_raw_extraction', {})
    if not raw:
        print(f"No _raw_extraction for record id={r.id} invoice={r.supplier_invoice_no!r}, skipping.")
        continue

    # Re-normalize using get_normalized_items
    layout_type = d.get('_validation_metadata', {}).get('layout_type', 'Layout C')
    norm_items = get_normalized_items(raw, tenant_id=None, layout_type=layout_type)
    
    # Update both data.items and data.line_items
    d['items'] = norm_items
    d['line_items'] = norm_items
    
    r.extracted_data = d
    r.save(update_fields=['extracted_data'])
    
    print(f"Successfully re-normalized and updated record id={r.id} invoice={r.supplier_invoice_no!r}")
    print(f"  Item count: {len(norm_items)}")
    for idx, it in enumerate(norm_items[:3]):
        print(f"    item[{idx}] name={it.get('description')[:30]!r} discount_percent={it.get('discount_percent')} discount_amount={it.get('discount_amount')}")
    print()
