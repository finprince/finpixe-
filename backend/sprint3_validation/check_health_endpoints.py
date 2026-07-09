import urllib.request
import json

endpoints = [
    "http://localhost:8000/api/health/",
    "http://localhost:8000/api/vouchers/health/",
    "http://localhost:8000/api/vouchers/bulk-healthz/"
]

for url in endpoints:
    print(f"Checking endpoint: {url}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            print(f"  Status: {status}")
            try:
                parsed = json.loads(body)
                print(f"  Body (JSON): {json.dumps(parsed, indent=2)}")
            except:
                print(f"  Body (Text): {body[:200]}")
    except Exception as e:
        print(f"  Check failed: {e}")
