import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from pending_purchases.models import PendingPurchase

def inspect_record(record_id):
    r = InvoiceTempOCR.objects.get(id=record_id)
    print(f"\n==========================================")
    print(f"RECORD ID: {r.id}")
    print(f"Invoice Number: {r.supplier_invoice_no}")
    print(f"File Path: {r.file_path}")
    print(f"Status: {r.status}, Validation Status: {r.validation_status}")
    
    ext = r.extracted_data or {}
    print("\n--- EXTRACTED_DATA KEYS ---")
    print(list(ext.keys()))
    
    # 1. OCR text snippets (first 200 chars)
    if r.ocr_raw_text:
        print("\n--- OCR RAW TEXT SNIPPET (first 500 chars) ---")
        print(r.ocr_raw_text[:500])
    
    # Let's find raw Qwen keys
    for k in ['_raw_qwen', 'raw_qwen', '_qwen_raw', 'qwen_output', '_raw_ai_output', '_ai_raw', 'raw_ai', '_raw_extraction', 'raw_extraction', '_source_json', '_raw_json', 'raw_response', '_raw_response', '_model_output']:
        if k in ext:
            print(f"\n--- RAW AI OUTPUT ({k}) ---")
            print(json.dumps(ext[k], indent=2)[:3000])
            break
            
    # 2. Structured AI JSON items
    print("\n--- TOP-LEVEL ITEMS IN EXTRACTED_DATA ---")
    items = ext.get('items', [])
    for idx, item in enumerate(items):
        print(f"  Item {idx}: desc={item.get('description')}, hsn={item.get('hsn_code') or item.get('hsn')}, qty={item.get('quantity') or item.get('qty')}, rate={item.get('rate') or item.get('unit_price')}, taxable={item.get('taxable_value') or item.get('taxable')}, gst_rate={item.get('gst_rate')}, cgst_rate={item.get('cgst_rate')}, sgst_rate={item.get('sgst_rate')}, igst_rate={item.get('igst_rate')}, tax_amt={item.get('cgst_amount') or item.get('sgst_amount') or item.get('igst_amount')}")

    # 3. Assembled exports
    print("\n--- ASSEMBLED EXPORTS ---")
    ae = ext.get('assembled_exports') or []
    if ae:
        print(f"Number of assembled exports: {len(ae)}")
        ae0 = ae[0]
        ae_items = ae0.get('items', [])
        for idx, item in enumerate(ae_items):
            print(f"  Item {idx}: desc={item.get('description')}, hsn={item.get('hsn_code') or item.get('hsn')}, qty={item.get('quantity') or item.get('qty')}, rate={item.get('rate') or item.get('unit_price')}, taxable={item.get('taxable_value') or item.get('taxable')}, gst_rate={item.get('gst_rate')}, cgst_rate={item.get('cgst_rate')}, sgst_rate={item.get('sgst_rate')}, igst_rate={item.get('igst_rate')}, tax_amt={item.get('cgst_amount') or item.get('sgst_amount') or item.get('igst_amount')}")
    else:
        print("No assembled_exports")

    # 4. Sections
    print("\n--- SECTIONS ITEMS ---")
    sec_items = ext.get('sections', {}).get('items', [])
    for idx, item in enumerate(sec_items):
        print(f"  Item {idx}: desc={item.get('description')}, hsn={item.get('hsn_code') or item.get('hsn')}, qty={item.get('quantity') or item.get('qty')}, rate={item.get('rate') or item.get('unit_price')}, taxable={item.get('taxable_value') or item.get('taxable')}, gst_rate={item.get('gst_rate')}, cgst_rate={item.get('cgst_rate')}, sgst_rate={item.get('sgst_rate')}, igst_rate={item.get('igst_rate')}, tax_amt={item.get('cgst_amount') or item.get('sgst_amount') or item.get('igst_amount')}")

    # 5. GST validation engine / audit trail
    print("\n--- GST AUDIT TRAIL ---")
    print(json.dumps(ext.get('gst_audit_trail'), indent=2))

inspect_record(1009528)
inspect_record(1009527)
