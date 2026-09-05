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

result = send_purchase_order_email(
    po_id=5,
    sender_user=user,
    recipient_email='ulaganathank38@gmail.com' # test sending directly to smtp user
)

print("Result of send_purchase_order_email with PDF attachment:")
print(result)
