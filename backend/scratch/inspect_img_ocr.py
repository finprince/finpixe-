import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, OCRJob

print("=== INVENTORIZING OCR RECORDS ===")
records = InvoiceTempOCR.objects.filter(file_path__icontains="IMG_20260406_0003.pdf").order_by('-created_at')
print(f"Found {records.count()} records.")
for r in records:
    print(f"\nID: {r.id}")
    print(f"Created: {r.created_at}")
    print(f"Status: {r.status}")
    print(f"Validation Status: {r.validation_status}")
    print(f"Processed: {r.processed}")
    print(f"Upload Session ID: {r.upload_session_id}")
    print(f"File Path: {r.file_path}")
    print(f"Supplier Invoice No: {r.supplier_invoice_no}")
    ext = r.extracted_data or {}
    print(f"Has Extracted Data: {bool(ext)}")
    if 'error' in ext or 'errors' in ext:
        print(f"Errors: {ext.get('error') or ext.get('errors')}")
    audit = ext.get('gst_audit_trail', {})
    if audit:
        print(f"GST Audit Trail Validation: {audit.get('validation_status')}")
