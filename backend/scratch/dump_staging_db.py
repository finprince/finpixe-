import os
import sys
import json
import requests

API_BASE    = "http://localhost:8000"
USERNAME    = "admin"
EMAIL       = "admin@budstech.com"
PASSWORD    = "admin123"
SESSION_ID  = "4ef615ff-679e-414c-90b9-3dbb25762071"

def main():
    print(f"Logging in to fetch session {SESSION_ID}...")
    resp = requests.post(f"{API_BASE}/api/auth/login/",
                         json={"username": USERNAME, "email": EMAIL, "password": PASSWORD},
                         timeout=15)
    token = resp.json().get("access") or resp.json().get("token", "")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"{API_BASE}/api/ocr-staging/?upload_session_id={SESSION_ID}"
    r = requests.get(url, headers=headers, timeout=30)
    data = r.json()
    
    if isinstance(data, list):
        records = data
    else:
        records = data.get("data") or data.get("results") or []
        
    if not records:
        print("No records found.")
        return
        
    record = records[0]
    out_path = r"c:\108\AI-accounting-0.03\backend\scratch\staging_extracted_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"Staging record details dumped to {out_path}")

if __name__ == "__main__":
    main()
