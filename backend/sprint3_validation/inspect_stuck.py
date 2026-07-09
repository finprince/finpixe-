"""Inspect stuck EXTRACTING records."""
from ocr_pipeline.models import InvoiceTempOCR, SessionFinalizationState

stuck_ids = [1008324, 1008325, 1008326, 1008327, 1008328]
for rid in stuck_ids:
    try:
        r = InvoiceTempOCR.objects.get(id=rid)
        fs = SessionFinalizationState.objects.filter(id=str(rid)).first()
        data = r.extracted_data or {}
        print(f"\nRecord {rid}: status={r.status}")
        print(f"  barrier: completed={fs.total_pages_completed if fs else 'N/A'}"
              f"  expected={fs.expected_pages if fs else 'N/A'}"
              f"  ai_done={fs.ai_completed_pages if fs else 'N/A'}"
              f"  finalized_at={fs.finalized_at if fs else 'N/A'}")
        print(f"  extracted_data keys({len(data)}): {list(data.keys())[:5]}")
        print(f"  vendor_name={data.get('vendor_name', 'N/A')}")
        print(f"  total_amount={data.get('total_amount', 'N/A')}")
    except Exception as e:
        print(f"  ERROR for {rid}: {e}")
