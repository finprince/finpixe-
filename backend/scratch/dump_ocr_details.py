import os
import sys
import json
import time

BACKEND_DIR = r"c:\108\AI-accounting-0.03\backend"
sys.path.insert(0, BACKEND_DIR)

from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction

TARGET_PDF = r"C:\Users\ulaganathan\Downloads\Screenshot 2026-06-24 180236.pdf"

def main():
    print("Running Mistral OCR isolated page extraction...")
    t0 = time.time()
    res = run_isolated_page_extraction(TARGET_PDF, page_idx=0)
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.2f} seconds. Success: {res.get('success')}")
    
    # We remove image_bytes from the dumped output to keep the JSON file size small and readable
    if "image_bytes" in res:
        res["image_bytes_len"] = len(res["image_bytes"])
        del res["image_bytes"]
        
    res["total_ocr_latency_s"] = elapsed
    
    out_path = r"c:\108\AI-accounting-0.03\backend\scratch\ocr_extraction_details.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
    print(f"Details written to {out_path}")

if __name__ == "__main__":
    main()
