"""
CLEAN-ROOM END-TO-END FORENSIC RUN
==================================
This script automates the complete upload, extraction, normalization,
validation, and finalization workflow using the active start_cluster.py workers.
It prints detailed traces of the target invoice 3049/25-26 at each stage.
"""
import os
import sys
import time
import uuid
import django

# Setup Django
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import Client
from core.models import User
from ocr_pipeline.models import InvoiceTempOCR, InvoicePageResult, OCRJob, SessionFinalizationState, AICache
from vouchers.models import BulkInvoiceJob
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

PDF_PATH = r"C:\Users\ulaganathan\Downloads\New folder (2)\IMG_20260406_0003.pdf"
TENANT_ID = "2eda0ac6-6af2-493e-8792-bc973fe946b7"

def main():
    print("=" * 80)
    print("STARTING CLEAN-ROOM END-TO-END FORENSIC RUN")
    print("=" * 80)

    # 1. Retrieve user and generate auth token
    try:
        user = User.objects.get(username='admin')
        print(f"[*] Authenticated as user: '{user.username}' for tenant: '{user.tenant_id}'")
    except User.DoesNotExist:
        print("[!] Error: admin user not found.")
        return

    # Patch tenant verification helper
    patcher = patch('core.tenant.validate_tenant_access', return_value=(True, None))
    patcher.start()

    token = RefreshToken.for_user(user)
    access_token = str(token.access_token)

    # Setup client
    client = Client()

    # Generate upload session
    session_id = str(uuid.uuid4())
    print(f"[*] Generated Upload Session ID: {session_id}")

    # ── STAGE 1: UPLOAD API INGESTION ──
    print("\n--- [STAGE 1] POSTing file to Bulk Upload API ---")
    t0_upload = time.time()
    with open(PDF_PATH, 'rb') as f:
        response = client.post(
            '/api/bulk-upload/',
            {
                'files': f,
                'upload_session_id': session_id,
                'voucher_type': 'Purchase',
                'upload_type': 'BULK'
            },
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )
    t1_upload = time.time()
    
    print(f"Response status: {response.status_code}")
    res_data = response.json() if response.status_code == 200 else {}
    print(f"Response payload: {res_data}")
    print(f"Upload API duration: {t1_upload - t0_upload:.3f} seconds")
    
    job_id = res_data.get('job_id')
    if not job_id:
        print("[!] Ingestion failed, no job ID returned.")
        return

    # ── STAGE 2: POLLING WORKER FLEET INGESTION & PIPELINE CONVERGENCE ──
    print("\n--- [STAGE 2] Polling SQS Workers & Pipeline Convergence ---")
    t0_poll = time.time()
    max_poll_seconds = 180
    completed = False
    
    while time.time() - t0_poll < max_poll_seconds:
        # Check bulk job status
        job = BulkInvoiceJob.objects.filter(id=job_id).first()
        status = job.status if job else "UNKNOWN"
        processed_pages = job.processed_pages if job else 0
        total_pages = job.total_pages if job else 0
        
        # Check active session records
        recs = InvoiceTempOCR.objects.filter(upload_session_id=session_id)
        recs_count = recs.count()
        processed_recs = recs.filter(processed=True).count()
        
        print(f"  [T+{time.time()-t0_poll:.1f}s] Job Status: {status} | Pages: {processed_pages}/{total_pages} | DB Records: {recs_count} (processed={processed_recs})")
        
        # Check orchestrator session status
        from core.redis_orchestrator import orchestrator
        auth_state = orchestrator.get_authoritative_session_state(session_id)
        expected_pages = auth_state.get('expected_pages', 0)
        completed_pages = auth_state.get('completed_pages', 0)
        failed_pages = auth_state.get('failed_pages', 0)
        snap_done = auth_state.get('snapshot_complete', False)
        mat_done = auth_state.get('materialization_complete', False)
        
        print(f"    Orchestrator: expected={expected_pages} completed={completed_pages} failed={failed_pages} snap_complete={snap_done} mat_complete={mat_done}")
        
        if status in ['COMPLETED', 'FAILED'] or (expected_pages > 0 and int(completed_pages) + int(failed_pages) == int(expected_pages) and snap_done and mat_done):
            print("[*] Pipeline convergence reached!")
            completed = True
            break
            
        time.sleep(5)
        
    if not completed:
        print("[!] Timeout waiting for pipeline convergence.")
        return

    # Let's locate the record for the target invoice
    target_rec = InvoiceTempOCR.objects.filter(
        upload_session_id=session_id,
        extracted_data__payload__invoice_no='3049/25-26'
    ).first()
    if not target_rec:
        # Fallback to search by supplier_invoice_no
        target_rec = InvoiceTempOCR.objects.filter(
            upload_session_id=session_id,
            supplier_invoice_no='3049/25-26'
        ).first()

    if not target_rec:
        # Search by raw text / vendor
        target_rec = InvoiceTempOCR.objects.filter(
            upload_session_id=session_id,
            extracted_data__payload__vendor_name__icontains='OM MURUGA'
        ).first()

    if not target_rec:
        print("[!] Target invoice 3049/25-26 not found in this session staging records!")
        print("Available records in this session:")
        for r in recs:
            print(f"  id={r.id} | invoice={r.supplier_invoice_no} | status={r.status} | vs={r.validation_status}")
        return

    print(f"\n[*] FOUND TARGET INVOICE: id={target_rec.id} | invoice={target_rec.supplier_invoice_no} | status={target_rec.status} | vs={target_rec.validation_status}")

    # ── STAGE 3: PROGRAMMATIC FINALIZE & SAVE ──
    print("\n--- [STAGE 3] Programmatic Finalize & Save View Call ---")
    t0_finalize = time.time()
    response_finalize = client.post(
        '/api/ocr-staging-finalize/',
        {
            'upload_session_id': session_id,
        },
        content_type='application/json',
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )
    t1_finalize = time.time()
    
    print(f"Finalize response status: {response_finalize.status_code}")
    finalize_res = response_finalize.json()
    print(f"Finalize payload: {finalize_res}")
    print(f"Finalize duration: {t1_finalize - t0_finalize:.3f} seconds")

    # Re-fetch target record
    target_rec.refresh_from_db()
    print(f"\nPost-Finalize Target Record Status: status={target_rec.status} | vs={target_rec.validation_status}")
    if target_rec.extracted_data:
        trail = target_rec.extracted_data.get('gst_audit_trail', {})
        print(f"GST Audit Trail: {trail}")

    print("\n" + "=" * 80)
    print("CLEAN-ROOM END-TO-END FORENSIC RUN COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
