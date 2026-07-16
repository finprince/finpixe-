import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

for rid in [1009527, 1009545]:
    rec = InvoiceTempOCR.objects.filter(id=rid).first()
    if rec:
        print(f"Record {rid} created at: {rec.created_at}")
    else:
        print(f"Record {rid} not found.")
