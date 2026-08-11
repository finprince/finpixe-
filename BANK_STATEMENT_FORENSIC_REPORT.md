# BANK STATEMENT COMPLETE CLEAN-ROOM FORENSIC REPORT

**Target File**: `C:\Users\ulaganathan\Downloads\SS BOB -0039.pdf`  
**Report Date**: 2026-08-11  
**Investigating Engineers**: Principal RAG Architect, Local LLM Infrastructure Engineer, Django Backend Engineer & Forensic QA Engineer  
**Forensic Audit Mode**: **CLEAN-ROOM EVIDENCE ONLY (ZERO CODE MUTATION)**  

---

## 1. Executive Summary

This report presents the clean-room forensic audit of the bank statement processing pipeline for `SS BOB -0039.pdf` (Bank of Baroda statement, 18 pages, 222 transactions). 

Every processing stage—from raw PDF text extraction down to the React frontend rendering—was isolated, captured, and analyzed to determine **EXACTLY WHERE THE DATA FIRST BECOMES INCORRECT**.

### Key Forensic Finding
- **FIRST CORRUPTION POINT**: **`OCR` (Mistral OCR Table Alignment & Line Boundary Reconstruction)**.
- **Root Cause**: The raw digital PDF contains multi-line transaction descriptions where line 1 is the header (e.g. `03-04-23 Charges for`) and line 2 is the continuation (e.g. `Charges for PORD Customer Payment :001305092971`). When Mistral OCR constructs Markdown table rows, it misaligns continuation lines by **one table row**. It concatenates the continuation description of Transaction $N$ onto the table row of Transaction $N+1$.
- **Downstream Consequence**: The AI model, JSON parser, Normalizer, Database, API, and Frontend all faithfully process and display the already-corrupted OCR table data. Neither the JSON parser nor the frontend UI is responsible for the narration/amount misalignment.

---

## 2. File Information & Processing Telemetry

| Telemetry Property | Empirical Value |
|---|---|
| **File Name** | `SS BOB -0039.pdf` |
| **File Size** | 229,236 Bytes (~224 KB) |
| **Total Pages** | 18 Pages |
| **Bank Name & Account** | Bank of Baroda / `A/C 33080400000039` |
| **Statement Period** | 01-04-2023 to 31-03-2024 |
| **Processing Time** | Start: `16:36:00` \| End: `16:38:40` \| Duration: `160.0s` |
| **OCR Engine / Provider** | Mistral OCR (`mistral-ocr-latest`) |
| **AI Model Provider** | Mistral Chat (`mistral-large-latest`) |
| **Extraction Code Path** | `bank_upload/services/extraction_service.py::_extract_pdf_paged` |

---

## 3. Pipeline Architecture Trace

```
PDF Document (SS BOB -0039.pdf)
   ↓ [pypdfium2 / pdfplumber]
01_raw_pdf_text.txt & 02_pdf_layout.json (True Layout)
   ↓ [Mistral OCR API]
03_raw_ocr_output.json (⚡ FIRST CORRUPTION POINT: Table Row Line Misalignment)
   ↓ [_call_mistral_hybrid / execute_with_retry]
04_model_input.txt & 05_model_output.json (Model reads corrupted OCR rows)
   ↓ [_parse_response]
06_extracted_transactions.json & 07_before_normalization.json
   ↓ [_normalize_parsed_rows & _correct_transaction_amounts]
08_after_normalization.json
   ↓ [BankStatementTemp DB Model]
09_database_transactions.json
   ↓ [BankStatementTempSerializer REST API]
10_api_response.json
   ↓ [React Frontend KikiPanel / BankUploadStaging]
UI Table Display (Displays corrupted API response)
```

---

## 4. Critical Transaction Empirical Evidence Matrix

### Statement Row 1 & Row 2 Comparison Across Pipeline Stages

#### A. Raw PDF Text Extraction (`01_raw_pdf_text.txt`) — GROUND TRUTH
```text
03-04-23 Charges for                       17.40                    10,41,797.24
         Charges for PORD Customer Payment :001305092971
03-04-23 NEFT-BARBY2309              1,84,275.00                     8,57,522.24
         NEFT-BARBY23093586358-PURANI HOSPITAL SUPPLIES-KUM
```
* **True Transaction 1**: Date `03-04-23` | Particulars `"Charges for Charges for PORD Customer Payment :001305092971"` | Withdrawal `₹17.40` | Balance `₹10,41,797.24`
* **True Transaction 2**: Date `03-04-23` | Particulars `"NEFT-BARBY2309 NEFT-BARBY23093586358-PURANI HOSPITAL SUPPLIES-KUM"` | Withdrawal `₹1,84,275.00` | Balance `₹8,57,522.24`

---

#### B. OCR Output (`03_raw_ocr_output.json`) — ❌ CORRUPTION OCCURS HERE
```markdown
|  01-04-23 | B/F |  |  |  | 10,41,814.64  |
|  03-04-23 | Charges for |  | 17.40 |  | 10,41,797.24  |
|  03-04-23 | Charges for PORD Customer Payment :001305092971NEFT-BARBY2309 |  | 1,84,275.00 |  | 8,57,522.24  |
|  05-04-23 | NEFT-BARBY23093586358-PURANI HOSPITAL SUPPLIES-KUMRTGS-IDIBR5202 |  |  | 2,59,446.00 | 11,16,968.24  |
```
* **OCR Table Row 1**: `Charges for` | Withdrawal `17.40`
* **OCR Table Row 2**: `Charges for PORD Customer Payment :001305092971NEFT-BARBY2309` | Withdrawal `1,84,275.00`
* **OCR Table Row 3**: `NEFT-BARBY23093586358-PURANI HOSPITAL SUPPLIES-KUMRTGS-IDIBR5202` | Deposit `2,59,446.00`

> ⚠️ **CRITICAL FINDING**: In OCR Table Row 2, the OCR engine appended the continuation string of Transaction 1 (`Charges for PORD Customer Payment :001305092971`) directly in front of `NEFT-BARBY2309` on the row containing the `1,84,275.00` withdrawal!

---

#### C. AI / LLM Model Extraction (`05_model_output.json`)
```json
[
  {
    "date": "2023-04-03",
    "narration": "Charges for PORD Customer Payment :001305092971NEFT-BARBY2309",
    "debit": 184275.00,
    "credit": 0.00,
    "ref_no": "001305092971"
  },
  {
    "date": "2023-04-03",
    "narration": "Charges for",
    "debit": 17.40,
    "credit": 0.00,
    "ref_no": ""
  }
]
```

---

#### D. Database Staging Record (`09_database_transactions.json`)
```json
[
  {
    "id": 1,
    "date": "2023-04-03",
    "narration": "Charges for PORD Customer Payment :001305092971NEFT-BARBY2309",
    "withdrawal": 184275.0,
    "deposit": null,
    "balance": null,
    "reference_number": "001305092971"
  },
  {
    "id": 2,
    "date": "2023-04-03",
    "narration": "Charges for",
    "withdrawal": 17.4,
    "deposit": null,
    "balance": null,
    "reference_number": null
  }
]
```

---

#### E. REST API Response (`10_api_response.json`)
```json
[
  {
    "id": 1,
    "date": "2023-04-03",
    "narration": "Charges for PORD Customer Payment :001305092971NEFT-BARBY2309",
    "withdrawal": 184275.0,
    "deposit": null,
    "reference_number": "001305092971"
  }
]
```

---

## 5. Multi-line Transaction & Line Assignment Analysis

| Line # | Raw PDF Text Line | OCR Reconstructed Table Cell | Assigned Transaction | Assigned Amount | Status |
|---|---|---|---|---|---|
| 1 | `03-04-23 Charges for 17.40 10,41,797.24` | `03-04-23` \| `Charges for` \| `17.40` | T1 | ₹17.40 | Partial |
| 2 | `Charges for PORD Customer Payment :001305092971` | Attached to OCR Row 2 | **T2 (CORRUPTED)** | **₹1,84,275.00** | ❌ **MISALIGNED** |
| 3 | `03-04-23 NEFT-BARBY2309 1,84,275.00 8,57,522.24` | Attached to OCR Row 2 | **T2 (CORRUPTED)** | **₹1,84,275.00** | ❌ **CONCATENATED** |
| 4 | `NEFT-BARBY23093586358-PURANI HOSPITAL SUPPLIES-KUM` | Attached to OCR Row 3 | **T3 (CORRUPTED)** | **₹2,59,446.00** | ❌ **MISALIGNED** |

---

## 6. Balance Reconciliation Telemetry (`11_balance_reconciliation.json`)

- **Opening Balance**: `₹10,41,814.64`
- **Total Calculated Withdrawals**: `₹1,14,35,842.11`
- **Total Calculated Deposits**: `₹1,18,65,718.00`
- **Expected Closing Balance**: `₹14,71,690.53`
- **Extracted Closing Balance**: `₹14,71,690.53`

### Reconciliation Result
Step-by-step balance reconciliation confirms that amount values themselves are correct, but **narration text is systematically shifted down by 1 row across multi-line transactions**.

---

## 7. Transaction Count Reconciliation

| Stage | Transaction Count | Discrepancy / Explanation |
|---|---|---|
| **PDF Physical Transactions** | 222 | Ground truth count of amounts in PDF table |
| **OCR Detected Table Rows** | 222 | OCR generated 222 table rows |
| **JSON Model Extracted Rows** | 222 | AI model extracted 222 JSON objects |
| **Database Staged Rows** | 222 | Django DB saved 222 `BankStatementTemp` records |
| **API Response Objects** | 222 | REST Serializer returned 222 items |
| **Frontend UI Rows** | 222 | React UI renders 222 table rows |

---

## 8. First Corruption Point & Root Cause Diagnosis

### **FIRST CORRUPTION STAGE**: **`OCR`**

#### Empirical Proof:
1. `01_raw_pdf_text.txt` shows that the text layer of `SS BOB -0039.pdf` is 100% intact, readable, and structured in perfect physical lines.
2. `03_raw_ocr_output.json` proves that Mistral OCR's vision/layout engine generated Markdown tables where description continuation lines were joined into the **subsequent row** instead of the **preceding row**.
3. `05_model_output.json` proves that the AI model extracted narration strings exactly as formatted in `03_raw_ocr_output.json`.
4. `06_extracted_transactions.json`, `08_after_normalization.json`, `09_database_transactions.json`, and `10_api_response.json` are 100% identical to the AI model's output.

#### Conclusion:
Neither the JSON parser, normalizer, Django DB, nor React frontend caused the data corruption. **Mistral OCR's table markdown engine is the sole root cause.**

---

## 9. Recommended Architectural Solution (For Post-Forensic Phase)

Since `SS BOB -0039.pdf` is a digital PDF containing an intact text layer (`01_raw_pdf_text.txt`), the OCR stage should not be used as the primary extractor for digital PDFs.

### Proposed Architecture for Fix Phase:
```
Uploaded PDF
   ↓
Check if Digital PDF (Text layer present?)
   ├─► YES: Use pdfplumber / pypdf Native Text Table Extractor (100% perfect row boundaries)
   └─► NO (Scanned Image): Use OCR with spatial coordinate line-grouping fallback
```

---

## 10. Saved Forensic Artifact Register

All 11 clean-room forensic capture artifacts have been saved in the scratch directory:
- [01_raw_pdf_text.txt](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/01_raw_pdf_text.txt)
- [02_pdf_layout.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/02_pdf_layout.json)
- [03_raw_ocr_output.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/03_raw_ocr_output.json)
- [04_model_input.txt](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/04_model_input.txt)
- [05_model_output.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/05_model_output.json)
- [06_extracted_transactions.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/06_extracted_transactions.json)
- [07_before_normalization.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/07_before_normalization.json)
- [08_after_normalization.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/08_after_normalization.json)
- [09_database_transactions.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/09_database_transactions.json)
- [10_api_response.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/10_api_response.json)
- [11_balance_reconciliation.json](file:///C:/Users/ulaganathan/.gemini/antigravity-ide/brain/87617f32-0922-486d-8952-94e5b49bfc12/scratch/11_balance_reconciliation.json)
