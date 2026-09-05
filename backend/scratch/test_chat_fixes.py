"""
Test Kiki Chat UX and Intent Tailoring Fixes
"""
import os
import sys
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from core.kiki.kernel import ai_kernel
from core.models import Tenant

AUDIT_TENANT = "2eda0ac6-6af2-493e-8792-bc973fe946b7"

class MockUser:
    def __init__(self, tenant_id=AUDIT_TENANT):
        self.is_authenticated = True
        self.tenant_id = str(tenant_id)
        self.company_id = str(tenant_id)
        self.id = "test_ux_user"
        self.role = "Admin"
        self.is_superuser = False

u = MockUser()

queries = [
    # 1. Count & Conversational Queries
    ("1. Count Query", "How many items are there in inventory?"),
    ("2. List Query", "Show inventory items"),
    ("3. Value Query", "What is my inventory value?"),
    ("4. Sales Summary", "How much are my sales?"),
    ("5. Purchases Summary", "How much are my purchases?"),
    ("6. Receivables Summary", "What are my receivables?"),
    ("7. Payables Summary", "What are my payables?"),
    ("8. GST Summary", "What is my GST liability?"),
    ("9. Profit & Loss", "What is my profit?"),
    # Conversational messages
    ("10. Greeting", "hi"),
    ("11. Gratitude", "thanks"),
    ("12. Affirmation", "okay"),
    ("13. Smalltalk/Affirmation", "ohhhh okok"),
]

print("=" * 90)
print("TESTING KIKI CHAT RESPONSE FORMATTING & CONVERSATIONAL INTENTS")
print("=" * 90)

for label, query in queries:
    res = ai_kernel.process_request(query, u, context_data={"session_id": f"sess_{uuid.uuid4().hex[:6]}"})
    print(f"\n[{label}] Query: '{query}'")
    print(f"  - Intent: {res.get('intent')} | Domain: {res.get('domain')}")
    print(f"  - Reply:\n{res.get('reply')}")
    print("-" * 90)

print("\nALL TEST QUERIES EXECUTED SUCCESSFULLY!")
