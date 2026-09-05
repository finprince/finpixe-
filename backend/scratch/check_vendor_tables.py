import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT id, vendor_code, vendor_name, email, contact_no, tenant_id FROM vendor_master_vendorcreation_basicdetail;")
    vendors = cursor.fetchall()
    print("Vendors in vendor_master_vendorcreation_basicdetail:")
    for v in vendors:
        print(" ", v)

    cursor.execute("SHOW TABLES LIKE 'vendor%';")
    tables = cursor.fetchall()
    print("\nVendor tables in DB:")
    for t in tables:
        print(" ", t)
