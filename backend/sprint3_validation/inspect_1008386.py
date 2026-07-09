import os, sys, django
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
django.setup()
from ocr_pipeline.models import InvoiceTempOCR
r = InvoiceTempOCR.objects.get(id=1008386)
print(r.extracted_data.get('_pdf_ocr_text').encode('ascii', errors='replace').decode('ascii'))
