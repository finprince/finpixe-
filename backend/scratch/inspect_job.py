import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from vouchers.models import BulkInvoiceJob
from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState, FinalizedSnapshot
from core.redis_orchestrator import orchestrator

latest_job = BulkInvoiceJob.objects.order_by('-id').first()
print(f'Latest Job ID: {latest_job.id if latest_job else None}')
if latest_job:
    print(f'Upload session id: {latest_job.upload_session_id}')
    print(f'Total files: {latest_job.total_files}')
    items = list(latest_job.items.all())
    print(f'Items count: {len(items)}')
    for it in items:
        print(f'  Item {it.id}: item_dict={it.__dict__}')
    
    ocr_records = list(InvoiceTempOCR.objects.filter(upload_session_id=latest_job.upload_session_id))
    print(f'OCR records count with upload_session_id={latest_job.upload_session_id}: {len(ocr_records)}')
    for rec in ocr_records:
        print(f'  OCR {rec.id}: dict={rec.__dict__}')
    
    # Also check all recent OCR records
    recent_ocr = list(InvoiceTempOCR.objects.order_by('-id')[:5])
    print(f'\nRecent 5 OCR records:')
    for rec in recent_ocr:
        print(f'  OCR {rec.id}: status={rec.status}, upload_session={rec.upload_session_id}, original_filename={getattr(rec, "original_filename", None)}')

    states = list(SessionFinalizationState.objects.filter(id__in=[str(r.id) for r in ocr_records]))
    print(f'\nSessionFinalizationStates for job OCR records: {len(states)}')
    for s in states:
        print(f'  State {s.id}: dict={s.__dict__}')
    
    snaps = list(FinalizedSnapshot.objects.filter(session_id=latest_job.upload_session_id))
    print(f'\nFinalizedSnapshots for job upload_session_id={latest_job.upload_session_id}: {len(snaps)}')
    for sn in snaps:
        print(f'  Snapshot {sn.id}: dict={sn.__dict__}')

    auth_state = orchestrator.get_authoritative_session_state(latest_job.upload_session_id)
    print(f'\nAuth State for {latest_job.upload_session_id}:')
    for k, v in auth_state.items():
        print(f'  {k}: {v}')
