import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from ocr_pipeline.views import CleanOCRStagingView
from pending_purchases.models import PendingPurchase

view = CleanOCRStagingView()

# Get the exact records from screenshot
inv_nos = ['VMT25-26/1A7', 'UMT25-26/079', 'UMT25-26/091']
for inv in inv_nos:
    pp = PendingPurchase.objects.filter(invoice_number__iexact=inv).first()
    if pp:
        staging = InvoiceTempOCR.objects.filter(id=pp.source_scan_row_id).first()
        if staging:
            ext = staging.extracted_data or {}
            print(f"\n=== Invoice: {inv} | Staging ID: {staging.id}")
            print(f"  ext.vendor_name = {repr(ext.get('vendor_name'))}")
            print(f"  ext.canonical_vendor_name = {repr(ext.get('canonical_vendor_name'))}")
            print(f"  ext.raw_vendor_name = {repr(ext.get('raw_vendor_name'))}")
            print(f"  ext.bill_from = {repr(ext.get('bill_from', ''))[:80]}")
            print(f"  staging.validation_status = {repr(staging.validation_status)}")
            print(f"  staging.vendor_id = {repr(staging.vendor_id)}")
            print(f"  staging.vendor_status = {repr(staging.vendor_status)}")
            
            # Simulate _map_record_to_ui_row
            result = view._map_record_to_ui_row(staging)
            print(f"\n  MAPPED RESULT:")
            print(f"  result.vendor_name = {repr(result.get('vendor_name'))}")
            print(f"  result.vendor_status = {repr(result.get('vendor_status'))}")
            print(f"  result.validationStatus = {repr(result.get('validationStatus'))}")
            print(f"  result.vendor_id = {repr(result.get('vendor_id'))}")

print("\n\n=== PENDING PURCHASE SERIALIZER RESULT ===")
from pending_purchases.views import PendingPurchaseSerializer
for inv in inv_nos:
    pp = PendingPurchase.objects.filter(invoice_number__iexact=inv).first()
    if pp:
        data = PendingPurchaseSerializer(pp).data
        print(f"Invoice: {inv}")
        print(f"  SERIALIZED vendor_name: {repr(data.get('vendor_name'))}")
        print(f"  SERIALIZED vendor_gstin: {repr(data.get('vendor_gstin'))}")
