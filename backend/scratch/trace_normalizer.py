import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from ocr_pipeline.normalize import get_normalized_items

r = InvoiceTempOCR.objects.get(id=1012649)
ext = r.extracted_data or {}
raw_ai = ext.get('_raw_extraction') or {}

print("=== NORMALIZER INPUT (RAW AI ITEMS) ===")
raw_items = raw_ai.get('items', [])
for i, item in enumerate(raw_items):
    print(f"Item {i}:")
    for k, v in item.items():
        print(f"  {k}: {v} ({type(v).__name__})")

print("\n=== RUNNING NORMALIZER ===")
normalized_items = get_normalized_items(raw_ai, tenant_id=r.tenant_id)

print("\n=== NORMALIZER OUTPUT ===")
for i, item in enumerate(normalized_items):
    print(f"Item {i}:")
    for k, v in item.items():
        print(f"  {k}: {v} ({type(v).__name__})")
