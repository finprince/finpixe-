import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from pending_purchases.models import PendingPurchase
from pending_purchases.views import PendingPurchaseSerializer

# Get the records from screenshot
inv_nos = ['VMT25-26/1A7', 'UMT25-26/079', 'UMT25-26/091']
for inv in inv_nos:
    pp = PendingPurchase.objects.filter(invoice_number__iexact=inv).first()
    if pp:
        data = PendingPurchaseSerializer(pp).data
        print(f"Invoice: {inv}")
        print(f"  API vendor_name: {repr(data.get('vendor_name'))}")
        print(f"  API vendor_gstin: {repr(data.get('vendor_gstin'))}")
        print(f"  API vendor_status: {repr(data.get('vendor_status'))}")
        print(f"  API voucher_status: {repr(data.get('voucher_status'))}")
        print()

# Also check OCR staging API for these records
print("=== OCR Staging (SmartInvoiceUploadModal data source) ===")
from ocr_pipeline.models import InvoiceTempOCR
from ocr_pipeline.views import CleanOCRStagingView

# Simulate _map_record_to_ui_row
view = CleanOCRStagingView()
for inv in inv_nos:
    pp = PendingPurchase.objects.filter(invoice_number__iexact=inv).first()
    if pp:
        staging = InvoiceTempOCR.objects.filter(id=pp.source_scan_row_id).first()
        if staging:
            result = view._map_record_to_ui_row(staging)
            print(f"Invoice: {inv}")
            print(f"  OCR API vendor_name: {repr(result.get('vendor_name'))}")
            print(f"  OCR API vendor_status: {repr(result.get('vendor_status'))}")
            print(f"  OCR API validationStatus: {repr(result.get('validationStatus'))}")
            print(f"  OCR API status: {repr(result.get('status'))}")
            print()
