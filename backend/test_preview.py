import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from gst_reconciliation.models import GSTR3BReport

try:
    report = GSTR3BReport.objects.filter(
        period_month='January', 
        period_year='2024-25'
    ).first()
    if not report:
        report = GSTR3BReport.objects.create(period_month='January', period_year='2024-25')
    print("SUCCESS report created or fetched:", report.id)
    print("status:", report.status)
    print("arn_number:", report.arn_number)
except Exception as e:
    import traceback
    traceback.print_exc()
