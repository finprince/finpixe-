import os
import sys
import time
import requests
import json
import hashlib
import pypdf

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState, InvoicePageResult, FinalizedSnapshot
from vouchers.models import BulkInvoiceJob, InvoiceProcessingItem
from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails, VoucherPurchaseItem, VoucherPurchaseSupplyINRDetails
from pending_purchases.models import PendingPurchase
from core.redis_orchestrator import orchestrator

PDF_PATH = r"C:\Users\ulaganathan\Downloads\New folder (2)\IMG_20260406_0006.pdf"

def main():
    print("=========================================================")
    print("DUPLICATE / IDEMPOTENCY TEST (RUN 2 - SAME PDF)")
    print(f"Target PDF: {PDF_PATH}")
    print("=========================================================")

    # 1. Capture Pre-Run DB Counts
    counts_before = {
        "BulkInvoiceJob": BulkInvoiceJob.objects.count(),
        "InvoiceProcessingItem": InvoiceProcessingItem.objects.count(),
        "InvoiceTempOCR": InvoiceTempOCR.objects.count(),
        "SessionFinalizationState": SessionFinalizationState.objects.count(),
        "InvoicePageResult": InvoicePageResult.objects.count(),
        "FinalizedSnapshot": FinalizedSnapshot.objects.count(),
        "PendingPurchase": PendingPurchase.objects.count(),
        "VoucherPurchaseSupplierDetails": VoucherPurchaseSupplierDetails.objects.count(),
        "VoucherPurchaseItem": VoucherPurchaseItem.objects.count()
    }
    print("Pre-Duplicate Counts:")
    for k, v in counts_before.items():
        print(f"  {k}: {v}")

    session_id = f"e2e_dup_{int(time.time() * 1000)}"
    upload_url = "http://127.0.0.1:8000/api/bulk-upload/"

    print(f"\n--- 1. UPLOADING SAME PDF (Session: {session_id}) ---")
    t_upload_start = time.time()
    with open(PDF_PATH, 'rb') as f:
        files = {'files': ('IMG_20260406_0006.pdf', f, 'application/pdf')}
        data = {
            'upload_session_id': session_id,
            'voucher_type': 'Purchase',
            'upload_type': 'BULK'
        }
        resp = requests.post(upload_url, files=files, data=data)
    
    upload_duration = time.time() - t_upload_start
    print(f"HTTP Status: {resp.status_code}")
    print(f"Upload Response JSON: {resp.text}")

    if resp.status_code not in (200, 201, 202):
        print(f"Upload returned status {resp.status_code}")
        # Could be duplicate rejection at upload API gate
        return

    resp_json = resp.json()
    job_id = resp_json.get('job_id')
    job = BulkInvoiceJob.objects.filter(id=job_id).first()
    item = InvoiceProcessingItem.objects.filter(job_id=job_id).first()
    record_id = item.staging_record_id if item else None
    record = InvoiceTempOCR.objects.filter(id=record_id).first() if record_id else None

    print(f"Job ID: {job_id} | Staging Record ID: {record_id}")

    print("\n--- 2. POLLING PIPELINE STAGES FOR DUPLICATE RUN ---")
    max_wait = 180
    t_poll_start = time.time()
    last_status = None

    while time.time() - t_poll_start < max_wait:
        elapsed = time.time() - t_poll_start
        if record_id:
            record.refresh_from_db()
            auth_state = orchestrator.get_authoritative_session_state(session_id)
            final_state = SessionFinalizationState.objects.filter(id=str(record_id)).first()
            page_results = list(InvoicePageResult.objects.filter(record_id=record_id).values('page_number', 'is_failed', 'created_at'))
            snapshot = FinalizedSnapshot.objects.filter(session_id=session_id).first()
            
            cur_status = f"RecordStatus={record.status} ValStatus={record.validation_status} PagesDone={len(page_results)}/2 Snapshot={'YES' if snapshot else 'NO'}"
            if cur_status != last_status:
                print(f"[{elapsed:.1f}s] {cur_status} | AuthState: expected={auth_state.get('expected_pages')} completed={auth_state.get('completed_pages')} terminal={auth_state.get('terminal')}")
                last_status = cur_status
            
            if record.status in ['FINALIZED', 'COMPLETED', 'FAILED', 'ERROR'] and (record.processed or record.validation_status):
                print(f"\nDuplicate run reached terminal state at {elapsed:.2f}s!")
                break
        time.sleep(1)

    t_total_end = time.time()
    total_time = t_total_end - t_upload_start

    print(f"\n=========================================================")
    print(f"DUPLICATE RUN TOTAL TIME: {total_time:.2f}s")
    print(f"=========================================================")

    # Capture Post-Run DB Counts
    counts_after = {
        "BulkInvoiceJob": BulkInvoiceJob.objects.count(),
        "InvoiceProcessingItem": InvoiceProcessingItem.objects.count(),
        "InvoiceTempOCR": InvoiceTempOCR.objects.count(),
        "SessionFinalizationState": SessionFinalizationState.objects.count(),
        "InvoicePageResult": InvoicePageResult.objects.count(),
        "FinalizedSnapshot": FinalizedSnapshot.objects.count(),
        "PendingPurchase": PendingPurchase.objects.count(),
        "VoucherPurchaseSupplierDetails": VoucherPurchaseSupplierDetails.objects.count(),
        "VoucherPurchaseItem": VoucherPurchaseItem.objects.count()
    }
    print("Post-Duplicate Counts Comparison:")
    for k in counts_before.keys():
        diff = counts_after[k] - counts_before[k]
        print(f"  {k}: Before={counts_before[k]}, After={counts_after[k]} (Delta: +{diff})")

    record.refresh_from_db()
    print(f"\nDuplicate Staging Record Details:")
    print(f"  ID: {record.id}")
    print(f"  Status: {record.status}")
    print(f"  Validation Status: {record.validation_status}")
    print(f"  Processed: {record.processed}")

    # Export Run 2 forensic data
    dup_forensic = {
        "session_id": session_id,
        "job_id": job_id,
        "record_id": record_id,
        "counts_before": counts_before,
        "counts_after": counts_after,
        "record_state": {
            "status": record.status,
            "validation_status": record.validation_status,
            "processed": record.processed,
            "supplier_invoice_no": record.supplier_invoice_no,
            "gstin": record.gstin,
            "extracted_data": record.extracted_data
        }
    }
    with open(os.path.join(current_dir, "forensic_run2_duplicate.json"), "w", encoding="utf-8") as f_out:
        json.dump(dup_forensic, f_out, indent=2, default=str)
    print("Exported Run 2 forensic data to scratch/forensic_run2_duplicate.json")

if __name__ == '__main__':
    main()
