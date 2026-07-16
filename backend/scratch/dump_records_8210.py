import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from pending_purchases.models import PendingPurchase

def dump_data(r):
    print(f"\n=======================================================")
    print(f"RECORD ID: {r.id}")
    print(f"Invoice Number: {r.supplier_invoice_no}")
    print(f"File Path: {r.file_path}")
    print(f"Status: {r.status}, Validation Status: {r.validation_status}")
    
    ext = r.extracted_data or {}
    
    # 1. OCR text snippet (first 1000 chars)
    print("\n--- OCR RAW TEXT ---")
    if r.ocr_raw_text:
        print(r.ocr_raw_text)
    else:
        print("None")
        
    # 2. Raw AI output
    print("\n--- RAW AI JSON (_raw_extraction) ---")
    raw_ai = ext.get('_raw_extraction')
    if raw_ai:
        print(json.dumps(raw_ai, indent=2))
    else:
        print("None")
        
    # 3. Normalizer input / output (extracted_data.items)
    print("\n--- NORMALIZER OUTPUT (extracted_data.items) ---")
    items = ext.get('items', [])
    for idx, item in enumerate(items):
        print(f"Item {idx}:")
        for k in ['hsn_code', 'hsn', 'description', 'quantity', 'qty', 'rate', 'unit_price', 'taxable_value', 'taxable', 'gst_rate', 'cgst_rate', 'sgst_rate', 'igst_rate', 'cgst_amount', 'sgst_amount', 'igst_amount', 'cess_amount', 'expected_gst', 'current_gst']:
            print(f"  {k}: {item.get(k)}")

    # 4. GST validation audit trail
    print("\n--- GST AUDIT TRAIL ---")
    print(json.dumps(ext.get('gst_audit_trail'), indent=2))

print("=== INSPECTING RECORD 1009527 ===")
try:
    r = InvoiceTempOCR.objects.get(id=1009527)
    dump_data(r)
except Exception as e:
    print(f"Error loading 1009527: {e}")

print("\n=== INSPECTING RECORD 1009545 ===")
try:
    r = InvoiceTempOCR.objects.get(id=1009545)
    dump_data(r)
except Exception as e:
    print(f"Error loading 1009545: {e}")
