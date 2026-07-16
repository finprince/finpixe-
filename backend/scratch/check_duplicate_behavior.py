import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from pending_purchases.models import PendingPurchase
from vendors.vendor_validation_logic import canonicalize_gstin_ocr

print("=== CHECKING TARGET RECORDS STATE ===")
ids = [1009527, 1009528]
for r_id in ids:
    try:
        r = InvoiceTempOCR.objects.get(id=r_id)
        print(f"\nStaging ID: {r.id}")
        print(f"  Supplier Invoice No: {r.supplier_invoice_no}")
        print(f"  GSTIN: {r.gstin}")
        print(f"  Branch: {r.branch}")
        print(f"  Tenant ID: {r.tenant_id}")
        print(f"  Status: {r.status}")
        print(f"  Validation Status: {r.validation_status}")
        print(f"  Processed: {r.processed}")
        print(f"  Voucher ID: {r.voucher_id}")
        
        # Run the duplicate check
        canonical_gst = canonicalize_gstin_ocr(r.gstin or "")
        is_duplicate = VoucherPurchaseSupplierDetails.objects.filter(
            supplier_invoice_no__iexact=r.supplier_invoice_no,
            gstin__iexact=canonical_gst,
            branch__iexact=r.branch,
            tenant_id=r.tenant_id
        ).exists()
        print(f"  Duplicate Check (Strict): {is_duplicate}")
        
        # Let's count vouchers matching this invoice number and gstin in database
        vouchers = VoucherPurchaseSupplierDetails.objects.filter(
            supplier_invoice_no__iexact=r.supplier_invoice_no,
            gstin__iexact=canonical_gst,
            tenant_id=r.tenant_id
        )
        print(f"  Matching Vouchers Count (same inv_no & gstin): {vouchers.count()}")
        for v in vouchers:
            print(f"    Voucher ID: {v.id}, Branch: {v.branch}, Purchase Voucher No: {v.purchase_voucher_no}")
            
    except InvoiceTempOCR.DoesNotExist:
        print(f"Staging ID {r_id} does not exist.")

print("\n=== PENDING PURCHASES ===")
for r_id in ids:
    pps = PendingPurchase.objects.filter(source_scan_row_id=r_id)
    print(f"Staging ID {r_id} has {pps.count()} PendingPurchase rows:")
    for pp in pps:
        print(f"  PP ID: {pp.id}, Status: {pp.pending_purchase_status}, Invoice: {pp.invoice_number}, vendor_status: {pp.vendor_status}, item_status: {pp.item_status}, voucher_status: {pp.voucher_status}")
