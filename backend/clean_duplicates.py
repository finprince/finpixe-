import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from gst_reconciliation.models import GSTR3BReport

reports = GSTR3BReport.objects.all().order_by('-created_at')
seen = set()

deleted_count = 0
for report in reports:
    key = (report.period_month, report.period_year)
    if key in seen:
        report.delete()
        deleted_count += 1
    else:
        seen.add(key)
        
print(f"Deleted {deleted_count} duplicate reports. Kept 1 per month/year.")
