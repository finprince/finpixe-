import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()
from django.db import connection

tenant_id = "2eda0ac6-6af2-493e-8792-bc973fe946b7"

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, ledger_type, ledger, `group`, category, opening_balance, opening_balance_type 
        FROM master_ledgers 
        WHERE tenant_id = %s 
        LIMIT 25
    """, [tenant_id])
    for row in cursor.fetchall():
        print(row)
