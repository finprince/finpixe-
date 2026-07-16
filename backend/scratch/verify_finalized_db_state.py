import os
import sys
import django

# Setup Django first
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from pending_purchases.models import PendingPurchase
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails

print("=== VERIFYING DATABASE STATE FOR FINALIZED RECORD ===")
rec_id = 1009530
r = InvoiceTempOCR.objects.filter(id=rec_id).first()

if r:
    print(f"Staging Record id={r.id}:")
    print(f"  status: {r.status}")
    print(f"  validation_status: {r.validation_status}")
    print(f"  processed: {r.processed}")
    print(f"  voucher_id: {r.voucher_id}")
    
    # Check manual purchase voucher
    if r.voucher_id:
        v = VoucherPurchaseSupplierDetails.objects.filter(id=r.voucher_id).first()
        if v:
            print(f"  Voucher exists in VoucherPurchaseSupplierDetails:")
            print(f"    purchase_voucher_no: {v.purchase_voucher_no}")
            print(f"    supplier_invoice_no: {v.supplier_invoice_no}")
            print(f"    branch: {v.branch}")
            
    # Check pending purchase queue record
    pp = PendingPurchase.objects.filter(source_scan_row_id=r.id).first()
    if pp:
        print(f"  PendingPurchase record:")
        print(f"    pending_purchase_status: {pp.pending_purchase_status}")
        print(f"    resolved_at: {pp.resolved_at}")
        print(f"    review_payload: {pp.review_payload}")
else:
    print(f"Record {rec_id} not found!")
