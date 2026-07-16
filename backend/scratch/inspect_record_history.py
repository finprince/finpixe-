import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, RescanHistory

for rid in [1009527, 1009545]:
    rec = InvoiceTempOCR.objects.filter(id=rid).first()
    if rec:
        print(f"\n================ RECORD {rid} ================")
        print(f"status: {rec.status}")
        print(f"processed: {rec.processed}")
        print(f"supplier_invoice_no: {rec.supplier_invoice_no}")
        print(f"gstin: {rec.gstin}")
        
        # Print extracted_data
        ext = rec.extracted_data or {}
        print("Keys in extracted_data:", list(ext.keys()))
        
        if "items" in ext:
            print("\nItems in extracted_data:")
            for idx, itm in enumerate(ext["items"]):
                print(f"  Item {idx}: description={itm.get('description')} | hsn_sac={itm.get('hsn_code') or itm.get('hsn_sac')} | computed_gst_rate={itm.get('computed_gst_rate')} | cgst_rate={itm.get('cgst_rate')} | sgst_rate={itm.get('sgst_rate')}")
                
        if "_raw_extraction" in ext:
            raw = ext["_raw_extraction"]
            print("\nItems in _raw_extraction:")
            if "items" in raw:
                for idx, itm in enumerate(raw["items"]):
                    print(f"  Item {idx}: description={itm.get('description')} | hsn_code={itm.get('hsn_code')} | cgst_rate={itm.get('cgst_rate')} | sgst_rate={itm.get('sgst_rate')}")
                    
        # Check RescanHistory
        history = RescanHistory.objects.filter(invoice_temp_ocr_id=rid)
        print(f"\nRescanHistory count: {history.count()}")
        for h in history:
            print(f"  - timestamp={h.timestamp} | type={h.rescan_type} | user={h.user}")
    else:
        print(f"Record {rid} not found.")
