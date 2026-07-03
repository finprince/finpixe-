# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
"""
OCR Dataset Validation — Phase 8/9
====================================
Runs the FIRST page of every invoice in the Sprint 3 dataset through the
PRODUCTION optimized OCR pipeline (isolated_ocr_service.py) and collects:
  - Average confidence
  - Format matches (GSTIN + dates)
  - Character count
  - OCR success / failure

Compares against the documented baseline (avg_conf = 0.755, format_matches = ~2).

Output: sprint3_validation/reports/OCR_DATASET_VALIDATION_REPORT.md

NO production code is modified. Read-only validation.
"""
import os
import sys
import json
import time
import re
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

# Set env vars for the optimised configuration
os.environ.setdefault("OCR_ADAPTIVE_PREPROCESS_ENABLED", "true")
os.environ.setdefault("OCR_CLAHE_CLIP_LIMIT", "2.0")
os.environ.setdefault("OCR_CLAHE_TILE_GRID_SIZE", "8")
os.environ.setdefault("OCR_SHARPEN_SIGMA", "3.0")
os.environ.setdefault("OCR_SHARPEN_WEIGHT", "1.5")
os.environ.setdefault("OCR_PAGE_RETRY_THRESHOLD", "0.75")
os.environ.setdefault("OCR_UPGRADE_DPI", "450")
os.environ.setdefault("OCR_BOX_RETRY_ENABLED", "true")
os.environ.setdefault("OCR_BOX_RETRY_THRESHOLD", "0.60")
os.environ.setdefault("OCR_BOX_RETRY_PADDING_PERCENT", "0.15")

from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction

# ── Config ────────────────────────────────────────────────────────────────────
INVOICE_DIR    = r"C:\Users\ulaganathan\Downloads\New folder (2)"
TARGET_INVOICE = r"C:\Users\ulaganathan\Downloads\Screenshot 2026-06-24 180236.pdf"
OUTPUT_DIR     = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASELINE_AVG_CONF    = 0.755   # documented baseline
BASELINE_FORMAT_CNT  = 2       # estimated baseline format matches per page
SUPPORTED_EXTS       = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}

# ── Helpers ───────────────────────────────────────────────────────────────────
def count_format_matches(text: str) -> int:
    gstins = len(re.findall(r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}\b', text.upper()))
    dates  = len(re.findall(r'\b\d{2}[-/]\d{2}[-/]\d{4}\b', text))
    return gstins * 3 + dates * 2

def get_page_count(file_path: str) -> int:
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(file_path)
        n = len(doc)
        doc.close()
        return n
    except Exception:
        return 1

def collect_scores(result: dict) -> dict:
    """Extract numeric scores from an OCR result dict.
    
    Result keys from isolated_ocr_service.py:
      result['success']       : bool
      result['avg_confidence']: float  (pre-computed mean over all ocr_blocks)
      result['ocr_blocks']    : list of dicts with 'confidence', 'text', 'bbox'
      result['text']          : str (assembled final text)
    """
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "unknown")}
    # Use pre-computed avg_confidence from the OCR service
    avg_conf  = result.get("avg_confidence", 0.0)
    ocr_blocks = result.get("ocr_blocks", [])
    text       = result.get("text", "")
    return {
        "success": True,
        "avg_conf":       round(avg_conf, 4),
        "char_count":     len(text),
        "box_count":      len(ocr_blocks),
        "format_matches": count_format_matches(text),
        "dpi":            result.get("dpi", 0),
        "blur_score":     round(result.get("blur_score", 0.0), 2),
    }

# ── Main ──────────────────────────────────────────────────────────────────────
def run_validation():
    print("=" * 68)
    print("  OCR DATASET VALIDATION — Phase 8/9")
    print("  Sprint 3 · 22 Invoices + Target Invoice")
    print("=" * 68)

    all_files = sorted([
        f for f in os.listdir(INVOICE_DIR)
        if Path(f).suffix.lower() in SUPPORTED_EXTS
    ])
    
    # Add the dedicated forensic target at position 0
    all_entries = [("TARGET", TARGET_INVOICE)] + [
        ("BATCH", os.path.join(INVOICE_DIR, f)) for f in all_files
    ]

    results = []
    total_success = 0
    total_fail    = 0

    for idx, (kind, fpath) in enumerate(all_entries, 1):
        fname = os.path.basename(fpath)
        pages = get_page_count(fpath)
        label = f"[{idx:02d}/{len(all_entries)}]"
        print(f"\n{label} {fname}  ({pages} page{'s' if pages > 1 else ''}) [{kind}]")
        
        # Test only page 0 (first page) — keeps total runtime under 15 minutes
        t0 = time.time()
        res = run_isolated_page_extraction(fpath, page_idx=0)
        elapsed = round(time.time() - t0, 2)

        scores = collect_scores(res)
        scores["filename"]  = fname
        scores["file_path"] = fpath
        scores["kind"]      = kind
        scores["pages"]     = pages
        scores["elapsed_s"] = elapsed
        results.append(scores)

        if scores.get("success"):
            total_success += 1
            print(f"  [OK] avg_conf={scores['avg_conf']:.3f}  "
                  f"chars={scores['char_count']}  "
                  f"boxes={scores['box_count']}  "
                  f"fmt={scores['format_matches']}  "
                  f"dpi={scores.get('dpi','?')}  "
                  f"blur={scores.get('blur_score','?')}  "
                  f"time={elapsed}s")
        else:
            total_fail += 1
            print(f"  [FAIL] {scores.get('error', 'unknown')}")

        # Introduce short sleep to prevent DNS rate-limiting or socket starvation
        time.sleep(2.0)

    # ── Build Report ─────────────────────────────────────────────────────────
    ok_results = [r for r in results if r.get("success")]
    fail_results = [r for r in results if not r.get("success")]

    if ok_results:
        confs         = [r["avg_conf"] for r in ok_results]
        fmt_counts    = [r["format_matches"] for r in ok_results]
        char_counts   = [r["char_count"] for r in ok_results]
        avg_conf_all  = round(sum(confs) / len(confs), 4)
        avg_fmt_all   = round(sum(fmt_counts) / len(fmt_counts), 2)
        min_conf      = round(min(confs), 4)
        max_conf      = round(max(confs), 4)
        above_075     = sum(1 for c in confs if c >= 0.75)
        above_080     = sum(1 for c in confs if c >= 0.80)
        delta_conf    = round(avg_conf_all - BASELINE_AVG_CONF, 4)
        delta_fmt     = round(avg_fmt_all - BASELINE_FORMAT_CNT, 2)
    else:
        avg_conf_all = avg_fmt_all = min_conf = max_conf = 0.0
        above_075 = above_080 = 0
        delta_conf = delta_fmt = 0.0

    now = datetime.now(timezone.utc).isoformat()

    # ── Per-file table rows ────────────────────────────────────────────────────
    table_rows = []
    for r in results:
        if r.get("success"):
            trend = "^" if r["avg_conf"] >= BASELINE_AVG_CONF else "v"
            row = (f"| {r['filename']} | {r['pages']} | "
                   f"{r['avg_conf']:.3f} {trend} | "
                   f"{r['format_matches']} | "
                   f"{r['char_count']} | "
                   f"{r['elapsed_s']}s | OK |")
        else:
            row = (f"| {r['filename']} | {r.get('pages', '?')} | "
                   f"N/A | N/A | N/A | {r.get('elapsed_s', '?')}s | FAIL |")
        table_rows.append(row)

    table_body = "\n".join(table_rows)

    failed_section = ""
    if fail_results:
        failed_section = "\n## ❌ Failed Invoices\n\n"
        for r in fail_results:
            failed_section += f"- **{r['filename']}**: `{r.get('error', 'unknown')}`\n"

    report_md = f"""# OCR Dataset Validation Report
**Phase 8/9 — Optimized Pipeline vs Baseline**

Generated: `{now}`

---

## Executive Summary

| Metric | Baseline | Optimized | Delta |
|---|---|---|---|
| Average Confidence | {BASELINE_AVG_CONF:.3f} | {avg_conf_all:.3f} | **{delta_conf:+.4f}** |
| Average Format Matches | {BASELINE_FORMAT_CNT} | {avg_fmt_all:.2f} | **{delta_fmt:+.2f}** |
| Invoices Above 0.75 Conf | — | {above_075}/{total_success} | — |
| Invoices Above 0.80 Conf | — | {above_080}/{total_success} | — |
| Min Confidence | — | {min_conf:.3f} | — |
| Max Confidence | — | {max_conf:.3f} | — |
| Success Rate | — | {total_success}/{len(results)} ({round(total_success/len(results)*100,1)}%) | — |

---

## Per-Invoice Results (Page 1 Only)

| Filename | Pages | Avg Conf | Fmt Matches | Chars | Time | Status |
|---|---|---|---|---|---|---|
{table_body}

> ▲ = above baseline ({BASELINE_AVG_CONF}), ▼ = below baseline
{failed_section}
---

## Configuration Used

| Parameter | Value |
|---|---|
| OCR_ADAPTIVE_PREPROCESS_ENABLED | true |
| OCR_CLAHE_CLIP_LIMIT | 2.0 |
| OCR_CLAHE_TILE_GRID_SIZE | 8 |
| OCR_SHARPEN_SIGMA | 3.0 |
| OCR_SHARPEN_WEIGHT | 1.5 |
| OCR_PAGE_RETRY_THRESHOLD | 0.75 |
| OCR_UPGRADE_DPI | 450 |
| OCR_BOX_RETRY_ENABLED | true |
| OCR_BOX_RETRY_THRESHOLD | 0.60 |
| OCR_BOX_RETRY_PADDING_PERCENT | 0.15 |

---

## Conclusion

{"✅ **IMPROVEMENT CONFIRMED**: The optimized pipeline shows a positive delta over the baseline on the full dataset." if delta_conf > 0 else "⚠️ **NO IMPROVEMENT**: The optimized pipeline did not improve over the baseline on this dataset."}

- Baseline average confidence: `{BASELINE_AVG_CONF}`
- Optimized average confidence: `{avg_conf_all:.4f}`  
- Confidence delta: `{delta_conf:+.4f}`
- Invoices tested: `{len(results)}` ({total_success} passed, {total_fail} failed)
"""

    out_path = os.path.join(OUTPUT_DIR, "OCR_DATASET_VALIDATION_REPORT.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print("\n" + "=" * 68)
    print(f"  VALIDATION COMPLETE")
    print(f"  Total invoices  : {len(results)}")
    print(f"  Succeeded       : {total_success}")
    print(f"  Failed          : {total_fail}")
    print(f"  Avg confidence  : {avg_conf_all:.4f} (baseline: {BASELINE_AVG_CONF})")
    print(f"  Delta           : {delta_conf:+.4f}")
    print(f"  Report written  : {out_path}")
    print("=" * 68)

    # Also save raw JSON for downstream use
    json_path = os.path.join(OUTPUT_DIR, "OCR_DATASET_VALIDATION_RAW.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": now,
            "baseline_avg_conf": BASELINE_AVG_CONF,
            "optimized_avg_conf": avg_conf_all,
            "delta_conf": delta_conf,
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"  Raw JSON        : {json_path}")

    return results


if __name__ == "__main__":
    run_validation()
