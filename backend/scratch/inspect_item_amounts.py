import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

for rid in [1009527, 1009545]:
    rec = InvoiceTempOCR.objects.filter(id=rid).first()
    if rec:
        print(f"\n================ RECORD {rid} ================")
        ext = rec.extracted_data or {}
        items = ext.get("items") or []
        for idx, itm in enumerate(items):
            print(f"Item {idx}:")
            for k, v in itm.items():
                if 'rate' in k or 'amt' in k or 'cgst' in k or 'sgst' in k or 'igst' in k or 'taxable' in k or 'amount' in k:
                    print(f"  {k}: {v}")
