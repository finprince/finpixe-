import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from gst_reconciliation.models import GSTR2BInvoice, ReconciliationResult
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from vendors.models import VendorMasterBasicDetail

print("GSTR2BInvoice count:", GSTR2BInvoice.objects.count())
print("ReconciliationResult count:", ReconciliationResult.objects.count())
print("VoucherPurchaseSupplierDetails count:", VoucherPurchaseSupplierDetails.objects.count())
print("VendorMasterBasicDetail count:", VendorMasterBasicDetail.objects.count())

for r in ReconciliationResult.objects.all()[:10]:
    print(r.id, r.status, r.matching_score, r.invoice_2b_id, r.purchase_voucher_id)
