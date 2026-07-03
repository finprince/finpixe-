# OCR BASELINE REPORT

## 1. Document & Execution Metadata
- **Target Invoice:** `Screenshot 2026-06-24 180236.pdf`
- **Environment:** Local GPU/CPU Hybrid on `LAPTOP-601O6S3T`
- **DPI:** 350 (Production standard)
- **Execution Date:** 2026-07-01 11:25:21

---

## 2. Baseline Accuracy & Error Rates

### 2.1 Field Error Rates (Raw OCR vs Ground Truth)
| Field | Ground Truth | Raw OCR Recognized | CER | WER | Status |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Invoice No** | `VMT25-26/147` | `'5-26/47'` | 0.42 | 1.00 | Miss |
| **Invoice Date**| `30-09-2025` | `'-04-'` | 0.70 | 1.00 | Miss |
| **Vendor Name** | `ULTRA MACHINE TOOLS...` | `'ULTRA MACHINE TOOLS AND SERVICE'`| 0.00 | 0.00 | Match |
| **Vendor GSTIN**| `33BTTPM6743D1ZF` | `'GSTN:338TTP0674301ZF'`| 0.53 | 1.00 | Miss |
| **Buyer GSTIN** | `33AABCA5718R1ZD` | `'GSTNUD33AAA58'` | 0.93 | 1.00 | Miss |
| **Item 1 HSN** | `998711` | `'9957'` | 0.50 | 1.00 | Miss |
| **Item 4 Desc** | `"Service charges..."` | `'e ch f tn alynma'` | 0.85 | 1.00 | Miss |
| **Quantity** | `-(blank)` | `(blank)` | 0.00 | 0.00 | Match |
| **Rate** | `-(blank)` | `(blank)` | 0.00 | 0.00 | Match |
| **Taxable Val** | `3500` | `'3500'` | 0.00 | 0.00 | Match |
| **CGST Amount** | `315` | `(blank)` | 1.00 | 1.00 | Miss |
| **SGST Amount** | `315` | `(blank)` | 1.00 | 1.00 | Miss |
| **Grand Total** | `16520` | `'16520'` (Bottom total section) | 0.00 | 0.00 | Match |

**Overall Raw OCR Field Accuracy:** **38.5%** (5 / 13 fields correct).

### 2.2 OCR Recognition Confidences
- **Invoice No Box:** `0.861`
- **Vendor GSTIN Box:** `0.788`
- **Invoice Date Box:** `0.718`
- **Buyer GSTIN Box:** `0.708`
- **Item 1 HSN Box:** `0.571`
- **Ditto Marks Box:** `0.524`

---

## 3. Resource & Performance Metrics
- **Total Pipeline Latency:** 146.42 seconds
  - **OCR Stage Latency:** 5.37 seconds
  - **AI Inference Latency:** 141.05 seconds
- **CPU Utilization:** Peak 24.3% during rendering
- **RAM Usage:** Peak 3.84 GB
- **GPU Utilization:** Peak 98.4% during Qwen execution
- **VRAM Usage:** Peak 4.87 GB (out of 6.14 GB total available)
