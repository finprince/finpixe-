import sys
import django
import os
import json

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.stdout.reconfigure(encoding='utf-8')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

# Find records that have NON-ZERO discount to see if any ever got through
qs = InvoiceTempOCR.objects.exclude(extracted_data__isnull=True).order_by('-id')[:200]

print("=" * 80)
print("STAGE 3: Searching ALL recent staging records for non-zero discount_percent")
print("=" * 80)

found_with_discount = []

for r in qs:
    d = r.extracted_data or {}
    items = d.get('items') or []
    if not items:
        ae = d.get('assembled_exports') or []
        if ae:
            items = ae[0].get('items') or []
    for idx, it in enumerate(items):
        dp = it.get('discount_percent')
        da = it.get('discount_amount')
        if (dp and float(dp) > 0) or (da and float(da) > 0):
            found_with_discount.append({
                'id': r.id,
                'invoice': r.supplier_invoice_no,
                'item_idx': idx,
                'desc': str(it.get('description', ''))[:40],
                'discount_percent': dp,
                'discount_amount': da,
                'qty': it.get('qty'),
                'rate': it.get('rate'),
                'taxable_value': it.get('taxable_value'),
            })

if found_with_discount:
    print(f"Found {len(found_with_discount)} items with non-zero discount across staging:\n")
    for e in found_with_discount[:30]:
        print(f"  id={e['id']} invoice={e['invoice']!r} item[{e['item_idx']}] desc={e['desc']!r}")
        print(f"    discount_percent={e['discount_percent']}  discount_amount={e['discount_amount']}")
        print(f"    qty={e['qty']}  rate={e['rate']}  taxable_value={e['taxable_value']}")
else:
    print("NO staging records in the last 200 have non-zero discount_percent OR discount_amount.")
    print("This means discounts are being lost BEFORE or DURING OCR normalization/storage.")
    print()

# Now check what the raw extracted_data looks like for records where taxable < qty*rate
# (which is characteristic of having a discount applied)
print("\n" + "=" * 80)
print("DETECTING IMPLICIT DISCOUNTS: taxable_value < qty * rate")
print("=" * 80)

implicit_disc = []
for r in qs[:30]:
    d = r.extracted_data or {}
    items = d.get('items') or []
    if not items:
        ae = d.get('assembled_exports') or []
        if ae:
            items = ae[0].get('items') or []
    for idx, it in enumerate(items):
        qty = float(it.get('qty') or 0)
        rate = float(it.get('rate') or 0)
        tv = float(it.get('taxable_value') or 0)
        if qty > 0 and rate > 0 and tv > 0:
            gross = round(qty * rate, 4)
            if gross > 0 and tv < gross * 0.99:  # at least 1% difference
                implied_pct = round((gross - tv) / gross * 100, 2)
                implicit_disc.append({
                    'id': r.id,
                    'invoice': r.supplier_invoice_no,
                    'item_idx': idx,
                    'desc': str(it.get('description',''))[:35],
                    'qty': qty, 'rate': rate, 'gross': gross, 'tv': tv,
                    'implied_disc_pct': implied_pct,
                    'stored_disc_pct': it.get('discount_percent'),
                })

if implicit_disc:
    print(f"Found {len(implicit_disc)} items where taxable_value < qty*rate (discount implied):\n")
    for e in implicit_disc[:20]:
        print(f"  id={e['id']} invoice={e['invoice']!r} item[{e['item_idx']}] {e['desc']!r}")
        print(f"    qty={e['qty']}  rate={e['rate']}  gross={e['gross']}  taxable={e['tv']}")
        print(f"    implied_discount_pct={e['implied_disc_pct']}%  stored_discount_pct={e['stored_disc_pct']}")
else:
    print("No implicit discount detected (all taxable_values match qty*rate or are 0).")
