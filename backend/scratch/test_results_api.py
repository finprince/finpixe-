import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from gst_reconciliation.views import GSTReconciliationViewSet
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()

factory = APIRequestFactory()
request = factory.get('/api/gst/reconciliation/results/?month=January&year=2024-25')
force_authenticate(request, user=user)

view = GSTReconciliationViewSet.as_view({'get': 'results'})
response = view(request)

print("Status Code:", response.status_code)
print("Summary:", response.data.get('summary'))
print("Results Count:", len(response.data.get('results', [])))

counts_by_status = {}
for r in response.data.get('results', []):
    s = r.get('status')
    counts_by_status[s] = counts_by_status.get(s, 0) + 1

print("Counts in results list:", counts_by_status)
