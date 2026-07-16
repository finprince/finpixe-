"""
INSPECT SAVED VOUCHERS
======================
Queries the actual database entries for finalized vouchers matching
our target records to verify their saved GST rates.
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails, VoucherPurchaseItem

TARGET_IDS = [1009461, 1009480, 1009527, 1009545, 1009563]

print("=== INSPECTING SAVED VOUCHERS FOR TARGET RECORDS ===")
for r_id in TARGET_IDS:
    rec = InvoiceTempOCR.objects.filter(id=r_id).first()
    if not rec:
        print(f"Record {r_id} not found in InvoiceTempOCR!")
        continue
    
    print(f"\nStaging Record ID: {rec.id} | Supplier Invoice: {rec.supplier_invoice_no}")
    print(f"  Voucher ID: {rec.voucher_id} | Status: {rec.status} | Validation: {rec.validation_status}")
    
    if rec.voucher_id:
        v = VoucherPurchaseSupplierDetails.objects.filter(id=rec.voucher_id).first()
        if not v:
            print(f"  VoucherPurchaseSupplierDetails with ID {rec.voucher_id} not found!")
            continue
        print(f"  Voucher No: {v.purchase_voucher_no} | Date: {v.date}")
        items = list(VoucherPurchaseItem.objects.filter(supplier_details_id=v.id))
        print(f"  Items found: {len(items)}")
        for idx, item in enumerate(items):
            print(f"    Item {idx+1}: {item.item_name}")
            print(f"      Qty: {item.quantity} | Rate: {item.rate} | Taxable: {item.taxable_value}")
            print(f"      GST Rate:  {item.gst_rate}%")
            print(f"      CGST Amt:  {item.cgst_amount} | SGST Amt:  {item.sgst_amount}")
    else:
        print("  No voucher_id is associated with this staging record.")
print("="*60)
