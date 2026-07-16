import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

r = InvoiceTempOCR.objects.get(id=1009527)
print("=== OCR RAW TEXT ===")
print(r.ocr_raw_text)
print("\n=== EXTRACTED_DATA _raw_text ===")
print(r.extracted_data.get('_raw_text', ''))
print("\n=== EXTRACTED_DATA _pdf_ocr_text ===")
print(r.extracted_data.get('_pdf_ocr_text', ''))
