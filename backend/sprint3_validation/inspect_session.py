import os, sys, django, json
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
django.setup()
from ocr_pipeline.models import InvoiceTempOCR, InvoicePageResult

rid = 1008386
r = InvoiceTempOCR.objects.get(id=rid)
sess_id = r.upload_session_id

print(f"=== Session ID: {sess_id} ===")
# Find all InvoiceTempOCR records in this session
records = InvoiceTempOCR.objects.filter(upload_session_id=sess_id).order_by('id')
print(f"Total InvoiceTempOCR records: {records.count()}")
for rec in records:
    print(f"  id={rec.id} status={rec.status} supplier_invoice_no={repr(rec.supplier_invoice_no)} file={rec.file_path[-40:]}")

# Find all InvoicePageResult records in this session
pages = InvoicePageResult.objects.filter(session_id=sess_id).order_by('id')
print(f"\nTotal InvoicePageResult records: {pages.count()}")
# Group pages by record_id
from collections import defaultdict
grouped_pages = defaultdict(list)
for p in pages:
    grouped_pages[p.record_id].append(p)

for r_id, p_list in grouped_pages.items():
    print(f"  record_id={r_id} has {len(p_list)} pages: {[p.page_number for p in p_list]}")
    # Show first page info
    p0 = p_list[0]
    cp = p0.canonical_payload or {}
    print(f"    Page {p0.page_number} info: inv={cp.get('invoice_no')} vendor={cp.get('vendor_name')}")
