"""Check current session state."""
from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState
from collections import Counter

with open('sprint3_validation/reports/SESSION_ID.txt', 'r', encoding='utf-8') as fh:
    session_id = fh.read().strip()
records = list(InvoiceTempOCR.objects.filter(
    upload_session_id=session_id).order_by('id').values('id', 'status', 'file_path'))
statuses = Counter(r['status'] for r in records)
print('Total:', len(records))
print('Status breakdown:', dict(statuses))
print()
for r in records:
    fname = (r['file_path'] or '').split('/')[-1][-35:]
    print('  id=%d status=%-15s file=%s' % (r['id'], r['status'], fname))
print()
stuck_ids = [r['id'] for r in records if r['status'] == 'EXTRACTING']
if stuck_ids:
    print('EXTRACTING records (barrier state):')
    for rid in stuck_ids:
        fs = SessionFinalizationState.objects.filter(id=str(rid)).first()
        if fs:
            print('  id=%d barrier=%d/%d ai_done=%d finalized=%s' % (
                rid, fs.total_pages_completed, fs.expected_pages,
                fs.ai_completed_pages, fs.finalized_at))
        else:
            print('  id=%d NO BARRIER STATE' % rid)
