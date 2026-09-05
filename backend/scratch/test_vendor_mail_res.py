import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from core.models import User
from vendors.po_mail_service import send_purchase_order_email, get_vendor_email_from_master
from vendors import vendorpo_database as db

po_data = db.get_purchase_order_by_id(5)
vendor_email = get_vendor_email_from_master(po_data)
print("Vendor email resolved from master:", vendor_email)

user = User.objects.filter(username='aashiq').first()
result = send_purchase_order_email(po_id=5, sender_user=user)
print("Result:")
print(result)
