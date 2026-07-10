import os
import sys
import time
import uuid
import requests
import django
import logging
import json
import redis
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("E2E_Forensic_Run")

# Setup Django
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState, InvoicePageResult, FinalizedSnapshot, OCRJob

# Configuration
API_URL = "http://localhost:8000"
PDF_PATH = r"C:\Users\ulaganathan\Downloads\New folder (2)\IMG_20260406_0003.pdf"
LOGIN_USER = "admin"
LOGIN_EMAIL = "admin@budstech.com"
LOGIN_PASS = "admin123"

# Redis
r_client = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)), db=0)

def login():
    logger.info("Authenticating with Django backend...")
    url = f"{API_URL}/api/auth/login/"
    payload = {
        "email": LOGIN_EMAIL,
        "username": LOGIN_USER,
        "password": LOGIN_PASS
    }
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        raise ValueError(f"Login failed ({res.status_code}): {res.text}")
    tokens = res.json()
    logger.info("Authentication successful.")
    return tokens['access']

def fetch_db_state(session_id, record_id=None):
    state = {}
    
    # 1. InvoiceTempOCR
    ocr_records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id))
    state['temp_ocr'] = [
        {
            "id": r.id,
            "status": r.status,
            "validation_status": r.validation_status,
            "processed": r.processed,
            "supplier_invoice_no": r.supplier_invoice_no,
            "gstin": r.gstin,
            "vendor_id": r.vendor_id,
            "voucher_id": r.voucher_id
        } for r in ocr_records
    ]
    
    # Resolve record_id if not provided
    if not record_id and ocr_records:
        record_id = str(ocr_records[0].id)
        
    # 2. SessionFinalizationState
    if record_id:
        sfs = SessionFinalizationState.objects.filter(id=str(record_id)).first()
        if sfs:
            state['sfs'] = {
                "id": sfs.id,
                "expected_pages": sfs.expected_pages,
                "completed_pages": sfs.completed_pages,
                "failed_pages": sfs.failed_pages,
                "ai_completed_pages": sfs.ai_completed_pages,
                "snapshot_created": sfs.snapshot_created,
                "ai_complete": sfs.ai_complete,
                "assembly_complete": sfs.assembly_complete,
                "snapshot_complete": sfs.snapshot_complete,
                "materialization_complete": sfs.materialization_complete,
                "terminal_consistency": sfs.terminal_consistency,
                "status": sfs.status
            }
        else:
            state['sfs'] = None
            
        # 3. InvoicePageResult
        iprs = list(InvoicePageResult.objects.filter(record_id=int(record_id)))
        state['page_results'] = [
            {
                "page_number": p.page_number,
                "is_failed": p.is_failed,
                "counted_in_barrier": p.counted_in_barrier
            } for p in iprs
        ]
    else:
        state['sfs'] = None
        state['page_results'] = []
        
    # 4. FinalizedSnapshot
    snapshots = list(FinalizedSnapshot.objects.filter(session_id=session_id))
    state['snapshots'] = [
        {
            "id": s.id,
            "s3_key": s.s3_key,
            "invoice_count": s.invoice_count,
            "finalized_at": str(s.finalized_at)
        } for s in snapshots
    ]
    
    # 5. OCRJob
    ocr_jobs = list(OCRJob.objects.all().order_by('-created_at')[:2])
    state['ocr_jobs'] = [
        {
            "id": j.id,
            "status": j.status,
            "total_files": j.total_files,
            "processed_files": j.processed_files,
            "failed_files": j.failed_files
        } for j in ocr_jobs
    ]
    
    return state, record_id

def fetch_redis_state(session_id, record_id=None):
    state = {}
    if record_id:
        state[f'session:{record_id}'] = {k.decode(): v.decode() for k, v in r_client.hgetall(f"session:{record_id}").items()}
        state[f'finalize_lock:{record_id}'] = r_client.get(f"finalize_lock:{record_id}").decode() if r_client.get(f"finalize_lock:{record_id}") else None
        state[f'active_slots:{record_id}'] = {k.decode(): v.decode() for k, v in r_client.hgetall(f"active_slots:{record_id}").items()}
    state[f'session:{session_id}'] = {k.decode(): v.decode() for k, v in r_client.hgetall(f"session:{session_id}").items()}
    state['worker_heartbeats'] = {k.decode(): v.decode() for k, v in r_client.hgetall("worker_heartbeats").items()}
    return state

def run_test():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    session_id = str(uuid.uuid4())
    
    logger.info(f"Generated Session ID: {session_id}")
    
    # Verify file exists
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"Target PDF file missing at: {PDF_PATH}")
        
    logger.info(f"Starting upload of {PDF_PATH}...")
    
    files = {
        'files': (os.path.basename(PDF_PATH), open(PDF_PATH, 'rb'), 'application/pdf')
    }
    data = {
        'upload_session_id': session_id,
        'voucher_type': 'PURCHASE',
        'upload_type': 'LIVE_TEST'
    }
    
    t_upload = time.time()
    url = f"{API_URL}/api/ocr-staging/"
    res = requests.post(url, headers=headers, files=files, data=data)
    
    if res.status_code not in (200, 201, 202):
        raise ValueError(f"Upload failed ({res.status_code}): {res.text}")
        
    logger.info(f"Upload successful. Response: {res.text}")
    
    timeline = []
    timeline.append({
        "timestamp": datetime.now().isoformat(),
        "event": "UPLOAD_COMPLETED",
        "latency": time.time() - t_upload,
        "db_state": None,
        "redis_state": None
    })
    
    record_id = None
    max_poll_iterations = 60  # 120 seconds max
    poll_interval = 2.0
    
    stalled_at_finalized = 0
    hang_detected = False
    
    for i in range(max_poll_iterations):
        time.sleep(poll_interval)
        
        # Poll endpoint
        poll_url = f"{API_URL}/api/ocr-staging/?upload_session_id={session_id}"
        poll_res = requests.get(poll_url, headers=headers)
        poll_data = poll_res.json() if poll_res.status_code == 200 else {}
        
        # Fetch DB & Redis state
        db_state, record_id = fetch_db_state(session_id, record_id)
        redis_state = fetch_redis_state(session_id, record_id)
        
        status_text = poll_data.get('status', 'unknown')
        progress = poll_data.get('progress_percent', 0)
        row_count = len(poll_data.get('data', []))
        
        logger.info(f"Poll #{i+1}: status={status_text}, progress={progress}%, rows={row_count}, record_id={record_id}")
        
        # Log event in timeline
        timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": f"POLL_{i+1}",
            "status": status_text,
            "progress": progress,
            "db_state": db_state,
            "redis_state": redis_state
        })
        
        # Hang detection
        if db_state.get('sfs') and db_state['sfs']['snapshot_created'] and not db_state['sfs']['snapshot_complete']:
            if stalled_at_finalized == 0:
                stalled_at_finalized = time.time()
                logger.warning("Snapshot created but snapshot_complete is False. Finalize worker convergence check pending...")
            elif time.time() - stalled_at_finalized > 30.0:
                logger.critical("🚨 STALL DETECTED in FINALIZE worker stage! Circular dependency deadlock active.")
                hang_detected = True
                break
        
        if status_text in ('FINALIZED', 'HYDRATION_READY', 'SUCCESS') and progress >= 100.0:
            logger.info("E2E Test completed successfully (or reported finished status).")
            break
            
    # Capture final states on hang or completion
    logger.info("Capturing final diagnostic snapshots...")
    final_db, _ = fetch_db_state(session_id, record_id)
    final_redis = fetch_redis_state(session_id, record_id)
    
    # Save the E2E trace file as JSON
    trace_log = {
        "session_id": session_id,
        "record_id": record_id,
        "hang_detected": hang_detected,
        "timeline": timeline,
        "final_db_state": final_db,
        "final_redis_state": final_redis
    }
    
    trace_path = os.path.join(base_dir, 'scratch', 'e2e_run_trace.json')
    with open(trace_path, 'w') as f:
        json.dump(trace_log, f, indent=2, default=str)
        
    logger.info(f"Forensic run trace successfully saved to {trace_path}")
    print(f"\nFORENSIC RUN TRACE SAVED TO: {trace_path}\n")

if __name__ == '__main__':
    run_test()
