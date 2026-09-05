import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from core.models import User
from vendors.po_mail_service import send_purchase_order_email

user = User.objects.filter(username='aashiq').first() or User.objects.first()
print("User found:", user.username if user else None, user.email if user else None)

result = send_purchase_order_email(po_id=5, sender_user=user)
print("Result of send_purchase_order_email for PO #5:")
print(result)
