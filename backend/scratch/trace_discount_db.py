import sys
import django
import os
import json

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

qs = InvoiceTempOCR.objects.exclude(extracted_data__isnull=True).order_by('-id')[:10]

print("=" * 80)
print("STAGE 3: OCR Staging Table — discount_percent field audit")
print("=" * 80)

for r in qs:
    d = r.extracted_data or {}
    items = d.get('items') or []
    if not items:
        ae = d.get('assembled_exports') or []
        if ae:
            items = ae[0].get('items') or []

    has_discount = any(
        (it.get('discount_percent') or it.get('discount_pct') or
         it.get('discount_amount') or it.get('discount'))
        for it in items
    )

    print(f"\nRecord id={r.id}  invoice={r.supplier_invoice_no!r}  items={len(items)}  HAS_DISCOUNT={has_discount}")
    for idx, it in enumerate(items[:6]):
        disc_pct = it.get('discount_percent')
        disc_pct2 = it.get('discount_pct')
        disc_amt = it.get('discount_amount')
        tv = it.get('taxable_value')
        rate = it.get('rate')
        qty = it.get('qty')
        desc = str(it.get('description', ''))[:35]
        print(f"  item[{idx}] desc={desc!r}")
        print(f"         discount_percent={disc_pct!r}  discount_pct={disc_pct2!r}  discount_amount={disc_amt!r}")
        print(f"         qty={qty!r}  rate={rate!r}  taxable_value={tv!r}")

    # Show all keys to find any hidden aliases
    if items:
        all_keys = set()
        for it in items:
            all_keys.update(it.keys())
        disc_keys = [k for k in all_keys if 'disc' in k.lower() or 'discount' in k.lower()]
        print(f"  Discount-related keys found: {disc_keys or 'NONE'}")
