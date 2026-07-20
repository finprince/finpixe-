import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    try:
        cursor.execute("ALTER TABLE gst_reconciliation_gstr3b_reports ADD COLUMN status VARCHAR(20) DEFAULT 'DRAFT'")
    except Exception as e:
        print(e)
        
    try:
        cursor.execute("ALTER TABLE gst_reconciliation_gstr3b_reports ADD COLUMN arn_number VARCHAR(100) NULL")
    except Exception as e:
        print(e)
        
    try:
        cursor.execute("ALTER TABLE gst_reconciliation_gstr3b_reports ADD COLUMN filed_date DATETIME NULL")
    except Exception as e:
        print(e)

print("SUCCESS")
