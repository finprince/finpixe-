import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT id, vendor_code, vendor_name, email_address, contact_no, tenant_id FROM vendor_master_basic_details;")
    vendors = cursor.fetchall()
    print("Vendors in DB:")
    for v in vendors:
        print(" ", v)

    cursor.execute("SELECT id, vendor_basic_detail_id, gstin, branch_email, branch_address, city, state, pincode FROM vendor_master_gst_details;")
    gst_details = cursor.fetchall()
    print("\nVendor GST Details / Branches in DB:")
    for g in gst_details:
        print(" ", g)
