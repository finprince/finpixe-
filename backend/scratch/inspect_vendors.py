import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from vendors.models import VendorMasterBasicDetail
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails

print("VendorMasterBasicDetail fields:", [f.name for f in VendorMasterBasicDetail._meta.fields])
print("VoucherPurchaseSupplierDetails fields:", [f.name for f in VoucherPurchaseSupplierDetails._meta.fields])
