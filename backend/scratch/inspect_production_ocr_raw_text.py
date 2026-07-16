import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

rec = InvoiceTempOCR.objects.filter(id=1009545).first()
if rec:
    print("Record status:", rec.status)
    print("Record supplier_invoice_no:", rec.supplier_invoice_no)
    
    # Let's inspect raw_text
    ext_data = rec.extracted_data or {}
    print("\nKeys in extracted_data:", list(ext_data.keys()))
    
    raw_text = ext_data.get("_raw_text")
    print("\n_raw_text length:", len(raw_text) if raw_text else "None")
    if raw_text:
        print("\n=== _raw_text content ===")
        print(raw_text)
        print("=========================")
else:
    print("Record 1009545 not found.")
