"""
Phase 3 - Raw OCR Trace: Run Mistral OCR on 3 representative invoices
and dump raw text for ground truth comparison.
READ-ONLY — no code modifications.
"""
import os, sys, json, pypdf
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
import django

def main():
    django.setup()
    from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction

    DATASET = r"C:\Users\ulaganathan\Downloads\New folder (2)"

    # Select representative invoices:
    # 1. IMG_20260319_0001 (16 pages, N.S. SOLUTION) - multi-page, FINALIZED
    # 2. IMG_20260406_0006 (2 pages, SRI VISHNU) - small, FINALIZED
    # 3. IMG_20260319_0003 (5 pages, SRI VISHNU HEAT TREATERS)
    targets = [
        ("IMG_20260319_0001.pdf", 1008375),
        ("IMG_20260406_0006.pdf", 1008395),
        ("IMG_20260319_0003.pdf", 1008377),
    ]

    results = {}
    for fname, record_id in targets:
        fpath = os.path.join(DATASET, fname)
        print(f"\n{'='*60}")
        print(f"File: {fname} (record={record_id})")
        with open(fpath,"rb") as f:
            reader = pypdf.PdfReader(f)
            pages = len(reader.pages)
        print(f"Pages: {pages}")
        
        # OCR first 2 pages
        ocr_pages = []
        for page_idx in range(min(2, pages)):
            print(f"  Running Mistral OCR page {page_idx+1}...")
            result = run_isolated_page_extraction(fpath, page_idx, dpi=200)
            if result.get("success"):
                text = result.get("text","")
                print(f"  Page {page_idx+1}: {len(text)} chars, conf={result.get('avg_confidence',0):.3f}")
                print(f"  --- OCR TEXT (first 300 chars) ---")
                print(text[:300])
                print("  ---")
                ocr_pages.append({"page":page_idx+1,"text":text,"conf":result.get("avg_confidence")})
            else:
                print(f"  Page {page_idx+1} FAILED: {result.get('error')}")
                ocr_pages.append({"page":page_idx+1,"error":result.get("error")})
        
        results[fname] = {"record_id":record_id,"pages":pages,"ocr_pages":ocr_pages}

    with open("sprint3_validation/reports/OCR_RAW_TRACE.json","w",encoding="utf-8") as f:
        json.dump(results,f,indent=2,ensure_ascii=False)
    print("\nDone. Written to OCR_RAW_TRACE.json")

if __name__ == '__main__':
    main()
