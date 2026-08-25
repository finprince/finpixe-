import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from accounting.views_voucher_purchase import VoucherPurchaseViewSet
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()

pv = VoucherPurchaseSupplierDetails.objects.filter(supplier_invoice_no='RECO-PART-001').first()
print("Found PV in DB:", pv.id if pv else None, pv.supplier_invoice_no if pv else None, pv.tenant_id if pv else None)

if pv:
    factory = APIRequestFactory()
    request = factory.get(f'/api/vouchers/purchase/{pv.id}/?show_all=true')
    force_authenticate(request, user=user)

    view = VoucherPurchaseViewSet.as_view({'get': 'retrieve'})
    response = view(request, pk=pv.id)

    print("GET Voucher Status Code:", response.status_code)
    print("Response Data:", response.data)
