import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from vendors import vendorpo_database as db
from django.db import connection

po = db.get_purchase_order_by_id(5)
if not po:
    print("PO #5 not found.")
    sys.exit(0)

print("PO #5 data:")
for k, v in po.items():
    if k != 'items':
        print(f"  {k}: {v}")

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, vendor_code, vendor_name, email, contact_no 
        FROM vendor_master_vendorcreation_basicdetail 
        WHERE vendor_name = %s;
    """, [po.get('vendor_name')])
    vendor = cursor.fetchone()
    print("\nMatching Vendor from vendor_master_vendorcreation_basicdetail:")
    print(" ", vendor)
