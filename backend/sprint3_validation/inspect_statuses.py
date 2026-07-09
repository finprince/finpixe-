import os, sys, django
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
django.setup()
from ocr_pipeline.models import InvoiceTempOCR

records = InvoiceTempOCR.objects.filter(upload_session_id='008b2c8b-40c3-4bc6-b13a-8e90011c630b').order_by('id')
print("ID | status | validation_status | vendor_status | supplier_invoice_no | file")
print("-" * 90)
for r in records:
    print(f"{r.id} | {r.status:10s} | {r.validation_status:15s} | {r.vendor_status:10s} | {repr(r.supplier_invoice_no):20s} | {r.file_path[-30:]}")
