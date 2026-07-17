import os, sys, django
sys.path.append(r'd:\finpixe\Ai_Accounting_28\AI-accounting-0.03\backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from accounting.models_voucher_sales import VoucherSalesInvoiceDetails

print("Checking schema...")
for field in VoucherSalesInvoiceDetails._meta.fields:
    if 'ecommerce' in field.name:
        print(f"{field.name}: {field.get_internal_type()}")
