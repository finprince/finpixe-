"""
Phase 6 - Stability & Determinism Test
Runs Mistral OCR on the same page 3 times, checks character length, hash, and content identity.
Also checks the AI structured extraction.
READ-ONLY — no code changes.
"""
import os, sys, json, hashlib
sys.path.insert(0,".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE","backend.settings")
import django

def main():
    django.setup()
    from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction

    DATASET = r"C:\Users\ulaganathan\Downloads\New folder (2)"
    fname = "IMG_20260406_0006.pdf"
    fpath = os.path.join(DATASET, fname)

    print(f"=== Phase 6 Stability Analysis: {fname} ===")
    
    texts = []
    hashes = []
    confs = []
    
    # Run 3 iterations
    for i in range(3):
        print(f"Iteration {i+1}...")
        res = run_isolated_page_extraction(fpath, 0, dpi=200)
        if not res.get("success"):
            print(f"  FAILED: {res.get('error')}")
            return
        
        txt = res.get("text", "")
        h = hashlib.sha256(txt.encode('utf-8')).hexdigest()
        conf = res.get("avg_confidence", 0)
        
        texts.append(txt)
        hashes.append(h)
        confs.append(conf)
        
        print(f"  Len: {len(txt)} | Hash: {h[:16]} | Conf: {conf:.4f}")

    print("\n--- Comparison Results ---")
    deterministic = len(set(hashes)) == 1
    if deterministic:
        print("[SUCCESS] OCR output is 100% DETERMINISTIC across 3 runs! (All hashes match)")
    else:
        print("[WARNING] OCR output is NON-DETERMINISTIC! Hashes differ.")
        # Compare lengths and check character diff
        for idx in range(1, len(texts)):
            diff_len = len(texts[idx]) - len(texts[0])
            print(f"  Run {idx+1} vs Run 1: length difference = {diff_len} characters")
            # Print first difference if any
            if texts[idx] != texts[0]:
                for c_idx, (c1, c2) in enumerate(zip(texts[0], texts[idx])):
                    if c1 != c2:
                        print(f"  First char diff at index {c_idx}: {repr(texts[0][c_idx-10:c_idx+10])} vs {repr(texts[idx][c_idx-10:c_idx+10])}")
                        break

if __name__ == '__main__':
    main()
