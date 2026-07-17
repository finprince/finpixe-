import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounting.models import AdvanceAllocation

advs = AdvanceAllocation.objects.all()
print(f"Total AdvanceAllocations: {advs.count()}")
for a in advs:
    print(f"ID: {a.id}, Amount: {a.amount}, Transaction: {a.transaction_id}, Type: {a.transaction.transaction_type if a.transaction else 'None'}, GST Rate: {a.gst_rate}, Date: {a.transaction.date if a.transaction else 'None'}")
