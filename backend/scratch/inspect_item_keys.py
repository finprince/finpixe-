"""
PRINT KEY VALUES OF HSN 8210 FOR RECORD 1009545
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

rec = InvoiceTempOCR.objects.get(id=1009545)
items = rec.extracted_data.get("items", [])
for itm in items:
    if "8210" in str(itm.get("hsn_sac") or itm.get("hsn_code") or ""):
        print(f"HSN 8210: {itm}")
