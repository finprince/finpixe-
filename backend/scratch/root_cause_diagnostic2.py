"""
ROOT CAUSE DIAGNOSTIC: UI stuck at "Almost done â€” building review..."
Inspects the live session 43ec9f0c-d755-419b-8e4f-32d47999e4fc
and cross-checks every layer of the pipeline that the UI polls.
"""
import os
import sys
import django
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import (
    InvoiceTempOCR, SessionFinalizationState, FinalizedSnapshot, PipelineEvent, OCRTask
)
from core.redis_orchestrator import orchestrator

SESSION_ID = "43ec9f0c-d755-419b-8e4f-32d47999e4fc"
RECORD_ID = 1012613

print("=" * 70)
print(f"ROOT CAUSE DIAGNOSTIC FOR SESSION: {SESSION_ID}")
print("=" * 70)

# â”€â”€â”€ LAYER 1: InvoiceTempOCR DB Record â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[LAYER 1] InvoiceTempOCR DB Record:")
r = InvoiceTempOCR.objects.filter(id=RECORD_ID).first()
if r:
    print(f"  status             : {r.status}")
    print(f"  validation_status  : {r.validation_status}")
    print(f"  processed          : {r.processed}")
    print(f"  supplier_invoice_no: {r.supplier_invoice_no}")
    print(f"  upload_session_id  : {r.upload_session_id}")
    print(f"  created_at         : {r.created_at}")
else:
    print("  !! RECORD NOT FOUND !!")

# â”€â”€â”€ LAYER 2: SessionFinalizationState â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[LAYER 2] SessionFinalizationState:")
state = SessionFinalizationState.objects.filter(id=str(RECORD_ID)).first()
if state:
    expected = state.expected_pages or 1
    completed = (state.completed_pages or 0) + (state.failed_pages or 0)
    raw_pct = (completed / expected) * 100.0
    backend_pct = min(99.0, raw_pct)
    print(f"  status              : {state.status}")
    print(f"  expected_pages      : {state.expected_pages}")
    print(f"  completed_pages     : {state.completed_pages}")
    print(f"  failed_pages        : {state.failed_pages}")
    print(f"  ai_completed_pages  : {state.ai_completed_pages}")
    print(f"  snapshot_created    : {state.snapshot_created}")
    print(f"  terminal_consistency: {state.terminal_consistency}")
    print(f"  raw_pct calculation : {completed}/{expected} * 100 = {raw_pct:.2f}%")
    print(f"  backend_pct (min99) : {backend_pct:.2f}%")
    print()
    if state.terminal_consistency:
        print("  âœ… terminal_consistency=True => backend GET will return status='FINALIZED'")
    else:
        print(f"  âš ï¸  terminal_consistency=False => backend GET returns status='PROCESSING' with progress={backend_pct:.2f}%")
        if backend_pct >= 99.0:
            print("  âŒ STUCK CONDITION: progress_percent hits 99% but FINALIZED not emitted yet!")
else:
    print("  !! NO SessionFinalizationState found for this record !!")
    print("  âŒ STUCK CONDITION: barrier never initialized â€” GET returns status=PROCESSING, progress=0%")

# â”€â”€â”€ LAYER 3: FinalizedSnapshot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[LAYER 3] FinalizedSnapshot:")
snaps = FinalizedSnapshot.objects.filter(session_id=SESSION_ID)
print(f"  Snapshots count: {snaps.count()}")
for s in snaps:
    print(f"  Snap ID: {s.id}, created: {s.created_at}, tenant: {s.tenant_id}")

if not snaps.exists():
    print("  âš ï¸  No FinalizedSnapshot found â€” SSE cannot emit FINALIZED even if Redis says FINALIZED!")

# â”€â”€â”€ LAYER 4: Redis Orchestrator â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[LAYER 4] Redis Orchestrator State:")
try:
    redis_status = orchestrator.get_session_status(SESSION_ID)
    auth_state = orchestrator.get_authoritative_session_state(SESSION_ID)
    print(f"  redis_status        : {redis_status}")
    print(f"  authoritative_state : {auth_state}")
    if redis_status:
        print(f"  Redis progress      : {redis_status.get('progress')}%")
        print(f"  Redis status        : {redis_status.get('status')}")
        if redis_status.get('status') in ['COMPLETED', 'FINALIZED']:
            print("  âœ… Redis says FINALIZED")
            if not snaps.exists():
                print("  âŒ But no FinalizedSnapshot => SSE blocks FINALIZED emission (line 1779)")
        else:
            print(f"  âš ï¸  Redis status is '{redis_status.get('status')}' â€” not FINALIZED yet")
    else:
        print("  âš ï¸  No Redis state found for this session (may have expired or never set)")
except Exception as e:
    print(f"  !! Redis error: {e}")

# â”€â”€â”€ LAYER 5: SSE Simulation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[LAYER 5] SSE Condition Simulation:")
all_records = InvoiceTempOCR.objects.filter(upload_session_id=SESSION_ID)
is_processing = all_records.filter(status__in=[
    'PENDING', 'INGESTED', 'INGESTING',
    'QUEUED', 'PROCESSING', 'EXTRACTING',
    'ASSEMBLING', 'FINALIZING'
]).exists() if all_records.exists() else True
print(f"  Total records in session   : {all_records.count()}")
print(f"  is_processing (still active): {is_processing}")

snap_tenant = None
if snaps.exists():
    snap_tenant = snaps.first().tenant_id

print(f"  FinalizedSnapshot exists   : {snaps.exists()}")
print(f"  Snapshot tenant_id         : {snap_tenant}")

try:
    redis_status = orchestrator.get_session_status(SESSION_ID)
    if redis_status and redis_status.get('status') in ['COMPLETED', 'FINALIZED']:
        if snaps.exists() and not is_processing:
            print("  âœ… SSE WOULD EMIT FINALIZED (Redis FINALIZED + snapshot exists + not processing)")
        elif not snaps.exists():
            print("  âŒ SSE BLOCKED: Redis says FINALIZED but FinalizedSnapshot missing!")
        elif is_processing:
            print("  âŒ SSE BLOCKED: Redis says FINALIZED but records still processing!")
    else:
        print("  âš ï¸  SSE would NOT emit FINALIZED (Redis not FINALIZED)")
        if not is_processing and snaps.exists():
            print("  âœ… SSE would fall to SNAPSHOT check and emit FINALIZED (fallback path)")
        elif not is_processing and not snaps.exists():
            print("  âŒ SSE FALLBACK ALSO BLOCKED: not processing but no snapshot!")
except Exception as e:
    print(f"  !! Redis check failed: {e}")

# â”€â”€â”€ LAYER 6: Backend GET Response Simulation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n[LAYER 6] Backend GET Response Simulation (what frontend receives when polling):")
from django.test import RequestFactory
from rest_framework.request import Request
from ocr_pipeline.views import CleanOCRStagingView
from core.models import User

try:
    factory = RequestFactory()
    raw_request = factory.get(f'/api/ocr-staging/?upload_session_id={SESSION_ID}')
    user = User.objects.get(username='admin')
    drf_request = Request(raw_request)
    drf_request.user = user

    view = CleanOCRStagingView()
    response = view.get(drf_request)

    resp_status = response.data.get('status')
    resp_pct = response.data.get('progress_percent')
    resp_rows = len(response.data.get('data', []))
    resp_terminal = response.data.get('terminal')
    resp_hydration = response.data.get('hydration_pending')

    print(f"  status            : {resp_status}")
    print(f"  progress_percent  : {resp_pct}")
    print(f"  data rows count   : {resp_rows}")
    print(f"  terminal          : {resp_terminal}")
    print(f"  hydration_pending : {resp_hydration}")

    if resp_status == 'FINALIZED':
        print("  âœ… GET returns FINALIZED â€” frontend doFetch would call setScanProgress(100) + setStep('review')")
    elif resp_status == 'PROCESSING' and resp_rows == 0:
        if resp_pct is not None and round(resp_pct) >= 100:
            print("  âŒ STUCK CONDITION CONFIRMED!")
            print("     GET returns PROCESSING + empty data + progress_percent>=100")
            print("     Frontend: pct=100 => 'Almost done â€” building review...' BUT hydration barrier blocks setStep('review')")
        else:
            print(f"  âš ï¸  GET returns PROCESSING + empty data + progress={resp_pct}% â€” still polling")
    elif resp_status == 'FAILED':
        print(f"  âš ï¸  GET returns FAILED + {resp_rows} rows â€” frontend should setStep('review') with failed data")
except Exception as e:
    import traceback
    print(f"  !! Simulation error: {e}")
    traceback.print_exc()

# â”€â”€â”€ SUMMARY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print("\n" + "=" * 70)
print("SUMMARY / ROOT CAUSE:")
print("=" * 70)

