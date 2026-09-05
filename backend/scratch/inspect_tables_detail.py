import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection

tables_to_inspect = [
    'customer_master_customer_basicdetails',
    'vendor_master_vendorcreation_basicdetail',
    'inventory_master_inventoryitems',
    'voucher_sales_invoicedetails',
    'voucher_sales_paymentdetails',
    'voucher_purchase_supplier_details',
    'voucher_purchase_supply_inr_details',
    'vouchers'
]

with connection.cursor() as cursor:
    for t in tables_to_inspect:
        cursor.execute(f"DESCRIBE `{t}`")
        cols = [row[0] for row in cursor.fetchall()]
        print(f"\n=== Table: {t} ===")
        print(f"Columns ({len(cols)}): {cols}")
        cursor.execute(f"SELECT * FROM `{t}` LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            row_dict = dict(zip(cols, sample))
            non_nulls = {k: str(v)[:50] for k, v in row_dict.items() if v is not None}
            print(f"Sample non-null values: {non_nulls}")
