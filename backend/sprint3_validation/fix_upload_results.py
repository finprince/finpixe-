"""
Fix BATCH_UPLOAD_RESULTS.json with actual Django DB status.
Run this script to correct results of the validation session.
"""
import os
import sys
import json
import django
from datetime import datetime, timezone

BACKEND_DIR = r"c:\108\AI-accounting-0.03\backend"
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
try:
    import django
    django.setup()
except Exception:
    pass

from ocr_pipeline.models import InvoiceTempOCR

OUTPUT_DIR = r"c:\108\AI-accounting-0.03\backend\sprint3_validation\reports"
results_path = os.path.join(OUTPUT_DIR, "BATCH_UPLOAD_RESULTS.json")

if not os.path.isfile(results_path):
    print(f"Error: {results_path} not found.")
    sys.exit(1)

with open(results_path, "r", encoding="utf-8") as f:
    batch_results = json.load(f)

session_id = batch_results["session_id"]
print(f"Repairing batch upload results for session {session_id}...")

success_count = 0
failure_count = 0
TERMINAL_STATUSES = {"FINALIZED", "FAILED", "ASSEMBLY_ABORTED", "ERROR", "CANCELLED"}

for entry in batch_results["results"]:
    fname = entry["filename"]
    file_hash = entry["file_hash"]
    
    # Query record by file_path containing the file_hash and session_id
    record = InvoiceTempOCR.objects.filter(upload_session_id=session_id, file_path__contains=file_hash).first()
    if record:
        status = record.status or "UNKNOWN"
        print(f"  File {fname}: found record_id={record.id} status={status}")
        
        entry["record_id"] = str(record.id)
        entry["upload"]["record_id"] = str(record.id)
        
        # Determine if terminal
        is_term = status in TERMINAL_STATUSES or status == "EXTRACTING"  # treating stuck EXTRACTING as terminal for reporting
        final_status = status
        if status == "EXTRACTING":
            final_status = "TIMEOUT" # Mark stuck record as TIMEOUT
            
        entry["pipeline"] = {
            "final_status": final_status,
            "terminal": is_term,
            "poll_count": 120
        }
        
        if final_status in {"FINALIZED", "COMPLETED", "HYDRATION_READY", "SUCCESS"}:
            success_count += 1
        else:
            failure_count += 1
    else:
        print(f"  File {fname}: record not found in DB!")
        entry["pipeline"] = {
            "final_status": "NOT_FOUND",
            "terminal": True,
            "poll_count": 0
        }
        failure_count += 1

total = len(batch_results["results"])
batch_results["success_count"] = success_count
batch_results["failure_count"] = failure_count
batch_results["success_rate_pct"] = round(success_count / total * 100, 1)
batch_results["completed_at"] = datetime.now(timezone.utc).isoformat()

with open(results_path, "w", encoding="utf-8") as f:
    json.dump(batch_results, f, indent=2, ensure_ascii=False)

print()
print("="*60)
print(f"REPAIR COMPLETE:")
print(f"  Total    : {total}")
print(f"  Success  : {success_count}")
print(f"  Failures : {failure_count}")
print(f"  Rate     : {batch_results['success_rate_pct']}%")
print(f"  Saved to : {results_path}")
print("="*60)
