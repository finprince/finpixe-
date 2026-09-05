import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT id, username, email, company_name, tenant_id FROM users LIMIT 10;")
    users = cursor.fetchall()
    print("Users in DB:")
    for u in users:
        print(" ", u)

    cursor.execute("SELECT id, name, email, gstin FROM tenants LIMIT 10;")
    tenants = cursor.fetchall()
    print("\nTenants in DB:")
    for t in tenants:
        print(" ", t)

    cursor.execute("SELECT id, po_number, vendor_name, email_address, status, created_at, updated_at FROM vendor_transaction_po ORDER BY id DESC LIMIT 5;")
    pos = cursor.fetchall()
    print("\nRecent Purchase Orders:")
    for p in pos:
        print(" ", p)
