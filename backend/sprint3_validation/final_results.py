"""Final session results summary."""
from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState
from collections import Counter

with open('sprint3_validation/reports/SESSION_ID.txt', 'r', encoding='utf-8') as fh:
    session_id = fh.read().strip()
records = list(InvoiceTempOCR.objects.filter(upload_session_id=session_id).order_by('id'))
statuses = Counter(r.status for r in records)
print('=== FINAL SESSION RESULTS ===')
print('Session:', session_id)
print('Total:', len(records))
print('Status breakdown:', dict(statuses))
print()
print('%-6s %-15s %-15s %-12s %s' % ('ID', 'STATUS', 'VENDOR', 'AMOUNT', 'FILE'))
print('-'*95)
for r in records:
    fname = (r.file_path or '').split('/')[-1]
    parts = fname.split('_', 1)
    clean_fname = parts[-1] if len(parts) > 1 else fname
    clean_fname = clean_fname[-35:]
    data = r.extracted_data or {}
    vendor = str(data.get('vendor_name', ''))[:14]
    amount = str(data.get('total_amount', data.get('grand_total', '')))[:11]
    print('%-6d %-15s %-15s %-12s %s' % (r.id, r.status, vendor, amount, clean_fname))

success = statuses.get('FINALIZED', 0)
total = len(records)
print()
print('SUCCESS RATE: %d/%d = %.1f%%' % (success, total, success/total*100))
print()

# Check barriers for non-finalized records
for r in records:
    if r.status not in ('FINALIZED',):
        fs = SessionFinalizationState.objects.filter(id=str(r.id)).first()
        fname = (r.file_path or '').split('/')[-1][-30:]
        if fs:
            print('NON-FINALIZED: id=%d status=%s barrier=%d/%d file=%s' % (
                r.id, r.status, fs.total_pages_completed, fs.expected_pages, fname))
        else:
            print('NON-FINALIZED: id=%d status=%s file=%s (no barrier)' % (r.id, r.status, fname))
