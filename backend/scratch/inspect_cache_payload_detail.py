import os
import sys
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import AICache

qs = AICache.objects.all()
for c in qs:
    payload_str = json.dumps(c.payload)
    if "EIS/25-26/1014" in payload_str:
        print("FOUND MATCHING ENTRY:")
        print("Keys at root of payload:", list(c.payload.keys()))
        if "_raw_extraction" in c.payload:
            print("Keys inside _raw_extraction:", list(c.payload["_raw_extraction"].keys()))
        if "_raw_response" in c.payload:
            print("_raw_response field length:", len(str(c.payload["_raw_response"])))
            print("_raw_response contents:")
            print(json.dumps(c.payload["_raw_response"], indent=2)[:2000])
        else:
            print("No _raw_response in root of payload")
        
        # Check if there are other keys like raw_response or model_output
        for k in c.payload.keys():
            if "raw" in k.lower() or "response" in k.lower() or "output" in k.lower():
                print(f"Key '{k}' values:")
                print(json.dumps(c.payload[k], indent=2)[:1000])
        break
