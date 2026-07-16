import sys
import os
import json

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.stdout.reconfigure(encoding='utf-8')
import django
django.setup()

from ocr_pipeline.normalize import get_normalized_items
from ocr_pipeline.models import InvoiceTempOCR

r = InvoiceTempOCR.objects.filter(supplier_invoice_no='EIS/25-26/688').order_by('-id').first()
d = r.extracted_data or {}
raw = d.get('_raw_extraction', {})

print("=" * 70)
print("STAGE 4: Simulating get_normalized_items() on _raw_extraction")
print("=" * 70)

result = get_normalized_items(raw, tenant_id=None, layout_type='Layout C')
print(f"get_normalized_items produced {len(result)} items\n")

for idx, it in enumerate(result[:6]):
    desc = str(it.get('description', ''))[:35]
    dp = it.get('discount_percent')
    da = it.get('discount_amount')
    qty = it.get('qty')
    rate = it.get('rate')
    tv = it.get('taxable_value')
    print(f"  item[{idx}] desc={desc!r}")
    print(f"    discount_percent={dp}  discount_amount={da}")
    print(f"    qty={qty}  rate={rate}  taxable_value={tv}")
    print()
