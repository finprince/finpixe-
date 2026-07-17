import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

client = APIClient()
client.force_authenticate(user=user)

endpoints = [
    '/api/masters/ledgers/',
    '/api/customerportal/customer-master/',
    '/api/vendors/basic-details/',
    '/api/masters/hierarchy/'
]

for url in endpoints:
    res = client.get(url)
    print(f"URL: {url} | Status: {res.status_code}")
    if res.status_code != 200:
        print(res.content.decode('utf-8')[:500])
