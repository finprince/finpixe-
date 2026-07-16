import os
import sys
import django
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState, FinalizedSnapshot

session_id = "test-val-forensic-c6424728"
print(f"=== INSPECTING SESSION {session_id} ===")

records = InvoiceTempOCR.objects.filter(upload_session_id=session_id).order_by('id')
print(f"Total InvoiceTempOCR records in session: {records.count()}")
for r in records:
    print(f"  Record ID: {r.id} | Status: {r.status} | Validation Status: {r.validation_status} | Invoice: {r.supplier_invoice_no}")

print("\n--- SessionFinalizationStates in this session ---")
for r in records:
    state = SessionFinalizationState.objects.filter(id=str(r.id)).first()
    if state:
        print(f"  For Record {r.id}: expected={state.expected_pages}, completed={state.completed_pages}, failed={state.failed_pages}, status={state.status}, terminal_consistency={state.terminal_consistency}")

print("\n--- FinalizedSnapshots for this session ---")
snaps = FinalizedSnapshot.objects.filter(session_id=session_id)
print(f"Count: {snaps.count()}")
for s in snaps:
    print(f"  Snap ID: {s.id} | Created: {s.created_at}")

# Let's call the CleanOCRStagingView.get logic to see exactly what response is returned
from django.test import RequestFactory
from ocr_pipeline.views import CleanOCRStagingView
from core.models import User

factory = RequestFactory()
request = factory.get(f'/api/ocr-staging/?upload_session_id={session_id}')
user = User.objects.get(username='admin')
from rest_framework.request import Request
drf_request = Request(request)
drf_request.user = user

view = CleanOCRStagingView()
response = view.get(drf_request)
print("\n--- CleanOCRStagingView.get RESPONSE ---")
print(f"Status Code: {response.status_code}")
print(f"Response Data keys: {response.data.keys() if hasattr(response, 'data') else 'No data'}")
if hasattr(response, 'data'):
    print(f"Response Status: {response.data.get('status')}")
    print(f"Response Progress Percent: {response.data.get('progress_percent')}")
    print(f"Response Data Rows count: {len(response.data.get('data', []))}")
