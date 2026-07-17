import os
import django
import sys
sys.path.append(r'd:\finpixe\Ai_Accounting_28\AI-accounting-0.03\backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from accounting.models_voucher_sales import VoucherSalesInvoiceDetails

print("LAST 5 UPDATED VOUCHERS:")
for v in VoucherSalesInvoiceDetails.objects.order_by('-updated_at')[:5]:
    print("-" * 40)
    print(f"Voucher ID: {v.id} | Inv No: {v.sales_invoice_no}")
    print(f"is_ecommerce_operator: {v.is_ecommerce_operator}")
    print(f"third_party_supplier_gstin: '{v.third_party_supplier_gstin}'")
    print(f"amendment_date: {v.amendment_date}")
    print(f"gst_registered: {v.gst_registered}")
    print(f"gstin: '{v.gstin}'")
    print(f"ecommerce_gstin: '{v.ecommerce_gstin}'")
