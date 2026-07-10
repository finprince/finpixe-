# Production Single Invoice Forensic Validation Report

**Target Invoice:** `Screenshot 2026-06-24 180236.pdf`  
**Generated:** `2026-07-03T10:37:19.767102+00:00`  
**Pipeline:** Production (no code changes, no prompt changes)

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Pipeline Final Status | `COMPLETED` |
| Job ID | `5039437b-eebb-44f4-9495-965bedb045d9` |
| File Hash | `bf6410252a102954e2410b9ea5f0b39c...` |
| Staging Record ID | `1008208` |
| DB Validation Status | `PENDING_PURCHASE` |
| DB GSTIN Extracted | `33BTTPM6743D1ZF` |
| DB Invoice No Extracted | `` |
| Voucher Created | `None` |
| **Overall Extraction Accuracy** | **83.9%** (26/31 fields correct) |
| Header Field Accuracy | 92.3% |
| Item Field Accuracy | 77.8% |

---

## 2. Stage-by-Stage Execution Timeline

| Stage | Duration | Notes |
|-------|----------|-------|
| OCR (Mistral OCR) | 3.23s | avg_conf=0.950, boxes=5, chars=2254 |
| Invoice Upload (API) | 2.81s | HTTP 202 accepted |
| Pipeline Processing (poll) | 10.07s | Terminal: COMPLETED |
| DB Record Fetch | 0.05s | Record ID: 1008208 |
| **Total Wall Clock** | **21.54s** | |

---

## 3. OCR Stage Output

### 3.1 Raw OCR Text (first 800 chars)
```
# ULTRA MACHINE TOOLS AND SERVICE

SF No. 143/1, Villankurichi Road, Vinayagapuram, Saravanampatti, Coimbatore - 641 035

Mobile : 74025 82817

E-mail : vmahendran89@gmail.com

|  State : Tamilnadu |   | State Code : 33 |   | Invoice No. : VMT25-26/147  |   |   |   |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  GSTIN : 33BTTPM6743D1ZF |   |   |   | Invoice Date : 30-09-2025  |   |   |   |
|  Details of Receiver (Billed to) |   |   |   | Vehicle No. :  |   |   |   |
|  Name : ACCUTURN MACHINERS PVT LTD |   |   |   | Mode of Transport :  |   |   |   |
|  Address : 13A, Thaddekar to Kanuvai road. |   |   |   | E WAY BILL No. :  |   |   |   |
|  APPanaleen Palayam. |   |   |   | Place of Supply :  |   |   |   |
|  K. Vaidamadurai Post |   |   |   | Buyer Order No & Date :  |   |   |   
```

### 3.2 OCR Block Statistics
- Total blocks detected: **5**
- Average confidence: **0.9500**
- OCR fields extractable from raw text:
  - Invoice No: `VMT25-26/147`
  - Invoice Date: `30-09-2025`
  - GSTIN: `33BTTPM6743D1ZF`
  - Grand Total: `NOT FOUND`

---

## 4. Qwen AI Extraction Output (extracted_data)

### 4.1 Full extracted_data JSON (truncated at 3000 chars)
```json
{
  "sections": {},
  "bill_from": "SF No. 143/1, Villankurichi Road, Vinayagapuram, Saravanampatti, Coimbatore - 641 035",
  "billing_address": "ACCUTURN MACHINERS PVT LTD, 13A, Thaddekar to Kanuvai road.",
  "items": [
    {
      "qty": 1.0,
      "uom": "nos",
      "cgst": 315.0,
      "igst": 0.0,
      "rate": 3500.0,
      "sgst": 315.0,
      "hsn_sac": "998717",
      "raw_hsn": "998717",
      "hsn_code": "998717",
      "cess_rate": 0.0,
      "cgst_rate": 9.0,
      "igst_rate": 0.0,
      "item_code": "",
      "item_name": "Service charges for pneumatic chuck and pneumatic tail stock Service and function checking",
      "sgst_rate": 9.0,
      "line_index": 0,
      "description": "Service charges for pneumatic chuck and pneumatic tail stock Service and function checking",
      "item_status": "ALREADY EXIST",
      "match_source": null,
      "total_amount": 4130.0,
      "canonical_hsn": "998717",
      "raw_item_name": "Service charges for pneumatic chuck and pneumatic tail stock Service and function checking",
      "taxable_value": 3500.0,
      "canonical_name": "Service charges for pneumatic chuck and pneumatic tail stock Service and function checking",
      "computed_gst_rate": 0.0,
      "inventory_item_id": 41,
      "matched_item_name": null,
      "canonical_item_name": "Service charges for pneumatic chuck and pneumatic tail stock Service and function checking",
      "normalized_item_name": "SERVICE CHARGES FOR PNEUMATIC CHUCK AND PNEUMATIC TAIL STOCK SERVICE AND FUNCTION CHECKING",
      "inventory_match_level": "Master",
      "inventory_match_strategy": "HSN_NAME_MATCH",
      "inventory_match_confidence": 98.52941176470588
    },
    {
      "qty": 1.0,
      "uom": "nos",
      "cgst": 225.0,
      "igst": 0.0,
      "rate": 2500.0,
      "sgst": 225.0,
      "hsn_sac": "998717",
      "raw_hsn": "998717",
      "hsn_code": "998717",
      "cess_rate": 0.0,
      "cgst_rate": 9.0,
      "igst_rate": 0.0,
      "item_code": "",
      "item_name": "Service charges for Leveling and function checking for Low Smarter",
      "sgst_rate": 9.0,
      "line_index": 1,
      "description": "Service charges for Leveling and function checking for Low Smarter",
      "item_status": "ALREADY EXIST",
      "match_source": null,
      "total_amount": 2950.0,
      "canonical_hsn": "998717",
      "raw_item_name": "Service charges for Leveling and function checking for Low Smarter",
      "taxable_value": 2500.0,
      "canonical_name": "Service charges for Leveling and function checking for Low Smarter",
      "computed_gst_rate": 0.0,
      "inventory_item_id": 42,
      "matched_item_name": null,
      "canonical_item_name": "Service charges for Leveling and function checking for Low Smarter",
      "normalized_item_name": "SERVICE CHARGES FOR LEVELING AND FUNCTION CHECKING FOR LOW SMARTER",
      "inventory_match_level": "Master",
      "inventory_match_strategy": "HSN_NAME_MATCH",
      "inventory_match_confidence": 94.308
```

### 4.2 Qwen Key Fields
- Invoice No: `VMT25-26/147`
- Invoice Date: `30-09-2025`
- Vendor Name: `ULTRA MACHINE TOOLS AND SERVICE`
- Vendor GSTIN: `33BTTPM6743D1ZF`
- Buyer Name: `ACCUTURN MACHINERS PVT LTD`
- Buyer GSTIN: `33ABACA5718R1ZD`
- Subtotal: `14000.0`
- CGST: `9.0%` → `1260.0`
- SGST: `9.0%` → `1260.0`
- IGST: `0.0`
- Grand Total: `16520.0`
- Items extracted: `6`

---

## 5. Database Values (InvoiceOCRTemp)

| DB Field | Value |
|----------|-------|
| id | `1008208` |
| status | `FINALIZED` |
| validation_status | `PENDING_PURCHASE` |
| vendor_status | `NEW` |
| gstin (normalized) | `33BTTPM6743D1ZF` |
| supplier_invoice_no | `?` |
| normalized_invoice_no | `?` |
| vendor_id | `None` |
| voucher_id | `?` |
| branch | `COIMBATORE` |
| vendor_confidence | `?` |
| gstin_confidence | `?` |

---

## 6. API Response

API record fetched from: `GET /api/ocr-staging/1008208/`

| API Field | Value |
|-----------|-------|
| invoice_no (extracted) | `VMT25-26/147` |
| vendor_gstin (extracted) | `33BTTPM6743D1ZF` |
| grand_total (extracted) | `16520.0` |

---

## 7. Field-by-Field Trace Table (Header + Totals)

| Field | Ground Truth | OCR Raw | Qwen | DB | API | Status | First Error Stage |
|-------|-------------|---------|------|----|-----|--------|-------------------|
| invoice_no | `VMT25-26/147` | `VMT25-26/147` | `VMT25-26/147` | `MISSING` | `VMT25-26/147` | OK | DATABASE |
| invoice_date | `30-09-2025` | `30-09-2025` | `30-09-2025` | `MISSING` | `30-09-2025` | OK | DATABASE |
| vendor_name | `ULTRA MACHINE TOOLS AND SERVICE` | `MISSING` | `ULTRA MACHINE TOOLS AND SERVICE` | `MISSING` | `ULTRA MACHINE TOOLS AND SERVICE` | OK | DATABASE |
| vendor_gstin | `33BTTPM6743D1ZF` | `33BTTPM6743D1ZF` | `33BTTPM6743D1ZF` | `33BTTPM6743D1ZF` | `33BTTPM6743D1ZF` | OK | NONE |
| buyer_name | `ACCUTURN MACHINERS PVT LTD` | `MISSING` | `ACCUTURN MACHINERS PVT LTD` | `MISSING` | `ACCUTURN MACHINERS PVT LTD` | OK | DATABASE |
| buyer_gstin | `33AABCA5718R1ZD` | `MISSING` | `33ABACA5718R1ZD` | `MISSING` | `33ABACA5718R1ZD` | FAIL | OCR_DETECTION or QWEN |
| subtotal | `14000` | `MISSING` | `14000.0` | `MISSING` | `14000.0` | OK | DATABASE |
| cgst_rate | `9.0` | `MISSING` | `9.0` | `MISSING` | `9.0` | OK | DATABASE |
| cgst_amount | `1260.0` | `MISSING` | `1260.0` | `MISSING` | `1260.0` | OK | DATABASE |
| sgst_rate | `9.0` | `MISSING` | `9.0` | `MISSING` | `9.0` | OK | DATABASE |
| sgst_amount | `1260.0` | `MISSING` | `1260.0` | `MISSING` | `1260.0` | OK | DATABASE |
| igst_amount | `0.0` | `MISSING` | `0.0` | `MISSING` | `0.0` | OK | DATABASE |
| grand_total | `16520.0` | `MISSING` | `16520.0` | `MISSING` | `16520.0` | OK | DATABASE |

---

## 8. Line Items Trace

| # | GT HSN | Qwen HSN | HSN | GT Desc (50c) | Qwen Desc (50c) | Desc | GT Amount | Qwen Amount | Amt |
|---|--------|----------|-----|---------------|-----------------|------|-----------|-------------|-----|
| 1 | `998711` | `998717` | OK | `Service Charges for Penumatic Chuck` | `Service charges for pneumatic chuck` | FAIL | `3500` | `3500.0` | OK |
| 2 | `998711` | `998717` | OK | `Service charges for Leveling and fu` | `Service charges for Leveling and fu` | OK | `2500` | `2500.0` | OK |
| 3 | `998711` | `998717` | OK | `Service charges for CET not on for ` | `Service charges for CRT not on for ` | FAIL | `1500` | `1500.0` | OK |
| 4 | `998711` | `998717` | OK | `Service charges for turnet alignmen` | `Service charges for turnout alignme` | FAIL | `3500` | `3500.0` | OK |
| 5 | `998711` | `998717` | OK | `Service charges for ATC Problem for` | `Service charges for APC Problem for` | FAIL | `1500` | `1500.0` | OK |
| 6 | `998711` | `998717` | OK | `Service charges for APC alarm batte` | `Service charges for APC alarm batte` | OK | `1500` | `1500.0` | OK |

---

## 9. Root Cause Analysis

### Incorrect Fields (header/totals)
- **buyer_gstin**: Ground truth=`33AABCA5718R1ZD`, Qwen=`33ABACA5718R1ZD`, OCR=`` → First error: **OCR_DETECTION or QWEN**

### Incorrect Item Fields
- Item 1 Description
- Item 3 Description
- Item 4 Description
- Item 5 Description

---

## 10. Accuracy Summary

| Stage | Correct / Total | Accuracy |
|-------|----------------|---------|
| OCR (key field detection) | 2/2 | 100.0% |
| Qwen AI Extraction (header) | 12/13 | 92.3% |
| Qwen AI Extraction (items) | 14/18 | 77.8% |
| **End-to-End Overall** | **26/31** | **83.9%** |

---

## 11. Log Warnings (last 30 from backend logs)

  (no warnings captured)

---

## 12. Silent Data Corruption Check

| Check | Result |
|-------|--------|
| GSTIN format valid (vendor) | `NO — 33BTTPM6743D1ZF` |
| GSTIN format valid (buyer) | `NO — 33ABACA5718R1ZD` |
| Grand Total matches expected | `YES` |
| Hallucinated GSTIN | `NONE` |
| Null invoice_no | `NO` |
| Tax arithmetic (CGST+SGST+Sub=Total) | `OK (14000.0+1260.0+1260.0=16520.0)` |

---

## 13. Final Answers

1. **Real end-to-end extraction accuracy:** **83.9%** (26/31 fields)
2. **First error stage:** QWEN (if header fields incorrect)
3. **Is OCR still primary bottleneck?** OCR avg_conf=0.950 (well above 0.75 threshold). OCR quality has improved significantly. Primary bottleneck is now Qwen extraction accuracy.
4. **Is Qwen still introducing errors?** YES — 1 header fields incorrect
5. **Errors after Qwen?** NONE detected at DB/API level
6. **Remaining incorrect fields:** buyer_gstin; Items: Item 1 Description, Item 3 Description, Item 4 Description, Item 5 Description
7. **Barrier to >97% accuracy:** Qwen description accuracy and buyer GSTIN extraction
8. **Highest-ROI remaining improvement:** Buyer GSTIN extraction improvement in Qwen prompt

---

## 14. Production Readiness Verdict

Pipeline Status: `COMPLETED`  
Overall Accuracy: **83.9%**

> [!NOTE]  
> **ACCEPTABLE — CONTINUE MONITORING**: End-to-end extraction accuracy is 83.9%. Target is >97%.

---

*Generated by Production Forensic Validation Script — Read-only, no code modifications.*
