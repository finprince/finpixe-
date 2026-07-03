# PRODUCTION SINGLE-INVOICE FORENSIC TRACE

## 1. Executive Summary

This document presents a **100% read-only forensic trace** of the hand-written PDF invoice `Screenshot 2026-06-24 180236.pdf` as it executed end-to-end through the 15 production stages of the local billing pipeline. The record was processed under strict GPU compute and memory isolation guards on an **NVIDIA GeForce RTX 4050 Laptop GPU**.

The pipeline successfully moved the document from API ingestion to a `FINALIZED` database record (ID: `1008123`) in **141.2 seconds**. 

**Primary Finding:** The invoice failed arithmetic GST validation due to a **CGST/SGST total sum mismatch** (total GST is 2,520.00, but line items were normalization-resolved to 0.00% tax). This correctly routed the voucher into the `PENDING_PURCHASE` review pool.

---

## 2. Pipeline Execution Timeline

All events occurred on `2026-07-01`:
- **11:25:21**: POST request received by Django API (`CleanOCRStagingView`). File written to local disk.
- **11:25:22**: Database entry initialized with `status='INGESTING'` (Record ID `1008123`).
- **11:25:22**: SQS message dispatched to `ingestion` queue.
- **11:25:22**: Ingestion worker picks up task, renders page 1 to PNG, and executes PaddleOCR.
- **11:25:23**: LineBuilder groups bounding boxes into text lines.
- **11:25:34**: Ingestion worker finishes. Dispatches SQS task to `ai` queue.
- **11:25:35**: AI worker picks up task, starts local Ollama `qwen2.5vl:7b` vision inference.
- **11:27:45**: Qwen-VL model inference completes (**129.75s latency**). Output repaired and parsed.
- **11:27:45**: AI worker saves canonicalized payload to `InvoicePageResult` (ID `12471`). Dispatches to `assembly`.
- **11:27:45**: Assembly worker runs GST Validation Engine, flags CGST/SGST reconciliation failure.
- **11:27:45**: Finalization worker runs, compresses final snapshot to local cache. Record ID `1008123` transitions to `FINALIZED`.

---

## 3. Traced Fields - First Wrong Stage Analysis

### 3.1 header.invoice_number
- **Invoice Visual Value:** `VMT25-26/147`
- **OCR Recognized:** `5-26/47` (First wrong value)
- **LineBuilder:** `5-26/47`
- **AI Input:** `5-26/47`
- **Raw Qwen:** `VMT25-26/147` (Corrected back using visual model!)
- **Parsed JSON:** `VMT25-26/147`
- **Canonical:** `VMT25-26/147`
- **Normalized:** `VMT25-26/147`
- **Validator:** `VMT25-26/147`
- **Database:** `VMT25-26/147`
- **API Response:** `VMT25-26/147`
- **Frontend:** `VMT25-26/147`
- **First Corruption Stage:** **OCR Stage** (PaddleOCR misread visual characters, but Qwen-VL's vision encoder corrected it at the AI stage).

### 3.2 header.invoice_date
- **Invoice Visual Value:** `30-09-2025`
- **OCR Recognized:** `-04-` (First wrong value)
- **LineBuilder:** `-04-`
- **AI Input:** `-04-`
- **Raw Qwen:** `30-09-2025` (Corrected!)
- **Parsed JSON:** `30-09-2025`
- **Canonical:** `30-09-2025`
- **Normalized:** `30-09-2025`
- **Validator:** `30-09-2025`
- **Database:** `30-09-2025`
- **API Response:** `30-09-2025`
- **Frontend:** `30-09-2025`
- **First Corruption Stage:** **OCR Stage** (PaddleOCR misread visual characters, corrected at the AI stage).

### 3.3 header.vendor_name
- **Invoice Visual Value:** `ULTRA MACHINE TOOLS AND SERVICE`
- **OCR Recognized:** `ULTRA MACHINE TOOLS AND SERVICE`
- **LineBuilder:** `ULTRA MACHINE TOOLS AND SERVICE`
- **AI Input:** `ULTRA MACHINE TOOLS AND SERVICE`
- **Raw Qwen:** `ULTRA MACHINE TOOLS AND SERVICE`
- **Parsed JSON:** `ULTRA MACHINE TOOLS AND SERVICE`
- **Canonical:** `ULTRA MACHINE TOOLS AND SERVICE`
- **Normalized:** `ULTRA MACHINE TOOLS AND SERVICE`
- **Validator:** `ULTRA MACHINE TOOLS AND SERVICE`
- **Database:** `ULTRA MACHINE TOOLS AND SERVICE`
- **API Response:** `ULTRA MACHINE TOOLS AND SERVICE`
- **Frontend:** `ULTRA MACHINE TOOLS AND SERVICE`
- **First Corruption Stage:** None (100% correct).

### 3.4 header.vendor_gstin
- **Invoice Visual Value:** `33BTTPM6743D1ZF`
- **OCR Recognized:** `338TTP0674301ZF` (First wrong value)
- **LineBuilder:** `338TTP0674301ZF`
- **AI Input:** `338TTP0674301ZF`
- **Raw Qwen:** `33BTTPM6743D1ZF` (Corrected!)
- **Parsed JSON:** `33BTTPM6743D1ZF`
- **Canonical:** `33BTTPM6743D1ZF`
- **Normalized:** `33BTTPM6743D1ZF`
- **Validator:** `33BTTPM6743D1ZF`
- **Database:** `33BTTPM6743D1ZF`
- **API Response:** `33BTTPM6743D1ZF`
- **Frontend:** `33BTTPM6743D1ZF`
- **First Corruption Stage:** **OCR Stage** (PaddleOCR read `B` as `8` and `D` as `0`, corrected at the AI stage).

### 3.5 header.buyer_gstin
- **Invoice Visual Value:** `33AABCA5718R1ZD`
- **OCR Recognized:** `GSTNUD33AAA58` (First wrong value)
- **LineBuilder:** `GSTNUD33AAA58`
- **AI Input:** `GSTNUD33AAA58`
- **Raw Qwen:** `""` (Empty string)
- **Parsed JSON:** `""`
- **Canonical:** `""`
- **Normalized:** `""`
- **Validator:** `""`
- **Database:** `""`
- **API Response:** `""`
- **Frontend:** `""`
- **First Corruption Stage:** **OCR Stage** (PaddleOCR misrecognized input), propagating through AI as `""`.

### 3.6 Item 1 Description
- **Invoice Visual Value:** `Service charges for Penumatic Chuck and Penumatic tool Stock Service and function checking`
- **OCR Recognized:** `Serie ehans for Penumate ChuchordPenmeal slo 9957` (First wrong value)
- **LineBuilder:** `Serie ehans for Penumate ChuchordPenmeal slo 9957`
- **AI Input:** `Serie ehans for Penumate ChuchordPenmeal slo 9957`
- **Raw Qwen:** `Service charges for Penumatic Chuck and Penumatic tool Stock Service and function checking` (Corrected!)
- **Parsed JSON:** `Service charges for Penumatic Chuck and Penumatic tool Stock Service and function checking`
- **Canonical:** `Service charges for Penumatic Chuck and Penumatic tool Stock Service and function checking`
- **Normalized:** `SERVICE CHARGES FOR PENUMATIC CHUCK AND PENUMATIC TOOL STOCK SERVICE AND FUNCTION CHECKING`
- **Validator:** `SERVICE CHARGES FOR PENUMATIC CHUCK AND PENUMATIC TOOL STOCK SERVICE AND FUNCTION CHECKING`
- **Database:** `Service charges for Penumatic Chuck and Penumatic tool Stock Service and function checking`
- **API Response:** `Service charges for Penumatic Chuck and Penumatic tool Stock Service and function checking`
- **Frontend:** `Service charges for Penumatic Chuck and Penumatic tool Stock Service and function checking`
- **First Corruption Stage:** **OCR Stage** (PaddleOCR misread visual characters, corrected at the AI stage).

### 3.7 Item 1 HSN
- **Invoice Visual Value:** `998711`
- **OCR Recognized:** `9957` (First wrong value)
- **LineBuilder:** `9957`
- **AI Input:** `9957`
- **Raw Qwen:** `948711` (Alternative wrong value)
- **Parsed JSON:** `948711`
- **Canonical:** `948711`
- **Normalized:** `948711`
- **Validator:** `948711`
- **Database:** `948711`
- **API Response:** `948711`
- **Frontend:** `948711`
- **First Corruption Stage:** **OCR Stage** (OCR read as `9957`, AI read as `948711`).

### 3.8 Item 1 Quantity
- **Invoice Visual Value:** `-(blank)`
- **OCR Recognized:** `(blank)`
- **LineBuilder:** `(blank)`
- **AI Input:** `(blank)`
- **Raw Qwen:** `null`
- **Parsed JSON:** `null`
- **Canonical:** `0.0`
- **Normalized:** `1.0` (First wrong value - due to fallback defaults)
- **Validator:** `1.0`
- **Database:** `1.0`
- **API Response:** `1.0`
- **Frontend:** `1.0`
- **First Corruption Stage:** **Normalizer Stage** (Deliberate fallback logic set `qty = 1.0` since AI outputted `null`).

### 3.9 Item 1 Rate
- **Invoice Visual Value:** `-(blank)`
- **OCR Recognized:** `(blank)`
- **LineBuilder:** `(blank)`
- **AI Input:** `(blank)`
- **Raw Qwen:** `null`
- **Parsed JSON:** `null`
- **Canonical:** `0.0`
- **Normalized:** `3500.0` (First wrong value - due to fallback defaults)
- **Validator:** `3500.0`
- **Database:** `3500.0`
- **API Response:** `3500.0`
- **Frontend:** `3500.0`
- **First Corruption Stage:** **Normalizer Stage** (Fallback logic set `rate = taxable_value` since AI outputted `null`).

### 3.10 Item 1 Taxable Value
- **Invoice Visual Value:** `3500.00`
- **OCR Recognized:** `3500`
- **LineBuilder:** `3500`
- **AI Input:** `3500`
- **Raw Qwen:** `3500`
- **Parsed JSON:** `3500`
- **Canonical:** `3500.0`
- **Normalized:** `3500.0`
- **Validator:** `3500.0`
- **Database:** `3500.0`
- **API Response:** `3500.0`
- **Frontend:** `3500.0`
- **First Corruption Stage:** None (100% correct).

### 3.11 Item 1 CGST Amount
- **Invoice Visual Value:** `315.00` (inferred from 9% rate)
- **OCR Recognized:** `(blank)`
- **LineBuilder:** `(blank)`
- **AI Input:** `(blank)`
- **Raw Qwen:** `0.0` (First wrong value in database payload)
- **Parsed JSON:** `0.0`
- **Canonical:** `0.0`
- **Normalized:** `0.0`
- **Validator:** `0.0`
- **Database:** `0.0`
- **API Response:** `0.0`
- **Frontend:** `0.0`
- **First Corruption Stage:** **AI Inference Stage** (Ollama Qwen-VL failed to extract tax rate/amount per line item and returned `0.0` / `null`).

### 3.12 Item 1 SGST Amount
- **Invoice Visual Value:** `315.00` (inferred from 9% rate)
- **OCR Recognized:** `(blank)`
- **LineBuilder:** `(blank)`
- **AI Input:** `(blank)`
- **Raw Qwen:** `0.0` (First wrong value)
- **Parsed JSON:** `0.0`
- **Canonical:** `0.0`
- **Normalized:** `0.0`
- **Validator:** `0.0`
- **Database:** `0.0`
- **API Response:** `0.0`
- **Frontend:** `0.0`
- **First Corruption Stage:** **AI Inference Stage** (Failed to extract tax details on line items).

### 3.13 Item 1 IGST Amount
- **Invoice Visual Value:** `0.00` (inferred)
- **OCR Recognized:** `(blank)`
- **LineBuilder:** `(blank)`
- **AI Input:** `(blank)`
- **Raw Qwen:** `0.0`
- **Parsed JSON:** `0.0`
- **Canonical:** `0.0`
- **Normalized:** `0.0`
- **Validator:** `0.0`
- **Database:** `0.0`
- **API Response:** `0.0`
- **Frontend:** `0.0`
- **First Corruption Stage:** None (100% correct).

### 3.14 Item 1 Total Amount
- **Invoice Visual Value:** `4130.00` (3500 + 315 CGST + 315 SGST)
- **OCR Recognized:** `3500`
- **LineBuilder:** `3500`
- **AI Input:** `3500`
- **Raw Qwen:** `3500` (First wrong value)
- **Parsed JSON:** `3500`
- **Canonical:** `3500.0`
- **Normalized:** `3500.0`
- **Validator:** `3500.0`
- **Database:** `3500.0`
- **API Response:** `3500.0`
- **Frontend:** `3500.0`
- **First Corruption Stage:** **AI Inference Stage** (Extracted taxable value as total amount due to missing tax context).

### 3.15 Grand Total
- **Invoice Visual Value:** `16520.00`
- **OCR Recognized:** `(blank)`
- **LineBuilder:** `(blank)`
- **AI Input:** `(blank)`
- **Raw Qwen:** `16520`
- **Parsed JSON:** `16520`
- **Canonical:** `16520.0`
- **Normalized:** `16520.0`
- **Validator:** `16520.0`
- **Database:** `16520.0`
- **API Response:** `16520.0`
- **Frontend:** `16520.0`
- **First Corruption Stage:** None (100% correct).

---

## 4. Root Cause Analysis per Field

### 4.1 Item 1 HSN Code
1. **First Point of Failure:** OCR Stage (`9957`), and AI Stage (`948711`).
2. **First Incorrect Function:** `_extract_page_worker()` (PaddleOCR call).
3. **First Incorrect File:** `ocr_pipeline/isolated_ocr_service.py` at line 422.
4. **Why it happened:** Bounding box for handwritten HSN `998711` was messy. PaddleOCR misrecognized the characters as `'9957'`. Qwen-VL subsequently read the image crop as `948711`.
5. **Previous correct?** Yes, visual visual was `998711`.
6. **Propagation:** Yes, later stages (canonicalizer, normalizer, DB) simply copied the value `948711`.

### 4.2 Items 2-6 HSN Codes
1. **First Point of Failure:** AI Stage (Ollama extraction outputting `"11"`).
2. **First Incorrect Function:** `QwenProvider.call_single()`.
3. **First Incorrect File:** `core/providers/qwen_provider.py` at line 479.
4. **Why it happened:** The ditto marks `"` representing the HSN were misrecognized as `11` by the model due to visual similarity.
5. **Previous correct?** Yes, visual visual was `"`.
6. **Propagation:** Yes, normalizer and database copied `11`.

### 4.3 Buyer GSTIN
1. **First Point of Failure:** OCR Stage (PaddleOCR raw block detection).
2. **First Incorrect Function:** `_extract_page_worker()`.
3. **First Incorrect File:** `ocr_pipeline/isolated_ocr_service.py` at line 422.
4. **Why it happened:** Bounding box text `'GSTNUD33AAA58'` did not contain standard GSTIN format, causing Qwen-VL to output `""` to prevent validation errors.
5. **Previous correct?** Yes, visual visual was `33AABCA5718R1ZD`.
6. **Propagation:** Yes, database and UI mappings preserved `""`.

### 4.4 Item 4 Description
1. **First Point of Failure:** AI Stage.
2. **First Incorrect Function:** `QwenProvider.call_single()`.
3. **First Incorrect File:** `core/providers/qwen_provider.py` at line 479.
4. **Why it happened:** Messy handwritten words `"turret alignment"` and garbled layout text outputted by PaddleOCR caused the model to read it as `"turned alarm not"`.
5. **Previous correct?** Yes.
6. **Propagation:** Mapped directly to database and API outputs.

### 4.5 Line Item CGST / SGST Rates and Amounts
1. **First Point of Failure:** AI Stage (Extraction outputting `null`).
2. **First Incorrect Function:** `QwenProvider.call_single()`.
3. **First Incorrect File:** `core/providers/qwen_provider.py` at line 479.
4. **Why it happened:** The invoice layout has no tax rate/amount columns on a per-line basis (only totals at the bottom). Qwen-VL failed to propagate the 9% rate back onto individual items.
5. **Previous correct?** Yes, visually all service items are taxable at 9%.
6. **Propagation:** The normalizer set it to 0.0%, causing arithmetic reconciliation to fail.

---

## 5. Environment & Infrastructure Findings

During this forensic trace, an additional **major architectural issue** was discovered:

### Tier 2 DB Cache Failures (VARCHAR Column Constraint)
- **Log Entry:** `[OCR_CACHE_TIER2_WRITE_ERR] (1406, "Data too long for column 'key_hash' at row 1")`
- **Location:** `ocr_pipeline/ocr_cache.py` line 166.
- **Root Cause:** The database column `key_hash` in `ai_inference_cache` is defined as `varchar(64)`. However, the caching code attempts to save key hashes formatted as `ocr_page:{file_hash}:{page_number}:{timestamp}` which is **86 characters long**. This causes every DB write to fail, preventing Tier 2 persistence.
- **Impact:** Local development falls back to `LocMemCache` (Django's default memory cache). Because this is ephemeral, cached extractions are lost upon worker recycle or script execution in separate processes.

---

## 6. Final Conclusion

At exactly which production stage does each incorrect value first become incorrect?

1. **Buyer GSTIN (`""`):** First incorrect at the **OCR Stage** (PaddleOCR misread block).
2. **Item 1 HSN (`948711`):** First incorrect at the **OCR Stage** (PaddleOCR misread `998711` as `9957`).
3. **Items 2-6 HSN (`11`):** First incorrect at the **AI Stage** (Qwen-VL misread `"` ditto marks as `11`).
4. **Item 4 Description (`"turned alarm not"`):** First incorrect at the **AI Stage** (Qwen-VL misread handwriting).
5. **Line Item CGST/SGST Rates (`0.0%`):** First incorrect at the **AI Stage** (Qwen-VL failed to extract/propagate the tax rates per-item).
6. **Line Item Quantities (`1.0`):** First incorrect at the **Normalizer Stage** (system fallback rule replaced `null` with `1.0`).
7. **Line Item Rates (`3500.0`):** First incorrect at the **Normalizer Stage** (system fallback rule replaced `null` with taxable value).
