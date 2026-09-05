import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.core.mail import get_connection

try:
    connection = get_connection()
    connection.open()
    print("SMTP connection opened successfully!")
    connection.close()
    print("SMTP connection closed.")
except Exception as e:
    print(f"SMTP Connection failed: {e}")
