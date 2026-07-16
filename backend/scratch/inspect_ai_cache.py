import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import AICache

print("Querying AICache...")
qs = AICache.objects.all()
found = []
for c in qs:
    payload_str = json.dumps(c.payload)
    if "EIS/25-26/1014" in payload_str or "8210" in payload_str or "6116" in payload_str or "8205" in payload_str:
        found.append(c)

print(f"Found {len(found)} cache entries:")
for idx, c in enumerate(found):
    print(f"\n--- Entry {idx+1} | key_hash={c.key_hash} | created_at={c.created_at} ---")
    print(json.dumps(c.payload, indent=2)[:5000]) # Limit length to print safely
