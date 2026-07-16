import os
import sys
import django

# Setup Django first
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from vendors.vendor_validation_logic import canonicalize_gstin_ocr

SESSION_ID = "327c4f6c-882f-43ce-bc5b-67a770142fb7"

print("=== INSPECTING DUPLICATE STATUS OF SESSION RECORDS ===")
records = InvoiceTempOCR.objects.filter(upload_session_id=SESSION_ID, validation_status='DUPLICATE')
print(f"Staging records with DUPLICATE status: {records.count()}")

for r in records:
    print(f"\nStaging ID: {r.id}")
    print(f"  Invoice No: {r.supplier_invoice_no}")
    print(f"  GSTIN: {r.gstin}")
    print(f"  Branch: {r.branch}")
    print(f"  Tenant ID: {r.tenant_id}")
    
    canonical_gst = canonicalize_gstin_ocr(r.gstin or "")
    
    # Let's find matching vouchers in the DB
    matching_vouchers = VoucherPurchaseSupplierDetails.objects.filter(
        supplier_invoice_no__iexact=r.supplier_invoice_no,
        gstin__iexact=canonical_gst,
        branch__iexact=r.branch,
        tenant_id=r.tenant_id
    )
    
    print(f"  Matching ERP Vouchers Count (same inv_no, gstin, branch, tenant): {matching_vouchers.count()}")
    for v in matching_vouchers:
        print(f"    Voucher ID: {v.id}")
        print(f"    Voucher No: {v.purchase_voucher_no}")
        print(f"    Created: {v.created_at if hasattr(v, 'created_at') else 'N/A'}")
        
    if matching_vouchers.count() == 0:
        # Check without branch just in case
        matching_no_branch = VoucherPurchaseSupplierDetails.objects.filter(
            supplier_invoice_no__iexact=r.supplier_invoice_no,
            gstin__iexact=canonical_gst,
            tenant_id=r.tenant_id
        )
        print(f"  Matching ERP Vouchers Count (without branch): {matching_no_branch.count()}")
        for v in matching_no_branch:
            print(f"    Voucher ID: {v.id} | Branch: {v.branch} | Voucher No: {v.purchase_voucher_no}")
