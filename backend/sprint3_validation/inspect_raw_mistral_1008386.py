import os, sys, django, json
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
django.setup()
from ocr_pipeline.models import InvoicePageResult
pages = InvoicePageResult.objects.filter(record_id=1008386).order_by('page_number')
for p in pages:
    print(f"=== Page {p.page_number} ===")
    print("canonical_payload type:", type(p.canonical_payload))
    if isinstance(p.canonical_payload, dict):
        print(json.dumps(p.canonical_payload, indent=2)[:2000])
    else:
        print(str(p.canonical_payload)[:2000])
