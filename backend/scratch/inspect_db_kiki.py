import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection
from core.models import Tenant, User
from accounting.models_voucher_sales import VoucherSalesInvoiceDetails
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
from customerportal.database import CustomerMaster
from vendors.models import Vendor
from inventory.models import InventoryItem

print("--- DB INSPECTION ---")
with connection.cursor() as cursor:
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Total tables in DB: {len(tables)}")

print(f"Tenants count: {Tenant.objects.count()}")
for t in Tenant.objects.all()[:5]:
    print(f"Tenant: ID={t.id}, Name={t.name}, IsActive={t.is_active}")

print(f"Users count: {User.objects.count()}")
for u in User.objects.all()[:5]:
    print(f"User: ID={u.id}, Username={u.username}, Tenant={getattr(u, 'tenant_id', None)}")

print(f"Sales Vouchers count: {VoucherSalesInvoiceDetails.objects.count()}")
for s in VoucherSalesInvoiceDetails.objects.all()[:3]:
    print(f"Sales: ID={s.id}, Invoice={s.sales_invoice_no}, Customer={s.customer_name}, Date={s.date}, Total={getattr(s, 'total', None)}, Tenant={s.tenant_id}")

print(f"Purchase Vouchers count: {VoucherPurchaseSupplierDetails.objects.count()}")
for p in VoucherPurchaseSupplierDetails.objects.all()[:3]:
    print(f"Purchase: ID={p.id}, Voucher={p.purchase_voucher_no}, Vendor={p.vendor_name}, Date={p.date}, Tenant={p.tenant_id}")

print(f"Customers count: {CustomerMaster.objects.count()}")
for c in CustomerMaster.objects.all()[:3]:
    print(f"Customer: Code={c.customer_code}, Name={c.customer_name}, Tenant={c.tenant_id}")

print(f"Vendors count: {Vendor.objects.count()}")
for v in Vendor.objects.all()[:3]:
    print(f"Vendor: Code={v.vendor_code}, Name={v.vendor_name}, Tenant={v.tenant_id}")

print(f"Inventory Items count: {InventoryItem.objects.count()}")
for i in InventoryItem.objects.all()[:3]:
    print(f"Item: Code={i.item_code}, Name={i.item_name}, Rate={i.rate}, OpeningStock={i.opening_stock}, Tenant={i.tenant_id}")
