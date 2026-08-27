import sys
import os

sys.path.insert(0, os.path.abspath('backend'))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SHOW TABLES")
    all_tables = [r[0] for r in cursor.fetchall()]
    
    print("\n--- ALL SALES, VOUCHER, INVOICE & CUSTOMER TABLES IN MYSQL FINPIXE DB ---")
    targets = [t for t in all_tables if any(k in t for k in ['sale', 'voucher', 'invoice', 'customer', 'entry'])]
    
    for t in sorted(targets):
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{t}`")
            cnt = cursor.fetchone()[0]
            if cnt > 0:
                print(f"  [HAS DATA] {t}: {cnt} rows")
            else:
                print(f"  [EMPTY]    {t}: 0 rows")
        except Exception as e:
            print(f"  [ERROR]    {t}: {e}")
