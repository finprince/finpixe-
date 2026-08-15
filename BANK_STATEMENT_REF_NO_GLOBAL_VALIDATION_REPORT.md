# Global Bank Statement Ref_No & Narration Isolation Validation Report

## Executive Summary

A global architectural fix has been implemented across the entire Bank Statement Upload system (digital PDF extractors, OCR pipeline, and AI structured providers) to enforce strict column-based authority:
1. **Source Document Column Authority**: `ref_no` is **strictly populated** from the physical/logical Cheque/Reference column (`Chq.No.`, `Cheque No.`, `Ref No.`, `Reference No.`, `Instrument No.`). If this column is empty or missing, `ref_no` is set to `null` (`None`).
2. **Narration Integrity**: All text in the statement's Details / Description / Particulars / Narration / Transaction Details column remains **100% intact** in `narration`. Identifiers (UPI IDs, UTRs, IMPS/NEFT/RTGS sequence numbers, ATM POS numbers, colon-numeric strings) are **NEVER** stripped or promoted to `ref_no`.
3. **No Regex Inference**: All regex patterns (`REF_REGEX`, UPI regex, NEFT/RTGS/IMPS pattern matching, `:(\d{6,})` matching) that inferred reference numbers from description text have been permanently excised.
4. **Canonical DTO Provenance**: Transactions output canonical JSON structures with strict provenance metadata: `ref_source` is only `"REFERENCE_COLUMN"` or `"NONE"`, and `narration_source` is `"DETAILS_COLUMN"`.

---

## Canonical Data Contract

Every bank statement transaction adheres to the following canonical schema:

```json
{
  "date": "YYYY-MM-DD",
  "value_date": "YYYY-MM-DD",
  "narration": "Full unaltered text from the Details / Description column",
  "ref_no": "Value from dedicated reference column or null",
  "ref_source": "REFERENCE_COLUMN | NONE",
  "narration_source": "DETAILS_COLUMN",
  "debit": 123.45,
  "credit": null,
  "balance": 1500.00
}
```

### Prohibited Inferences

| Field | Prohibited Action | Permitted Action |
|---|---|---|
| `ref_no` | ❌ Extracting UPI ID `UPI/309265704325/UPI` from description | ✅ Setting `ref_no: null` when reference column is empty |
| `ref_no` | ❌ Extracting colon-numeric `:001305092971` from description | ✅ Preserving `:001305092971` inside `narration` |
| `ref_no` | ❌ Extracting NEFT/RTGS `NEFT-BARBY23093586358` from description | ✅ Setting `ref_no: null`, keeping full NEFT string in `narration` |
| `ref_no` | ❌ Extracting POS SEQ NO `309510007634` from description | ✅ Setting `ref_no: null`, keeping POS sequence in `narration` |
| `ref_source` | ❌ Setting `UPI`, `NEFT`, `REGEX`, `INFERRED`, or `NARRATION` | ✅ Only setting `REFERENCE_COLUMN` or `NONE` |

---

## Forensic Verification Across Test Datasets

### 1. SBI / Amsaveni Statement (`Amsaveni Account Statement.pdf`)
- **Structure**: 2-page digital PDF with explicit grid tables (`Txn Date`, `Value Date`, `Description`, `Ref No./Cheque No.`, `Debit`, `Credit`, `Balance`).
- **Extraction Results**:
  - Total Transactions: **16**
  - Transactions with Dedicated Ref No: **14** (`TRANSFER FROM 4897733162090`, `TRANSFER TO 35725329806`)
  - Transactions with Empty Ref No: **2** (`CREDIT INTEREST--` with `ref_no: null`)
- **Sample Canonical DTO**:
  ```json
  {
    "date": "2025-02-10",
    "value_date": "2025-02-10",
    "narration": "BY TRANSFER- UPI/CR/540704565986/BAGGI ARA/SBIN/kbraj45-1@/UPI-",
    "ref_no": "TRANSFER FROM 4897733162090",
    "ref_source": "REFERENCE_COLUMN",
    "narration_source": "DETAILS_COLUMN",
    "debit": null,
    "credit": 1500.0,
    "balance": 1500.0
  }
  ```
- **Verification**: Multi-line reference text `"TRANSFER\nFROM\n4897733162090"` is preserved as `"TRANSFER FROM 4897733162090"` in `ref_no`, while `narration` retains the full `UPI/CR/540704565986/...` string.

---

### 2. Bank of Baroda Statement (`SS BOB -0039.pdf`)
- **Structure**: 18-page digital PDF stream layout (`DATE`, `PARTICULARS`, `CHQ.NO.`, `WITHDRAWALS`, `DEPOSITS`, `BALANCE`).
- **Extraction Results**:
  - Total Transactions: **220**
  - Transactions with Dedicated Ref No: **0** (Electronic transactions where `CHQ.NO.` is empty)
  - Transactions with Empty Ref No: **220** (`ref_no: null`, `ref_source: "NONE"`)
- **Sample Canonical DTO (Before vs After)**:
  - **Before (Defective Regex)**:
    ```json
    {
      "narration": "Charges for Charges for PORD Customer Payment :001305092971",
      "ref_no": "001305092971"
    }
    ```
  - **After (Correct Global Rule)**:
    ```json
    {
      "date": "2023-04-03",
      "value_date": "2023-04-03",
      "narration": "Charges for Charges for PORD Customer Payment :001305092971",
      "ref_no": null,
      "ref_source": "NONE",
      "narration_source": "DETAILS_COLUMN",
      "debit": 17.4,
      "credit": null,
      "balance": 1041797.24
    }
    ```
- **Verification**: Colon-numeric identifiers like `:001305092971` remain in `narration`. `ref_no` is strictly `null`.

---

### 3. Indian Bank Statement (`INDIAN BANK 3468  (1.4.23 - 31.3.24).pdf`)
- **Structure**: 93-page digital PDF stream layout (`Post Date`, `Value Date`, `Details`, `Chq.No.`, `Debit`, `Credit`, `Balance`).
- **Extraction Results**:
  - Total Transactions: **648**
  - Transactions with Dedicated Ref No: **0** (All UPI / POS electronic transactions where `Chq.No.` is empty)
  - Transactions with Empty Ref No: **648** (`ref_no: null`, `ref_source: "NONE"`)
- **Sample Canonical DTO (Before vs After)**:
  - **Before (Defective Regex)**:
    ```json
    {
      "narration": "WITHDRAWAL TRANSFER UPI/309265704325/UPI /",
      "ref_no": "309265704325"
    }
    ```
  - **After (Correct Global Rule)**:
    ```json
    {
      "date": "2023-04-02",
      "value_date": "2023-04-02",
      "narration": "WITHDRAWAL TRANSFER UPI/309265704325/UPI /",
      "ref_no": null,
      "ref_source": "NONE",
      "narration_source": "DETAILS_COLUMN",
      "debit": 254.0,
      "credit": null,
      "balance": 1530.66
    }
    ```
- **Verification**: UPI numbers like `309265704325` remain fully in `narration`. `ref_no` is strictly `null`.

---

## Code Modification Summary

1. **[`backend/bank_upload/services/digital_pdf_extractor.py`](file:///c:/108/AI-accounting-0.03/backend/bank_upload/services/digital_pdf_extractor.py)**:
   - Deleted `REF_REGEX` (lines 40-43).
   - In `_extract_grid_tables`: Refined column mapping to only populate `ref_no` from actual dedicated reference columns (`Ref No.`, `Cheque No.`), with multi-line preservation and explicit `ref_source: "REFERENCE_COLUMN"` / `"NONE"`.
   - In `extract_digital_pdf_transactions`: Removed narration regex matching; set `ref_no = None` and `ref_source = "NONE"` for stream transactions without dedicated reference columns.

2. **[`backend/bank_upload/services/extraction_service.py`](file:///c:/108/AI-accounting-0.03/backend/bank_upload/services/extraction_service.py)**:
   - Updated `_PROMPT_TEMPLATE` and `_PROMPT_BINARY` to strictly forbid Qwen/AI extraction of `ref_no` from narration text.
   - Updated `_process_extracted_rows` to normalize empty strings, `'None'`, `'null'`, and dashes to `None`, attaching `ref_source` and `narration_source`.
   - Updated `_normalize_parsed_rows` to support multi-line reference column concatenation.

3. **[`backend/core/providers/mistral_structured_provider.py`](file:///c:/108/AI-accounting-0.03/backend/core/providers/mistral_structured_provider.py)**:
   - Updated `MistralBankTransactionSchema` field description for `ref_no` to strictly specify dedicated column source and forbid inference from narration.

4. **[`backend/bank_upload/views.py`](file:///c:/108/AI-accounting-0.03/backend/bank_upload/views.py)**:
   - Sanitized `ref_no` storage in `BankStatementTemp.objects.create` to ensure empty/placeholder values are stored as database `NULL`.
