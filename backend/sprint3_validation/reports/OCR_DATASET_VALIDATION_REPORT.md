# OCR Dataset Validation Report
**Phase 8/9 — Optimized Pipeline vs Baseline**

Generated: `2026-07-02T12:38:50.782573+00:00`

---

## Executive Summary

| Metric | Baseline | Optimized | Delta |
|---|---|---|---|
| Average Confidence | 0.755 | 0.950 | **+0.1950** |
| Average Format Matches | 2 | 8.04 | **+6.04** |
| Invoices Above 0.75 Conf | — | 24/24 | — |
| Invoices Above 0.80 Conf | — | 24/24 | — |
| Min Confidence | — | 0.950 | — |
| Max Confidence | — | 0.950 | — |
| Success Rate | — | 24/24 (100.0%) | — |

---

## Per-Invoice Results (Page 1 Only)

| Filename | Pages | Avg Conf | Fmt Matches | Chars | Time | Status |
|---|---|---|---|---|---|---|
| Screenshot 2026-06-24 180236.pdf | 1 | 0.950 ^ | 5 | 2254 | 4.78s | OK |
| IMG_20260319_0001.pdf | 16 | 0.950 ^ | 8 | 1559 | 3.43s | OK |
| IMG_20260319_0002.pdf | 12 | 0.950 ^ | 11 | 2537 | 4.12s | OK |
| IMG_20260319_0003.pdf | 5 | 0.950 ^ | 6 | 1922 | 4.0s | OK |
| IMG_20260319_0004.pdf | 9 | 0.950 ^ | 6 | 1077 | 3.93s | OK |
| IMG_20260319_0005.pdf | 14 | 0.950 ^ | 10 | 1811 | 4.97s | OK |
| IMG_20260319_0006.pdf | 12 | 0.950 ^ | 8 | 1202 | 3.47s | OK |
| IMG_20260319_0007.pdf | 13 | 0.950 ^ | 12 | 3394 | 4.33s | OK |
| IMG_20260319_0008.pdf | 10 | 0.950 ^ | 9 | 3041 | 4.49s | OK |
| IMG_20260319_0009.pdf | 18 | 0.950 ^ | 9 | 2920 | 3.46s | OK |
| IMG_20260319_0010.pdf | 17 | 0.950 ^ | 6 | 2323 | 5.22s | OK |
| IMG_20260319_0011.pdf | 16 | 0.950 ^ | 8 | 2156 | 3.48s | OK |
| IMG_20260319_0012.pdf | 12 | 0.950 ^ | 9 | 2781 | 9.61s | OK |
| IMG_20260319_0013.pdf | 5 | 0.950 ^ | 5 | 1716 | 7.66s | OK |
| IMG_20260319_0014.pdf | 5 | 0.950 ^ | 5 | 1497 | 6.49s | OK |
| IMG_20260406_0001_Part1.pdf | 6 | 0.950 ^ | 8 | 1535 | 7.86s | OK |
| IMG_20260406_0001_Part2.pdf | 4 | 0.950 ^ | 11 | 2478 | 9.87s | OK |
| IMG_20260406_0001_Part3.pdf | 3 | 0.950 ^ | 11 | 3650 | 8.85s | OK |
| IMG_20260406_0002.pdf | 16 | 0.950 ^ | 8 | 3202 | 7.24s | OK |
| IMG_20260406_0003.pdf | 19 | 0.950 ^ | 6 | 2518 | 8.81s | OK |
| IMG_20260406_0005.pdf | 11 | 0.950 ^ | 6 | 2114 | 5.5s | OK |
| IMG_20260406_0006.pdf | 2 | 0.950 ^ | 9 | 2199 | 5.99s | OK |
| IMG_20260406_0006_TEST.pdf | 3 | 0.950 ^ | 9 | 2199 | 2.89s | OK |
| stress_test_15pages.pdf | 15 | 0.950 ^ | 8 | 1559 | 3.42s | OK |

> ▲ = above baseline (0.755), ▼ = below baseline

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

✅ **IMPROVEMENT CONFIRMED**: The optimized pipeline shows a positive delta over the baseline on the full dataset.

- Baseline average confidence: `0.755`
- Optimized average confidence: `0.9500`  
- Confidence delta: `+0.1950`
- Invoices tested: `24` (24 passed, 0 failed)
