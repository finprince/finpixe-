"""
test_normalize.py
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from ocr_pipeline.normalize import get_canonical_export_record

test_invoice = {
    "header": {
        "vendor_name": "Test Vendor",
        "invoice_no": "12345",
        "total_amount": 100.0
    },
    "items": [
        {
            "description": "Item 1",
            "quantity": 1.0,
            "rate": 100.0,
            "amount": 100.0
        }
    ]
}

res = get_canonical_export_record(test_invoice)
print("Keys in result:", list(res.keys()))
print("_raw_extraction in result:", "_raw_extraction" in res)
if "_raw_extraction" in res:
    print("_raw_extraction value:", res["_raw_extraction"])
print("_validation_metadata in result:", "_validation_metadata" in res)
if "_validation_metadata" in res:
    print("_validation_metadata value:", res["_validation_metadata"])
