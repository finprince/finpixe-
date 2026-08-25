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
from core.redis_orchestrator import orchestrator
import redis

PDF_PATH = r"C:\Users\ulaganathan\Downloads\New folder (2)\IMG_20260406_0006.pdf"

def main():
    print("=========================================================")
    print("STARTING COMPLETE CLEAN-ROOM CLUSTER E2E TEST")
    print(f"Target PDF: {PDF_PATH}")
    print("=========================================================")

    if not os.path.exists(PDF_PATH):
        print(f"ERROR: PDF file not found at {PDF_PATH}")
        sys.exit(1)

    file_size = os.path.getsize(PDF_PATH)
    with open(PDF_PATH, 'rb') as f:
        file_bytes = f.read()
        file_sha256 = hashlib.sha256(file_bytes).hexdigest()
        reader = pypdf.PdfReader(f)
        page_count = len(reader.pages)

    print(f"File Size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
    print(f"SHA-256: {file_sha256}")
    print(f"Page Count: {page_count}")

    session_id = f"e2e_{int(time.time() * 1000)}"
    upload_url = "http://127.0.0.1:8000/api/bulk-upload/"

    print(f"\n--- 1. EXECUTING PRODUCTION API UPLOAD ---")
    print(f"Upload URL: {upload_url}")
    print(f"Session ID: {session_id}")
    
    t_upload_start = time.time()
    
    with open(PDF_PATH, 'rb') as f:
        files = {'files': ('IMG_20260406_0006.pdf', f, 'application/pdf')}
        data = {
            'upload_session_id': session_id,
            'voucher_type': 'Purchase',
            'upload_type': 'BULK'
        }
        resp = requests.post(upload_url, files=files, data=data)
    
    t_upload_end = time.time()
    upload_duration = t_upload_end - t_upload_start

    print(f"HTTP Status: {resp.status_code}")
    print(f"Upload Duration: {upload_duration:.3f}s")
    print(f"Upload Response JSON: {resp.text}")

    if resp.status_code not in (200, 201, 202):
        print(f"FATAL: Upload failed with status {resp.status_code}")
        sys.exit(1)

    resp_json = resp.json()
    job_id = resp_json.get('job_id')
    print(f"Created Job ID: {job_id}")

    # Inspect Job and Item in DB
    job = BulkInvoiceJob.objects.filter(id=job_id).first()
    item = InvoiceProcessingItem.objects.filter(job_id=job_id).first()
    record_id = item.staging_record_id if item else None
    record = InvoiceTempOCR.objects.filter(id=record_id).first() if record_id else None

    print(f"Item ID: {item.id if item else 'N/A'}")
    print(f"Staging Record ID: {record_id}")
    print(f"Storage Key: {item.file_path if item else 'N/A'}")

    print("\n--- 2. POLLING PIPELINE STAGES IN REAL-TIME ---")
    
    max_wait = 180 # 3 minutes timeout
    t_poll_start = time.time()
    last_status = None
    completed = False

    while time.time() - t_poll_start < max_wait:
        elapsed = time.time() - t_poll_start
        
        # Check DB State
        if record_id:
            record.refresh_from_db()
            auth_state = orchestrator.get_authoritative_session_state(session_id)
            final_state = SessionFinalizationState.objects.filter(id=str(record_id)).first()
            page_results = list(InvoicePageResult.objects.filter(record_id=record_id).values('page_number', 'is_failed', 'created_at'))
            snapshot = FinalizedSnapshot.objects.filter(session_id=session_id).first()
            
            cur_status = f"RecordStatus={record.status} ValStatus={record.validation_status} PagesDone={len(page_results)}/{page_count} Snapshot={'YES' if snapshot else 'NO'}"
            if cur_status != last_status:
                print(f"[{elapsed:.1f}s] {cur_status} | AuthState: expected={auth_state.get('expected_pages')} completed={auth_state.get('completed_pages')} terminal={auth_state.get('terminal')}")
                last_status = cur_status
            
            # Check terminal condition
            if record.status in ['FINALIZED', 'COMPLETED', 'FAILED', 'ERROR'] and (record.processed or record.validation_status):
                print(f"\nPipeline reached terminal state at {elapsed:.2f}s!")
                completed = True
                break
                
        time.sleep(1)

    t_total_end = time.time()
    total_time = t_total_end - t_upload_start

    print(f"\n=========================================================")
    print(f"TOTAL EXECUTION TIME: {total_time:.2f}s")
    print(f"=========================================================")

    # Dump forensic details
    print("\n--- 3. FORENSIC DATABASE STATE CAPTURE ---")
    record.refresh_from_db()
    print(f"InvoiceTempOCR ID: {record.id}")
    print(f"Status: {record.status}")
    print(f"Processed: {record.processed}")
    print(f"Validation Status: {record.validation_status}")
    print(f"Supplier Invoice No: {record.supplier_invoice_no}")
    print(f"GSTIN: {record.gstin}")
    print(f"Vendor ID: {record.vendor_id}")
    print(f"Branch: {record.branch}")
    print(f"Total Amount: {record.total_amount}")
    print(f"Taxable Value: {record.taxable_value}")
    print(f"CGST: {record.cgst_amount}, SGST: {record.sgst_amount}, IGST: {record.igst_amount}")

    # Check Voucher
    vouchers = list(VoucherPurchaseSupplierDetails.objects.filter(
        supplier_invoice_no=record.supplier_invoice_no,
        gstin=record.gstin,
        tenant_id=record.tenant_id
    ))
    print(f"\nMatched Purchase Vouchers in DB: {len(vouchers)}")
    for v in vouchers:
        print(f"  Voucher ID: {v.id} | Purchase Voucher No: {v.purchase_voucher_no} | Date: {v.date} | Vendor: {v.vendor_name}")
        items = list(VoucherPurchaseItem.objects.filter(supplier_details_id=v.id))
        print(f"  Voucher Line Items ({len(items)}):")
        for itm in items:
            print(f"    - Item: {itm.item_name} | Code: {itm.item_code} | HSN: {itm.hsn_sac} | Qty: {itm.quantity} | Rate: {itm.rate} | Taxable: {itm.taxable_value} | GST Rate: {itm.gst_rate}% | CGST: {itm.cgst_amount} | SGST: {itm.sgst_amount} | IGST: {itm.igst_amount} | Total: {itm.invoice_value}")

    # Save full telemetry to scratch json
    forensic_data = {
        "session_id": session_id,
        "job_id": job_id,
        "record_id": record_id,
        "file_hash": file_sha256,
        "upload_duration_s": upload_duration,
        "total_duration_s": total_time,
        "record_state": {
            "status": record.status,
            "processed": record.processed,
            "validation_status": record.validation_status,
            "supplier_invoice_no": record.supplier_invoice_no,
            "gstin": record.gstin,
            "total_amount": str(record.total_amount),
            "taxable_value": str(record.taxable_value),
            "cgst_amount": str(record.cgst_amount),
            "sgst_amount": str(record.sgst_amount),
            "igst_amount": str(record.igst_amount),
            "extracted_data": record.extracted_data
        },
        "pages": [
            {
                "page_number": p.page_number,
                "is_failed": p.is_failed,
                "canonical_payload": p.canonical_payload
            } for p in InvoicePageResult.objects.filter(record_id=record_id)
        ]
    }
    
    with open(os.path.join(current_dir, "e2e_forensic_run1.json"), "w", encoding="utf-8") as f_out:
        json.dump(forensic_data, f_out, indent=2, default=str)
    print(f"\nForensic snapshot saved to scratch/e2e_forensic_run1.json")

if __name__ == '__main__':
    main()
