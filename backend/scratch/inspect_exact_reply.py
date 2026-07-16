import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import AICache

file_hash = "c2ab2f6b5da0b8f9d2e1a86cb4b88c1549439c1bdbe3df267d59c689f529675a"
db_key = f"ocr_page:{file_hash}:14"
records = AICache.objects.filter(key_hash__startswith=db_key).order_by("created_at")

print(f"Total AICache entries found for page 14: {records.count()}")
for idx, rec in enumerate(records):
    print(f"\n--- Entry {idx}: key_hash={rec.key_hash} created_at={rec.created_at} ---")
    payload = rec.payload
    if isinstance(payload, str):
        payload = json.loads(payload)
    raw_ext = payload.get("_raw_extraction") or {}
    items = raw_ext.get("items") or []
    print("Items in _raw_extraction:")
    for i_idx, itm in enumerate(items):
        print(f"  Item {i_idx}: desc={itm.get('description')} | cgst_rate={itm.get('cgst_rate')} | sgst_rate={itm.get('sgst_rate')}")
