import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from core.models import Tenant

User = get_user_model()
for u in User.objects.all():
    print("User:", u.id, u.username, getattr(u, 'tenant_id', None), getattr(u, 'branch_id', None))

print("Tenants:", list(Tenant.objects.values('id', 'name') if 'Tenant' in locals() else []))
print("Distinct voucher tenant_ids:", list(VoucherPurchaseSupplierDetails.objects.values_list('tenant_id', flat=True).distinct()))
