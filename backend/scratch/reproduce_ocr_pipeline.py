"""
reproduce_ocr_pipeline.py

This script programmatically uploads the test invoice PDF using Django's Test Client
with the 'admin' user, and then polls the InvoiceTempOCR status until the background workers
running on SQS process the page.
"""
import os
import sys
import time
import uuid

import os
import sys
import uuid

# Ensure backend directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.test import Client
from core.models import User
from ocr_pipeline.models import InvoiceTempOCR, OCRJob

PDF_PATH = r"C:\Users\ulaganathan\Downloads\New folder (2)\IMG_20260406_0003.pdf"

def main():
    print(f"=== UPLOADING INVOICE PROGRAMMATICALLY ===")
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF path not found at {PDF_PATH}")
        sys.exit(1)

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
    print(f"Generated JWT Access Token: {access_token[:30]}...")

    # 2. Setup Django Test Client
    client = Client()

    # Generate a unique upload session ID
    session_id = str(uuid.uuid4())
    print(f"Generated upload session ID: {session_id}")

    # 3. Perform the POST upload request
    with open(PDF_PATH, 'rb') as f:
        response = client.post(
            '/api/ocr-staging/',
            {
                'files': [f],
                'voucher_type': 'PURCHASE',
                'upload_type': 'DIRECT',
                'upload_session_id': session_id,
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

    print(f"HTTP Response Status Code: {response.status_code}")
    print(f"HTTP Response Body: {response.content.decode()}")

    if response.status_code not in [200, 202]:
        print("Upload failed.")
        sys.exit(1)

    # 4. Poll the InvoiceTempOCR table to wait for extraction completion
    print("\n=== POLLING FOR OCR & EXTRACTION COMPLETION ===")
    start_time = time.time()
    completed = False
    
    while time.time() - start_time < 300: # Wait up to 5 minutes
        records = InvoiceTempOCR.objects.filter(upload_session_id=session_id)
        if records.exists():
            record = records.first()
            print(f"[{int(time.time() - start_time)}s] Record ID: {record.id} | Status: {record.status} | Validation Status: {record.validation_status}")
            
            # Let's inspect if status is terminal (FINALIZED, FAILED, COMPLETED, etc.)
            if record.status in ['FINALIZED', 'FAILED', 'COMPLETED', 'ERROR']:
                print(f"Terminal state reached in {int(time.time() - start_time)}s!")
                completed = True
                break
        else:
            print(f"[{int(time.time() - start_time)}s] No record found in DB yet...")
            
        time.sleep(5)

    if not completed:
        print("Timeout waiting for OCR pipeline to complete.")
        sys.exit(1)

    # 5. Fetch final state of all records in this session
    print("\n=== FINAL DB RECORDS IN SESSION ===")
    records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id))
    for r in records:
        print(f"\nStaging ID: {r.id}")
        print(f"File Path: {r.file_path}")
        print(f"File Hash: {r.file_hash}")
        print(f"Status: {r.status}")
        print(f"Validation Status: {r.validation_status}")
        print(f"Supplier Invoice No: {r.supplier_invoice_no}")
        print(f"GSTIN: {r.gstin}")
        print(f"Vendor Status: {r.vendor_status}")
        print(f"Vendor ID: {r.vendor_id}")
        print(f"Voucher ID: {r.voucher_id}")
        print(f"Processed: {r.processed}")
        
        # Print items count
        ext = r.extracted_data or {}
        items = ext.get('items', []) or ext.get('line_items', [])
        print(f"Items count: {len(items)}")
        if items:
            print(f"First item: {items[0]}")
        
        # Check if audit trail contains failures
        audit = ext.get('gst_audit_trail', {})
        print(f"GST Audit Trail: {audit}")

if __name__ == '__main__':
    main()
