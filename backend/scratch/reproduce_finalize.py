"""
reproduce_finalize.py

This script programmatically calls OCRStagingFinalizeView.post using Django's Test Client
with the 'admin' user, and captures the execution timing, response body, response code,
and prints any logs/exceptions.
"""
import os
import sys
import time
import uuid

# Ensure backend directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.test import Client
from core.models import User
from ocr_pipeline.models import InvoiceTempOCR

# The upload session ID from the previous run
SESSION_ID = "4387be16-f770-44f4-ba15-d663ebb2cd66"

def main():
    print(f"=== REPRODUCING FINALIZE & SAVE FOR SESSION: {SESSION_ID} ===")
    
    # 1. Retrieve the admin user
    try:
        user = User.objects.get(username='admin')
        print(f"User retrieved: {user.username} (tenant: {user.branch_id})")
    except User.DoesNotExist:
        print("Error: admin user not found.")
        sys.exit(1)

    # Mock validate_tenant_access to bypass the App 'core' doesn't have a 'Branch' model bug
    from unittest.mock import patch
    patcher = patch('core.tenant.validate_tenant_access', return_value=(True, None))
    patcher.start()

    # Generate JWT token using rest_framework_simplejwt
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(user)
    access_token = str(token.access_token)

    # 2. Setup Django Test Client
    client = Client()

    # Verify how many records are in the session and what status they are
    records = InvoiceTempOCR.objects.filter(upload_session_id=SESSION_ID)
    print(f"Staging records count in this session: {records.count()}")
    for r in records:
        print(f"  id={r.id} | invoice={r.supplier_invoice_no} | status={r.status} | vs={r.validation_status} | processed={r.processed}")

    # 3. Call the POST finalize request and measure timing
    print("\n=== SENDING POST /api/ocr-staging-finalize/ ===")
    start_time = time.time()
    
    response = client.post(
        '/api/ocr-staging-finalize/',
        {
            'upload_session_id': SESSION_ID,
        },
        content_type='application/json',
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    print(f"\nHTTP Response Status Code: {response.status_code}")
    print(f"Time taken: {elapsed:.3f} seconds")
    print(f"HTTP Response Body:")
    print(response.content.decode())

if __name__ == '__main__':
    main()
