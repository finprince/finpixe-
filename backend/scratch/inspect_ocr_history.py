import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from vouchers.models import BulkInvoiceJob, InvoiceProcessingItem
from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState, FinalizedSnapshot, InvoicePageOCR

ocr = InvoiceTempOCR.objects.filter(id=1013212).first()
print(f'OCR 1013212: {ocr.__dict__ if ocr else None}')

pages = list(InvoicePageOCR.objects.filter(record_id=1013212))
print(f'\nPages for OCR 1013212 ({len(pages)}):')
for p in pages:
    print(f'  Page {p.id}: page_num={p.page_number}, status={p.status}, error={p.error_message}, text_len={len(p.raw_text or "")}')

items = list(InvoiceProcessingItem.objects.filter(staging_record_id=1013212))
print(f'\nInvoiceProcessingItems pointing to 1013212 ({len(items)}):')
for it in items:
    print(f'  Item {it.id}: job_id={it.job_id}, status={it.status}, created_at={it.created_at}')

jobs = list(BulkInvoiceJob.objects.filter(id__in=[it.job_id for it in items]))
print(f'\nJobs:')
for j in jobs:
    print(f'  Job {j.id}: status={j.status}, upload_session_id={j.upload_session_id}, total_files={j.total_files}, created_at={j.created_at}')
