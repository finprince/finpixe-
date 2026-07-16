import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

TARGET_IDS = [1009545, 1009546, 1009528, 1009527, 1009461]

for rid in TARGET_IDS:
    try:
        r = InvoiceTempOCR.objects.get(id=rid)
        print(f"\n=======================================================")
        print(f"RECORD ID: {r.id} | Inv No: {r.supplier_invoice_no}")
        print(f"Has ocr_raw_text: {r.ocr_raw_text is not None} (len={len(r.ocr_raw_text) if r.ocr_raw_text else 0})")
        if r.ocr_raw_text:
            print("--- OCR TEXT ---")
            print(r.ocr_raw_text[:1500])
        ext = r.extracted_data or {}
        print(f"Has _raw_extraction: {'_raw_extraction' in ext}")
        print(f"Has _raw_text in extracted_data: {'_raw_text' in ext}")
        if ext.get('_raw_text'):
            print("--- _raw_text in extracted_data ---")
            print(ext['_raw_text'][:1500])
    except Exception as e:
        print(f"Error for ID {rid}: {e}")
