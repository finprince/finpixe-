import os
import django
import sys
sys.path.append(r'd:\finpixe\Ai_Accounting_28\AI-accounting-0.03\backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from accounting.models_voucher_sales import VoucherSalesInvoiceDetails

# Get the latest edited voucher
v = VoucherSalesInvoiceDetails.objects.order_by('-updated_at').first()
print(f"Voucher ID: {v.id}")
print(f"is_ecommerce_operator: {v.is_ecommerce_operator}")
print(f"third_party_supplier_gstin: {v.third_party_supplier_gstin}")
print(f"amendment_date: {v.amendment_date}")
print(f"gst_registered: {v.gst_registered}")
print(f"gstin: {v.gstin}")
print(f"customer_name: {v.customer_name}")
print(f"sales_invoice_no: {v.sales_invoice_no}")
print(f"ecommerce_gstin: {v.ecommerce_gstin}")
