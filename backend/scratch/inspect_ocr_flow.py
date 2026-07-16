import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, PipelineEvent, SessionFinalizationState, OCRTask
from pending_purchases.models import PendingPurchase

record_id = 1012613
print(f"=== DEEP DIVE INTO RECORD {record_id} ===")

r = InvoiceTempOCR.objects.filter(id=record_id).first()
if not r:
    print("Record not found!")
    sys.exit(0)

print("\n--- InvoiceTempOCR ---")
print(f"ID: {r.id}")
print(f"Status: {r.status}")
print(f"Validation Status: {r.validation_status}")
print(f"Processed: {r.processed}")
print(f"Upload Session ID: {r.upload_session_id}")
print(f"File Path: {r.file_path}")
print(f"Supplier Invoice No: {r.supplier_invoice_no}")
print(f"GSTIN: {r.gstin}")
print(f"Created At: {r.created_at}")
print(f"Workflow Version: {r.workflow_version}")

print("\n--- SessionFinalizationState ---")
state = SessionFinalizationState.objects.filter(id=str(record_id)).first()
if state:
    print(f"ID: {state.id}")
    print(f"Expected Pages: {state.expected_pages}")
    print(f"Completed Pages: {state.completed_pages}")
    print(f"Failed Pages: {state.failed_pages}")
    print(f"AI Completed Pages: {state.ai_completed_pages}")
    print(f"Snapshot Created: {state.snapshot_created}")
    print(f"Status: {state.status}")
    print(f"Terminal Consistency: {state.terminal_consistency}")
else:
    print("No SessionFinalizationState found!")

print("\n--- PipelineEvents ---")
events = PipelineEvent.objects.filter(record_id=str(record_id)).order_by('event_sequence')
print(f"Total events: {events.count()}")
for e in events:
    print(f"Seq: {e.event_sequence} | Status: {e.status} | Created: {e.created_at} | Schema: {e.event_schema_version}")
    print(f"  Metadata: {e.metadata}")

print("\n--- OCRTasks ---")
tasks = OCRTask.objects.filter(result_id=record_id)
print(f"Total tasks: {tasks.count()}")
for t in tasks:
    print(f"Task ID: {t.id} | Job ID: {t.job_id} | Status: {t.status}")

print("\n--- Linked Pending Purchases ---")
pps = PendingPurchase.objects.filter(source_scan_row_id=record_id)
print(f"Total Pending Purchases: {pps.count()}")
for p in pps:
    print(f"PP ID: {p.id} | Status: {p.pending_purchase_status} | Invoice: {p.invoice_number}")
