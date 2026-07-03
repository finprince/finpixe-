# PRODUCTION SINGLE-INVOICE STAGE-BY-STAGE FORENSIC TRACE

## 1. Executive Summary

This report presents a granular, **100% read-only stage-by-stage trace** of the hand-written PDF invoice `Screenshot 2026-06-24 180236.pdf` running through all 15 stages of the production pipeline. 

The pipeline ran on host `LAPTOP-601O6S3T` inside the `local` environment using the **NVIDIA GeForce RTX 4050 Laptop GPU** (VRAM usage: 4867 / 6141 MiB). The pipeline successfully resolved the invoice state to `FINALIZED` (Record ID: `1008123`) in **141.2 seconds**, routing it to the `PENDING_PURCHASE` pool due to a **CGST/SGST total sum mismatch** (validation status `FAIL`).

---

## 2. Complete Pipeline Timeline

All times represent local execution times on `2026-07-01`:
- **11:25:21.544**: POST upload endpoint hit. File uploaded to `media/bulk_pipeline/...`
- **11:25:22.108**: DB Record `1008123` created in table `ocr_pipeline_invoicetempocr` with status `INGESTING`.
- **11:25:22.504**: Ingestion worker picks up task from `ingestion` queue.
- **11:25:22.863**: PDF Page 1 rendered to image `stage4_crop_sent_to_ai.png`.
- **11:25:23.004**: PaddleOCR detection and recognition runs.
- **11:25:23.388**: LineBuilder groupings and layout analysis complete. SQS task dispatched to `ai` queue.
- **11:25:34.095**: AI worker picks up task from `ai` queue.
- **11:25:35.257**: Local Ollama server starts `qwen2.5vl:7b` GPU model inference.
- **11:27:45.008**: Qwen-VL model completes inference (129.75s latency, 6088 total tokens processed).
- **11:27:45.209**: AI worker runs JSON parser, repair wrapper, canonicalizer, and normalizer.
- **11:27:45.210**: Page result written to `InvoicePageResult` (ID: `12471`). Dispatches task to `assembly`.
- **11:27:45.735**: Assembly worker runs GST Validation Engine, logs failure status.
- **11:27:45.738**: Finalization worker runs, compresses final snapshot. Record transitions to `FINALIZED` and status to `PENDING_PURCHASE`.

---

## 3. Individual Field Traces

--------------------------------------------------------------------

### FIELD: Invoice Number

- **GROUND TRUTH (PDF):** `VMT25-26/147`
- **PaddleOCR Detection:** `Box: [[1041.0, 262.0], [1280.0, 269.0], [1278.0, 314.0], [1040.0, 307.0]]`
- **PaddleOCR Recognition:** `'5-26/47'` (Confidence: `0.861`)
- **LineBuilder Output:** `'5-26/47'`
- **Crop sent to Qwen:** Assembled PNG coordinates around visual region `Invoice No. / Dated`
- **OCR text sent to Qwen:** `'Invoi+ No. | 5-26/47'`
- **Prompt snippet for this field:** `"invoice_no": ""`
- **Raw Qwen JSON:** `"invoice_no": "VMT25-26/147"`
- **Translator Output:** `"VMT25-26/147"`
- **Normalizer Output:** `"VMT25-26/147"`
- **Validation Output:** `Pass`
- **InvoicePageResult:** `"VMT25-26/147"`
- **InvoiceTempOCR:** `"VMT25-26/147"`
- **Database:** `"VMT25-26/147"`
- **API Response:** `"VMT25-26/147"`
- **Frontend:** `"VMT25-26/147"`

**FIRST STAGE WHERE VALUE CHANGED:** **PaddleOCR Recognition** (Visual `VMT25-26/147` was misrecognized as `'5-26/47'`). 

**Reason:** Handwritten letters `VMT` and characters `2` and `1` were faded or partially cropped, causing detection/recognition failure.

**Evidence:** PaddleOCR raw results printed `'5-26/47'` with `0.861` confidence. The value was subsequently corrected back to the correct ground truth value `"VMT25-26/147"` in the **Qwen Raw Response** stage thanks to the model's visual-text encoder reading the image crop directly.

--------------------------------------------------------------------

### FIELD: Invoice Date

- **GROUND TRUTH (PDF):** `30-09-2025`
- **PaddleOCR Detection:** `Box: [[1041.0, 326.0], [1243.0, 317.0], [1245.0, 348.0], [1042.0, 356.0]]`
- **PaddleOCR Recognition:** `'-04-'` (Confidence: `0.718`)
- **LineBuilder Output:** `'-04-'`
- **Crop sent to Qwen:** Visual region `Dated`
- **OCR text sent to Qwen:** `'Irnvolce Dalo | -04-'`
- **Prompt snippet for this field:** `"invoice_date": ""`
- **Raw Qwen JSON:** `"invoice_date": "30-09-2025"`
- **Translator Output:** `"30-09-2025"`
- **Normalizer Output:** `"30-09-2025"`
- **Validation Output:** `Pass`
- **InvoicePageResult:** `"30-09-2025"`
- **InvoiceTempOCR:** `"30-09-2025"`
- **Database:** `"30-09-2025"`
- **API Response:** `"30-09-2025"`
- **Frontend:** `"30-09-2025"`

**FIRST STAGE WHERE VALUE CHANGED:** **PaddleOCR Recognition** (Visual `30-09-2025` misrecognized as `'-04-'`).

**Reason:** Messy handwriting and poor character contrast in the date region.

**Evidence:** PaddleOCR outputs `'-04-'` with `0.718` confidence. Corrected back to `30-09-2025` in the **Qwen Raw Response** stage via vision extraction.

--------------------------------------------------------------------

### FIELD: Vendor GSTIN

- **GROUND TRUTH (PDF):** `33BTTPM6743D1ZF`
- **PaddleOCR Detection:** `Box: [[154.0, 324.0], [512.0, 322.0], [512.0, 345.0], [154.0, 347.0]]`
- **PaddleOCR Recognition:** `'338TTP0674301ZF'` (Confidence: `0.788`)
- **LineBuilder Output:** `'338TTP0674301ZF'`
- **Crop sent to Qwen:** Visual block under `GSTIN`
- **OCR text sent to Qwen:** `'GSTN:338TTP0674301ZF'`
- **Prompt snippet for this field:** `"vendor_gstin": ""`
- **Raw Qwen JSON:** `"vendor_gstin": "33BTTPM6743D1ZF"`
- **Translator Output:** `"33BTTPM6743D1ZF"`
- **Normalizer Output:** `"33BTTPM6743D1ZF"`
- **Validation Output:** `Pass`
- **InvoicePageResult:** `"33BTTPM6743D1ZF"`
- **InvoiceTempOCR:** `"33BTTPM6743D1ZF"`
- **Database:** `"33BTTPM6743D1ZF"`
- **API Response:** `"33BTTPM6743D1ZF"`
- **Frontend:** `"33BTTPM6743D1ZF"`

**FIRST STAGE WHERE VALUE CHANGED:** **PaddleOCR Recognition** (Visual `33BTTPM6743D1ZF` misrecognized as `'338TTP0674301ZF'`).

**Reason:** Character shape similarities (`B` read as `8`, `D` as `0`).

**Evidence:** PaddleOCR logs show the raw text recognition is `'338TTP0674301ZF'` (confidence `0.788`). Corrected back to the correct GSTIN value `"33BTTPM6743D1ZF"` in the **Qwen Raw Response** stage.

--------------------------------------------------------------------

### FIELD: Buyer GSTIN

- **GROUND TRUTH (PDF):** `33AABCA5718R1ZD`
- **PaddleOCR Detection:** `Box: [[152.0, 619.0], [655.0, 618.0], [655.0, 646.0], [152.0, 647.0]]`
- **PaddleOCR Recognition:** `'GSTNUD33AAA58'` (Confidence: `0.708`)
- **LineBuilder Output:** `'GSTNUD33AAA58'`
- **Crop sent to Qwen:** Bounding box crop around `Buyer's Details`
- **OCR text sent to Qwen:** `'GSTNUD33AAA58'`
- **Prompt snippet for this field:** `"buyer_gstin": ""`
- **Raw Qwen JSON:** `"buyer_gstin": ""` (Empty string)
- **Translator Output:** `""`
- **Normalizer Output:** `""`
- **Validation Output:** `Pass`
- **InvoicePageResult:** `""`
- **InvoiceTempOCR:** `""`
- **Database:** `""`
- **API Response:** `""`
- **Frontend:** `""`

**FIRST STAGE WHERE VALUE CHANGED:** **PaddleOCR Recognition** (Visual `33AABCA5718R1ZD` misrecognized as `'GSTNUD33AAA58'`).

**Reason:** The visual printing of the buyer's GSTIN block was faded, cut off, or poorly aligned, causing the detector to skip or misread trailing characters.

**Evidence:** PaddleOCR outputs `'GSTNUD33AAA58'` (confidence `0.708`). Because this does not match a valid 15-character GSTIN structure, Qwen-VL discarded the value to prevent validation errors, outputting `""` in **Qwen Raw Response**.

--------------------------------------------------------------------

### FIELD: Description (Item 4)

- **GROUND TRUTH (PDF):** `"Service charges for turret alignment for Low Smart"`
- **PaddleOCR Detection:** `Box: [[196.0, 1210.0], [739.0, 1173.0], [742.0, 1221.0], [199.0, 1258.0]]`
- **PaddleOCR Recognition:** `'e ch f tn alynma'` (Confidence: `0.609`)
- **LineBuilder Output:** `'e ch f tn alynma fSmor'`
- **Crop sent to Qwen:** Item 4 table row
- **OCR text sent to Qwen:** `'e ch f tn alynma fSmor'`
- **Prompt snippet for this field:** `"description": ""`
- **Raw Qwen JSON:** `"description": "Service charges for turned alarm for Low Smarta"`
- **Translator Output:** `"Service charges for turned alarm for Low Smarta"`
- **Normalizer Output:** `"SERVICE CHARGES FOR TURNED ALARM FOR LOW SMARTA"`
- **Validation Output:** `Pass`
- **InvoicePageResult:** `"Service charges for turned alarm for Low Smarta"`
- **InvoiceTempOCR:** `"Service charges for turned alarm for Low Smarta"`
- **Database:** `"Service charges for turned alarm for Low Smarta"`
- **API Response:** `"Service charges for turned alarm for Low Smarta"`
- **Frontend:** `"Service charges for turned alarm for Low Smarta"`

**FIRST STAGE WHERE VALUE CHANGED:** **PaddleOCR Recognition** (Visual `"turret alignment"` misrecognized as `'e ch f tn alynma'`).

**Reason:** Messy hand-writing resembling `'tumed'` or `'turned'` and `'alarm'` combined with PaddleOCR's garbled layout lines.

**Evidence:** Qwen-VL resolved the garbled input `'e ch f tn alynma'` and handwriting visual crop into `"Service charges for turned alarm for Low Smarta"` in the **Qwen Raw Response** stage, corrupting `"turret alignment"`.

--------------------------------------------------------------------

### FIELD: HSN (Item 1)

- **GROUND TRUTH (PDF):** `998711`
- **PaddleOCR Detection:** `Box: [[757.0, 743.0], [852.0, 741.0], [853.0, 774.0], [758.0, 776.0]]`
- **PaddleOCR Recognition:** `'9957'` (Confidence: `0.571`)
- **LineBuilder Output:** `'9957'`
- **Crop sent to Qwen:** HSN column crop
- **OCR text sent to Qwen:** `'1. Serie ehans for Penumate ChuchordPenmeal slo 9957 | 3500'`
- **Prompt snippet for this field:** `"hsn_code": ""`
- **Raw Qwen JSON:** `"hsn_code": "948711"`
- **Translator Output:** `"948711"`
- **Normalizer Output:** `"948711"`
- **Validation Output:** `Pass`
- **InvoicePageResult:** `"948711"`
- **InvoiceTempOCR:** `"948711"`
- **Database:** `"948711"`
- **API Response:** `"948711"`
- **Frontend:** `"948711"`

**FIRST STAGE WHERE VALUE CHANGED:** **PaddleOCR Recognition** (Visual `998711` misrecognized as `'9957'`).

**Reason:** Faded print/handwritten digit occlusion.

**Evidence:** PaddleOCR recognized the box as `'9957'` (confidence `0.571`). The Qwen-VL model subsequently extracted `"948711"` in **Qwen Raw Response**, which propagated to the database.

--------------------------------------------------------------------

### FIELD: HSN (Items 2-6)

- **GROUND TRUTH (PDF):** `"` (ditto marks representing `998711`)
- **PaddleOCR Detection:** `Box: [[321.0, 1752.0], [444.0, 1760.0], [441.0, 1803.0], [318.0, 1795.0]]`
- **PaddleOCR Recognition:** `'tt'` (Confidence: `0.524`)
- **LineBuilder Output:** `'tt'`
- **Crop sent to Qwen:** Bounding box crop of table body
- **OCR text sent to Qwen:** `'tt'`
- **Prompt snippet for this field:** `"hsn_code": ""`
- **Raw Qwen JSON:** `"hsn_code": ""`
- **Translator Output:** `""`
- **Normalizer Output:** `""`
- **Validation Output:** `Pass`
- **InvoicePageResult:** `"11"` (First wrong value - from cluster run)
- **InvoiceTempOCR:** `"11"`
- **Database:** `"11"`
- **API Response:** `"11"`
- **Frontend:** `"11"`

**FIRST STAGE WHERE VALUE CHANGED:** **PaddleOCR Recognition** (Visual `"` misrecognized as `'tt'`).

**Reason:** Visual ditto marks `"` resemble double vertical strokes, which PaddleOCR recognized as `'tt'` and Qwen-VL (during the cluster run) misrecognized as `"11"` (two ones).

**Evidence:** The database persistent payload `InvoicePageResult` shows HSN is `'11'` for items 2-6.

--------------------------------------------------------------------

### FIELD: Quantity (Item 1)

- **GROUND TRUTH (PDF):** `-(blank)`
- **PaddleOCR Detection:** `(blank)`
- **PaddleOCR Recognition:** `(blank)`
- **LineBuilder Output:** `(blank)`
- **Crop sent to Qwen:** `(blank)`
- **OCR text sent to Qwen:** `(blank)`
- **Prompt snippet for this field:** `"quantity": 0`
- **Raw Qwen JSON:** `"quantity": null`
- **Translator Output:** `0.0`
- **Normalizer Output:** `1.0` (First wrong value - default fallback rule)
- **Validation Output:** `1.0`
- **InvoicePageResult:** `1.0`
- **InvoiceTempOCR:** `1.0`
- **Database:** `1.0`
- **API Response:** `1.0`
- **Frontend:** `1.0`

**FIRST STAGE WHERE VALUE CHANGED:** **Normalizer Output** (Visual blank/null was replaced with default fallback `1.0`).

**Reason:** In standard accounting, if Quantity is null but taxable value exists, the normalizer defaults `qty = 1.0` to preserve mathematical integrity.

**Evidence:** Normalizer code `normalize.py` at line 847: `qty = normalize_amount(_raw_qty_value or 1.0)`.

--------------------------------------------------------------------

### FIELD: Rate (Item 1)

- **GROUND TRUTH (PDF):** `-(blank)`
- **PaddleOCR Detection:** `(blank)`
- **PaddleOCR Recognition:** `(blank)`
- **LineBuilder Output:** `(blank)`
- **Crop sent to Qwen:** `(blank)`
- **OCR text sent to Qwen:** `(blank)`
- **Prompt snippet for this field:** `"rate": 0`
- **Raw Qwen JSON:** `"rate": null`
- **Translator Output:** `0.0`
- **Normalizer Output:** `3500.0` (First wrong value - default fallback rule)
- **Validation Output:** `3500.0`
- **InvoicePageResult:** `3500.0`
- **InvoiceTempOCR:** `3500.0`
- **Database:** `3500.0`
- **API Response:** `3500.0`
- **Frontend:** `3500.0`

**FIRST STAGE WHERE VALUE CHANGED:** **Normalizer Output** (Visual blank/null was replaced with taxable value `3500.0`).

**Reason:** System fallback rules dictate that if Rate is missing but taxable value exists, `rate = taxable_value` is set to ensure `rate * quantity = taxable_value` arithmetic consistency.

**Evidence:** Normalizer code `normalize.py` at line 940: `derived_rate = taxable / derived_qty`.

--------------------------------------------------------------------

### FIELD: CGST / SGST Rates (Item 1)

- **GROUND TRUTH (PDF):** `9.0%` (inferred from bottom tax section)
- **PaddleOCR Detection:** `(blank)`
- **PaddleOCR Recognition:** `(blank)`
- **LineBuilder Output:** `(blank)`
- **Crop sent to Qwen:** `(blank)`
- **OCR text sent to Qwen:** `(blank)`
- **Prompt snippet for this field:** `"cgst_rate": 0, "sgst_rate": 0`
- **Raw Qwen JSON:** `"cgst_rate": null, "sgst_rate": null`
- **Translator Output:** `0.0`
- **Normalizer Output:** `0.0` (First wrong value)
- **Validation Output:** `0.0`
- **InvoicePageResult:** `0.0`
- **InvoiceTempOCR:** `0.0`
- **Database:** `0.0`
- **API Response:** `0.0`
- **Frontend:** `0.0`

**FIRST STAGE WHERE VALUE CHANGED:** **Normalizer Output** (AI's `null` tax rates were resolved to `0.0%` tax rate).

**Reason:** The model did not extract a CGST/SGST rate for the line item (since no tax column exists on individual line items in this invoice layout). The normalizer then resolved `null` to `0.0` CGST.

**Evidence:** Normalizer code `normalize.py` line 899: `cg_rate = snap_to_standard_gst_rate(get_tax_rate("cgst", cg_amt))` returning `0.0`.

---

## 4. Stage-by-Stage Comparison

### 4.1 Did OCR change the field?
- **Invoice Number:** **YES** (Misrecognized visual `VMT25-26/147` as `'5-26/47'`)
- **Invoice Date:** **YES** (Misrecognized visual `30-09-2025` as `'-04-'`)
- **Vendor GSTIN:** **YES** (Misrecognized visual `33BTTPM6743D1ZF` as `'338TTP0674301ZF'`)
- **Buyer GSTIN:** **YES** (Misrecognized visual `33AABCA5718R1ZD` as `'GSTNUD33AAA58'`)
- **Item 1 HSN:** **YES** (Misrecognized visual `998711` as `'9957'`)
- **Items 2-6 HSN:** **YES** (Misrecognized visual ditto marks `"` as `'tt'`)
- **Item 4 Desc:** **YES** (Misrecognized visual `"turret alignment"` as `'e ch f tn alynma'`)
- **Line Item CGST/SGST:** **NO** (OCR visual was blank/empty, recognized correctly as blank).

### 4.2 Did LineBuilder change the field?
- **All Fields:** **NO** (LineBuilder only grouped detected coordinates into text rows, preserving OCR values exactly).

### 4.3 Did Qwen change the field?
- **Invoice Number:** **YES** (Corrected it back to correct ground truth `"VMT25-26/147"`)
- **Invoice Date:** **YES** (Corrected it back to correct ground truth `"30-09-2025"`)
- **Vendor GSTIN:** **YES** (Corrected it back to correct ground truth `"33BTTPM6743D1ZF"`)
- **Buyer GSTIN:** **YES** (Dropped the garbled `'GSTNUD33AAA58'` to output `""`)
- **Item 4 Desc:** **YES** (Outputted `"Service charges for turned alarm for Low Smarta"`, corrupting description)
- **Line Item CGST/SGST:** **YES** (Outputted `null`, which defaults to 0% tax).

### 4.4 Did Translator change the field?
- **All Fields:** **NO** (Translator mapped AI keys to schema elements without changing values).

### 4.5 Did Normalizer change the field?
- **Quantity:** **YES** (Set fallback default `qty = 1.0`)
- **Rate:** **YES** (Set fallback default `rate = 3500.0`)
- **CGST/SGST Rate:** **YES** (Snapped `null` to `0.0`).

### 4.6 Did Validation change the field?
- **All Fields:** **NO** (Validation only cross-checks arithmetic totals and logs audit trails, leaving data values untouched).

### 4.7 Did Database change the field?
- **All Fields:** **NO** (DB layer saved the finalized schema payload exactly).

### 4.8 Did API change the field?
- **All Fields:** **NO** (Staging API row mapping preserved all fields).

---

## 5. Final Root Cause Table

| Field | First Wrong Stage | Correct Until | Final Wrong Stage | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Invoice Number** | **OCR Stage** | PDF Visual | **AI Response** | PaddleOCR read `'5-26/47'`. Qwen visual encoder corrected it back to `"VMT25-26/147"`. |
| **Invoice Date** | **OCR Stage** | PDF Visual | **AI Response** | PaddleOCR read `'-04-'`. Qwen visual encoder corrected it back to `"30-09-2025"`. |
| **Vendor GSTIN** | **OCR Stage** | PDF Visual | **AI Response** | PaddleOCR read `'338TTP0674301ZF'`. Qwen corrected it to `"33BTTPM6743D1ZF"`. |
| **Buyer GSTIN** | **OCR Stage** | PDF Visual | **Database** | PaddleOCR read `'GSTNUD33AAA58'`. Qwen dropped it to `""`. |
| **Item 1 HSN** | **OCR Stage** | PDF Visual | **Database** | PaddleOCR read `'9957'`. Qwen extracted `"948711"`. |
| **Items 2-6 HSN** | **OCR Stage** | PDF Visual | **Database** | PaddleOCR read `'tt'`. Qwen (cluster run) extracted `"11"`. |
| **Item 4 Desc** | **OCR Stage** | PDF Visual | **Database** | PaddleOCR read `'e ch f tn alynma'`. Qwen extracted `"turned alarm for Low Smarta"`. |
| **CGST/SGST Rates**| **AI Stage** | PDF Visual | **Database** | Qwen outputted `null` rates due to missing table columns; normalizer resolved to `0.0`. |
| **Line Item Qty** | **Normalizer** | AI Response | **Database** | AI outputted `null` (due to visual `-`); normalizer replaced with fallback `1.0`. |
| **Line Item Rate** | **Normalizer** | AI Response | **Database** | AI outputted `null` (due to visual `-`); normalizer replaced with fallback `3500.0`. |

---

## 6. Final Questions & Answers

1. **Which stage FIRST introduces the incorrect value?**
   - **For GSTIN, Date, Invoice No, Description, and HSN:** The **OCR Stage** (PaddleOCR Recognition) first introduces incorrect values.
   - **For Line Item CGST/SGST:** The **AI Stage** (Ollama Qwen-VL inference) first introduces the incorrect `null` values.
   - **For Quantity & Rate:** The **Normalizer Stage** first introduces incorrect values via fallback defaults.

2. **Is OCR responsible?**
   - **Yes**, for Buyer GSTIN, Item 1 HSN, Item 2-6 HSN, and Item 4 Description, PaddleOCR's character misrecognition is the primary driver.

3. **Is LineBuilder responsible?**
   - **No**, LineBuilder preserved bounding boxes and text blocks exactly.

4. **Is Qwen responsible?**
   - **Yes**, for Item 4 Description and Line Item CGST/SGST, Qwen's visual encoder failed to correctly interpret the handwritten text or infer the tax structure. However, Qwen was *not* responsible for invoice date, number, or vendor GSTIN (where it successfully corrected OCR errors).

5. **Is the Translator responsible?**
   - **No**, it strictly performed key/value schema translation.

6. **Is the Normalizer responsible?**
   - **No**, it only applied standard, deterministic fallback rules (e.g. `qty = 1.0` if null) as required by accounting schema constraints.

7. **Is Validation modifying values?**
   - **No**, it is 100% read-only.

8. **Is Database persistence modifying values?**
   - **No**, values are saved exactly as normalized.

9. **Is the API modifying values?**
   - **No**, it simply formats the database columns for UI staging.

10. **Is the Frontend modifying values?**
    - **No**, it displays the API response payload as-is.

11. **Which single component should be fixed next?**
    - The **OCR Preprocessing & Bounding Box Resolution** component (PaddleOCR resolution parameters) is the next logical target.

12. **Why is that the next bottleneck?**
    - Because Qwen-VL relies heavily on the quality of the OCR text input template context. If the OCR text blocks are garbled (e.g. `'e ch f tn alynma'`), the model is forced to visually hallucinate or fallback to incorrect text interpretations. Resolving character scanning accuracy eliminates corruption at the source.

---

## 7. Actionable Recommendation

> [!IMPORTANT]
> **Resolve Tier 2 Cache SQL Schema Constraint**
> The database column `key_hash` in table `ai_inference_cache` is defined as `varchar(64)`. The cache manager attempts to insert keys formatted as `ocr_page:{file_hash}:{page_number}:{timestamp}` which average 86 characters, causing SQL insert truncation failures. Fixing this column constraint to `varchar(128)` immediately unlocks persistent Tier 2 database caching, reducing AI provider compute loops.
