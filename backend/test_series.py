import sys
import os
sys.path.append('.')

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from customerportal.database import CustomerMastersSalesOrder
for so in CustomerMastersSalesOrder.objects.values("id", "series_name", "current_number", "prefix", "suffix", "required_digits"):
    print(so)
