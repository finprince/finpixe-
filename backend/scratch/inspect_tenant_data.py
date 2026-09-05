import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection

tenant_id = "2eda0ac6-6af2-493e-8792-bc973fe946b7"

with connection.cursor() as cursor:
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    
    print("Tables with tenant rows:")
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{t}` WHERE tenant_id = %s", [tenant_id])
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"  {t}: {count} rows")
        except Exception:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM `{t}`")
                count = cursor.fetchone()[0]
                if count > 0 and any(k in t for k in ['customer', 'vendor', 'sales', 'purchase', 'voucher', 'ledger', 'item', 'inventory', 'transaction', 'gst']):
                    print(f"  {t} (no tenant_id col): {count} rows total")
            except Exception:
                pass
