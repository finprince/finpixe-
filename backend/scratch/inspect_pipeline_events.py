import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from vouchers.models import BulkInvoiceJob, InvoiceProcessingItem
from ocr_pipeline.models import (
    InvoiceTempOCR, SessionFinalizationState, FinalizedSnapshot,
    InvoicePageResult, OCRTask, PipelineEvent
)

session_id = '1788254375053'
record_id = '1013212'

print('--- InvoiceTempOCR ---')
for r in InvoiceTempOCR.objects.filter(upload_session_id=session_id):
    print(f'OCR {r.id}: status={r.status}, processed={r.processed}, file_hash={r.file_hash}')

print('\n--- InvoiceProcessingItem ---')
for item in InvoiceProcessingItem.objects.filter(job_id=882):
    print(f'Item {item.id}: status={item.status}, staging_record_id={item.staging_record_id}, file_hash={item.file_hash}')

print('\n--- PipelineEvents ---')
for ev in PipelineEvent.objects.filter(record_id=record_id).order_by('id'):
    print(f'Event {ev.id}: status={ev.status}, seq={ev.event_sequence}, version={ev.workflow_version}, session={ev.session_id}, created_at={ev.created_at}')

print('\n--- OCRTasks ---')
for t in OCRTask.objects.filter(result_id=record_id):
    print(f'Task {t.id}: status={t.status}, job_id={t.job_id}')

print('\n--- InvoicePageResults ---')
for pr in InvoicePageResult.objects.filter(record_id=record_id):
    print(f'Page {pr.id}: page_num={pr.page_number}, status={pr.status}, created_at={pr.created_at}')

print('\n--- SessionFinalizationState ---')
for s in SessionFinalizationState.objects.filter(id=record_id):
    print(f'State {s.id}: expected={s.expected_pages}, completed={s.completed_pages}, failed={s.failed_pages}, ai_completed={s.ai_completed_pages}, snap_complete={s.snapshot_complete}, mat_complete={s.materialization_complete}')
