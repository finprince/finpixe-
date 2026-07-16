"""
Verification of created vouchers and ledger entries.
"""
import os
import sys
import django

# Setup Django
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails, VoucherPurchaseItem, VoucherPurchaseDueDetails
from ocr_pipeline.models import InvoiceTempOCR
from django.db import connection

def main():
    print("=== VERIFYING TARGET VOUCHER STATE ===")
    
    # Check staging records for 3049/25-26
    staging_recs = InvoiceTempOCR.objects.filter(supplier_invoice_no='3049/25-26')
    print(f"Staging records count: {staging_recs.count()}")
    for r in staging_recs:
        print(f"  ID: {r.id} | Status: {r.status} | VS: {r.validation_status} | Processed: {r.processed}")
        if r.extracted_data:
            print(f"    GST Audit Trail: {r.extracted_data.get('gst_audit_trail')}")
            
    # Check if a voucher exists
    vouchers = VoucherPurchaseSupplierDetails.objects.filter(supplier_invoice_no='3049/25-26')
    print(f"\nCreated vouchers count: {vouchers.count()}")
    for v in vouchers:
        print(f"  Voucher No: {v.purchase_voucher_no} | Date: {v.date} | Normalized Inv No: {v.normalized_invoice_no}")
        print(f"  Vendor Name: {v.vendor_name} | GSTIN: {v.gstin} | Branch: {v.branch}")
        
        # Print items
        items = VoucherPurchaseItem.objects.filter(voucher_id=v.id)
        print(f"  Items count: {items.count()}")
        for i in items:
            print(f"    Desc: {i.description} | HSN: {i.hsn_sac} | Qty: {i.qty} | Rate: {i.rate} | Taxable: {i.taxable_value}")
            print(f"    CGST: {i.cgst_rate}% ({i.cgst}) | SGST: {i.sgst_rate}% ({i.sgst}) | IGST: {i.igst_rate}% ({i.igst})")
            
        # Due details
        due = getattr(v, 'due_details', None)
        if due:
            print(f"  Due details: total_tax={due.total_tax} | round_off={due.round_off} | grand_total={due.grand_total}")
            
if __name__ == '__main__':
    main()
