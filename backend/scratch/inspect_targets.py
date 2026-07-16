"""
INSPECT TARGET CORRUPTED RECORDS
================================
Reads the target records and prints their current extracted_data metadata.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

ids = [1009461, 1009480, 1009527, 1009545, 1009563]
for idx in ids:
    try:
        rec = InvoiceTempOCR.objects.get(id=idx)
        print(f"Record ID: {rec.id} | Invoice No: {rec.supplier_invoice_no} | Status: {rec.status} | Validation Status: {rec.validation_status}")
    except InvoiceTempOCR.DoesNotExist:
        print(f"Record ID: {idx} does not exist!")
