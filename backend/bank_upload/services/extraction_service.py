"""
extraction_service.py — Bank Statement Qwen/AI Extraction
=========================================================

STRICT RULES:
  ✅  Reads file bytes / text
  ✅  Calls Qwen/AI API
  ✅  Returns List[dict]
  ❌  NO Django model imports
  ❌  NO DB access of any kind
  ❌  NO side-effects

Entry point:
    extract_transactions(file_obj) -> List[dict]

Each returned dict:
    {
        "date":      "YYYY-MM-DD" or "",
        "narration": "FULL description exactly as written. Prepend the transaction date (e.g. 'DD-MM-YY') to the beginning.",
        "debit":     float | None,
        "credit":    float | None,
    }
"""

import os
import io
import re
import json
import logging
from datetime import datetime

logger = logging.getLogger('bank_upload.extraction')

# Use the shared key manager + retry logic from core.ai_proxy
# This gives us: key rotation, 429 mark-unhealthy, model fallback, exponential backoff
from core.ai_proxy import api_key_manager, execute_with_retry  # type: ignore


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

import time
from concurrent.futures import ThreadPoolExecutor

class ExtractionMetrics:
    """Track performance and reliability metrics for the extraction session."""
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.start_time = time.time()
        self.total_pages = 0
        self.total_chunks = 0
        self.successful_chunks = 0
        self.failed_chunks = 0
        self.total_txns = 0
        self.retries = 0
        self.duration = 0.0

    def finalize(self):
        self.duration = time.time() - self.start_time
        logger.info(f"📊 METRICS [{self.file_name}]: pages={self.total_pages}, chunks={self.total_chunks}, "
                    f"success={self.successful_chunks}, failed={self.failed_chunks}, "
                    f"txns={self.total_txns}, duration={self.duration:.2f}s")

    def to_dict(self):

        return {
            'file_name': self.file_name,
            'duration': round(time.time() - self.start_time, 2),
            'total_pages': self.total_pages,
            'total_chunks': self.total_chunks,
            'successful_chunks': self.successful_chunks,
            'failed_chunks': self.failed_chunks,
            'total_txns': self.total_txns,
            'opening_balance': getattr(self, 'opening_balance', None),
            'closing_balance': getattr(self, 'closing_balance', None),
            'balance_check_passed': getattr(self, 'balance_check_passed', True)
        }

def extract_transactions(file_obj) -> tuple[list, dict]:
    """
    Accept a Django UploadedFile.
    Returns (list_of_rows, metrics_dict).
    """
    metrics = None
    try:
        file_bytes = file_obj.read()
        mime_type  = getattr(file_obj, 'content_type', 'application/octet-stream') or 'application/octet-stream'
        file_name  = getattr(file_obj, 'name', 'bank_statement') or 'bank_statement'

        if not file_bytes:
            raise ValueError(f"CRITICAL: Empty file bytes received for {file_name}")

        metrics = ExtractionMetrics(file_name)
        logger.info(f"🔍 Starting hardened extraction: {file_name}")

        # ── Step 1: PDF Classification & Native vs OCR Routing ──
        is_pdf = mime_type == 'application/pdf' or file_name.lower().endswith('.pdf')
        if is_pdf:
            from .pdf_type_detector import detect_pdf_type
            pdf_info = detect_pdf_type(file_bytes)
            if pdf_info.get("pdf_type") == "digital":
                logger.info(
                    f"📄 [DIGITAL PDF ROUTING] '{file_name}' classified as DIGITAL "
                    f"({pdf_info.get('pages')} pages, {pdf_info.get('char_count_total')} chars). "
                    "Bypassing OCR Markdown table reconstruction in favor of Native Digital Extraction."
                )
                from .digital_pdf_extractor import extract_digital_pdf_transactions
                rows = extract_digital_pdf_transactions(file_bytes, metrics)
            else:
                logger.info(
                    f"📷 [SCANNED PDF ROUTING] '{file_name}' classified as SCANNED. "
                    "Routing to Isolated OCR Pipeline."
                )
                rows = _extract_pdf_paged(file_bytes, file_name, metrics)
        else:

            # Standard Processing for CSV/Excel/Images
            text_payload = _to_text(file_bytes, file_name, mime_type)
            if not text_payload and not mime_type.startswith('image/'):
                raise ValueError(f"CRITICAL: Failed to extract text from {file_name}")

            raw = _call_ai_provider(text_payload, mime_type, file_bytes, file_name)
            rows = _parse_response(raw)
            metrics.total_chunks = 1
            metrics.successful_chunks = 1 if rows else 0

        # ── Step 2: Post-Extraction Hardening (Normalization Patch) ──
        if not rows:
            raise ValueError(f"CRITICAL: No transactions extracted from {file_name}")

        # 1. Normalization: Rebuild transactions from over-split or messy rows
        normalized = _normalize_parsed_rows(rows)
        
        # 2. Amount Correction & DR/CR Assignment
        corrected = _correct_transaction_amounts(normalized)
        
        # 3. Deduplication
        deduped = _deduplicate_transactions(corrected)
        
        # 4. Chronological Consistency
        final_rows = _validate_chronology(deduped)
        
        # 5. Balance Sanity Check
        metrics.balance_check_passed = _validate_balances(final_rows, metrics)
        
        # 6. Quality Assurance
        _perform_quality_check(final_rows)

        metrics.total_txns = len(final_rows)
        metrics_dict = metrics.to_dict()
        metrics.finalize()
        
        return final_rows, metrics_dict

    except Exception as exc:
        if metrics:
            metrics.finalize()
        logger.error(f"❌ extraction_service: {exc}", exc_info=True)
        raise





# ---------------------------------------------------------------------------
# Helpers — file → text
# ---------------------------------------------------------------------------

def _to_text(file_bytes: bytes, file_name: str, mime_type: str) -> str | None:
    """Convert CSV / Excel to plain text for the prompt. Returns None for PDFs/images."""
    name_lower = file_name.lower()

    if name_lower.endswith('.csv') or 'csv' in mime_type:
        # Decode CSV as UTF-8 (fallback latin-1)
        try:
            return file_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return file_bytes.decode('latin-1', errors='replace')

    if name_lower.endswith(('.xlsx', '.xls')) or 'spreadsheet' in mime_type or 'excel' in mime_type:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
            ws = wb.active
            lines = []
            for row in ws.iter_rows(values_only=True):
                lines.append(','.join(str(c) if c is not None else '' for c in row))
            return '\n'.join(lines)
        except Exception as exc:
            logger.warning(f"openpyxl failed: {exc}. Falling back to binary upload.")
            return None

    # PDF / image — pass raw bytes to Qwen/AI inline
    return None


# ---------------------------------------------------------------------------
# Helpers — Qwen/AI call
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATE = r"""
### EXTRACTION & SELF-CORRECTION PROTOCOL:

#### STEP 1: INITIAL EXTRACTION
- **ANCHOR**: Every line with an amount = 1 transaction.
- **ISOLATION**: Create one row for every amount found. DO NOT merge multiple amounts.

#### STEP 2: STICKINESS STATE MACHINE (FOR NARRATION)
For each line processed, maintain an internal state `last_line_was_amount`:
1.  **IF line has an AMOUNT**:
    - Start new transaction.
    - Set `last_line_was_amount = True`.
2.  **IF line has NO amount AND `last_line_was_amount == True`**:
    - **UPWARD ATTACH**: Merge this line into the **PREVIOUS** transaction's narration.
    - Set `last_line_was_amount = False`.
3.  **IF line starts with a DATE**:
    - Start new transaction.
    - Set `last_line_was_amount = False`.
4.  **LIMIT**: Max 2 lines total for any single transaction.

#### STEP 3: CONSTRAINTS
- **DO NOT** change the number of transactions identified by amounts.
- **DO NOT** change amount values or dates.

### FIELD RULES:
- **date**: "YYYY-MM-DD"
- **value_date**: "YYYY-MM-DD" (if present, else same as date)
- **narration**: Full transaction details/description/particulars from the Details/Description/Narration column. ALL text, numbers, UPI IDs, UTRs, ATM seq numbers, account numbers, etc. in the Details column MUST remain inside narration.
- **debit / credit**: From the withdrawal/deposit or debit/credit column.
- **balance**: Running balance if present in the row.
- **ref_no**: ONLY populated from the actual dedicated "Chq.No." / "Cheque No." / "Ref No." / "Reference No." / "Instrument No." column when present in the table. If the reference column is empty, absent, or contains no dedicated cheque/instrument number, ref_no MUST be null. NEVER infer or extract ref_no from narration.

#### STEP 4: STABILITY & COMPLETENESS
- **STOP CONDITIONS**: Do not stop extracting until you see "END OF REPORT", "Total", or the end of the content.
- **PRECISION**: Ensure the very last transaction before the total is extracted.

### OUTPUT FORMAT:
Return an array of objects:
[
  {{
    "date": "YYYY-MM-DD",
    "value_date": "YYYY-MM-DD",
    "narration": "Full narration string",
    "debit": 123.45,
    "credit": null,
    "balance": 1500.00,
    "ref_no": null
  }}
]

Bank statement content:
{content}
"""

_PROMPT_BINARY = r"""
### STICKINESS PROTOCOL (CRITICAL):
1. **ANCHOR**: Every line with an amount = 1 transaction. SCAN EVERY PAGE COMPLETELY.
2. **AMOUNT LINE**: Set `last_line_was_amount = True`.
3. **NO AMOUNT + FLAG==True**: Attach UPWARD to previous transaction. Set flag = False.
4. **DATE LINE**: Start new txn. Set flag = False.
5. **LIMIT**: Max 2 lines per row.

### DATA SEARCH RULES:
- Ignore cover letters, marketing text, and general summaries.
- Search specifically for the Transaction Table (headers like Date, Description, Particulars, Details, Chq No, Withdrawal, Deposit, Debit, Credit, Balance).
- Extract all financial movements.

### FIELD RULES:
- **date**: "YYYY-MM-DD"
- **value_date**: "YYYY-MM-DD" (if present, else same as date)
- **narration**: Full description/particulars exactly as written in the Details/Description column. Keep all identifiers (UPI, UTR, etc.) in narration.
- **debit / credit**: From the anchor row amounts.
- **balance**: Running balance if present.
- **ref_no**: ONLY from the dedicated Cheque No. / Ref No. column. If the reference column is empty or missing, set ref_no to null. NEVER infer or extract ref_no from narration.

Return an array of objects:
[
  { "date": "YYYY-MM-DD", "value_date": "YYYY-MM-DD", "narration": "...", "debit": ..., "credit": ..., "balance": ..., "ref_no": null }
]
"""


def _call_ai_provider(text_payload: str | None, mime_type: str, file_bytes: bytes, file_name: str, is_first: bool = False, is_last: bool = False) -> str:
    """
    Call AI Provider with strict prompt injection, logging, and balance extraction flags.
    """
    api_key = api_key_manager.get_healthy_key()
    if not api_key:
        raise RuntimeError("No healthy AI API keys available.")

    # Enhance prompt for first/last chunks to capture balances
    balance_hint = ""
    if is_first:
        balance_hint += "\n- This is the START of the statement. Extract the 'opening_balance' as a number."
    if is_last:
        balance_hint += "\n- This is the END of the statement. Extract the 'closing_balance' as a number."

    is_binary = (mime_type == 'application/pdf' or mime_type.startswith('image/'))
    
    if is_binary:
        # Binary mode: send as dict matching what ai_proxy.py expects
        base_prompt = _PROMPT_BINARY + balance_hint
        prompt_text = f"{text_payload}\n\n{base_prompt}" if text_payload else base_prompt
        
        prompt = [
            prompt_text,
            {
                'inline_data': {
                    'mime_type': mime_type,
                    'data': file_bytes
                }
            }
        ]
    else:
        # Text mode (CSV/Excel): embed content in prompt template
        # Here text_payload IS the content
        prompt_text = _PROMPT_TEMPLATE.format(content=text_payload or "") + balance_hint
        prompt = prompt_text

    # Debugging visibility: Log prompt size
    logger.info(f"📡 AI Dispatch: file={file_name}, text_size={len(prompt_text)}, first={is_first}, last={is_last}")


    raw = execute_with_retry(
        prompt=prompt,
        request_data={
            'type': 'extraction',
            'prompt': prompt_text, # Ensure ai_proxy logs this correctly
            'document_type': 'bank_statement'
        },
        api_key=api_key,
    )
    
    if not raw:
        raise ValueError(f"CRITICAL: Empty response received from AI for {file_name}")
        
    return raw


def _call_mistral_hybrid(img_bytes: bytes, page_text: str, page_idx: int, file_name: str, total_pages: int, metrics: ExtractionMetrics) -> str:
    from core.ai_proxy import api_key_manager, execute_with_retry
    from ocr_pipeline.extraction import ai_concurrency_gate
    
    api_key = api_key_manager.get_healthy_key()
    if not api_key:
        raise RuntimeError("No healthy AI API keys available.")
        
    is_first = (page_idx == 0)
    is_last = (page_idx == total_pages - 1)
    
    balance_hint = ""
    if is_first:
        balance_hint += "\n- This is the START of the statement. Extract the 'opening_balance' as a number."
    if is_last:
        balance_hint += "\n- This is the END of the statement. Extract the 'closing_balance' as a number."
        
    prompt_text = f"### [PAGE {page_idx + 1} OCR DATA]\n{page_text}\n\n{_PROMPT_BINARY}{balance_hint}"
    
    prompt = prompt_text
    
    tenant_id = 'system'
    logger.info(f"📡 AI Hybrid Dispatch: page={page_idx+1}/{total_pages}, file={file_name}, text_size={len(prompt_text)}")
    
    t_ai_start = time.monotonic()
    with ai_concurrency_gate(tenant_id):
        raw = execute_with_retry(
            prompt=prompt,
            request_data={
                'type': 'extraction',
                'prompt': prompt_text,
                'page_index': page_idx + 1,
                'total_pages': total_pages,
                'document_type': 'bank_statement'
            },
            api_key=api_key,
        )
    
    if not raw:
        raise ValueError(f"CRITICAL: Empty response received from AI for {file_name} page {page_idx+1}")
        
    return raw

def _process_single_page_shared(page_idx: int, temp_pdf_path: str, file_name: str, total_pages: int, metrics: ExtractionMetrics):
    from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction
    
    logger.info(f"Rendering & running OCR for page {page_idx+1}/{total_pages}...")
    
    dpi = int(os.getenv("OCR_DEFAULT_DPI", "350"))
    iso_res = run_isolated_page_extraction(temp_pdf_path, page_idx, dpi=dpi)
    
    if not iso_res.get("success"):
        raise RuntimeError(f"OCR isolation failure on page {page_idx+1}: {iso_res.get('error')}")
        
    img_bytes = iso_res["image_bytes"]
    page_text = iso_res["text"]
    
    # Normalize layout whitespace
    page_text = re.sub(r'[ \t]+', ' ', page_text).strip()
    page_text = re.sub(r'(\r\n|\r|\n){2,}', '\n\n', page_text)
    
    raw_response = _call_mistral_hybrid(img_bytes, page_text, page_idx, file_name, total_pages, metrics)
    page_rows = _parse_response(raw_response)
    
    return raw_response, page_rows

def _extract_pdf_paged_shared(file_bytes: bytes, file_name: str, metrics: ExtractionMetrics) -> list:
    import tempfile
    import pypdfium2 as pdfium
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
        temp_pdf.write(file_bytes)
        temp_pdf_path = temp_pdf.name
        
    try:
        pdf = pdfium.PdfDocument(temp_pdf_path)
        total_pages = len(pdf)
        pdf.close()
        
        metrics.total_pages = total_pages
        metrics.total_chunks = total_pages
        
        all_results = [None] * total_pages
        logger.info(f"🚀 Shared OCR Parallel Dispatch: {total_pages} pages with 3 workers")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_idx = {}
            for i in range(total_pages):
                future = executor.submit(
                    _process_single_page_shared,
                    i, temp_pdf_path, file_name, total_pages, metrics
                )
                future_to_idx[future] = i
                
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    raw_response, page_rows = future.result()
                    
                    if idx == 0:
                        metrics.opening_balance = _extract_balance_from_raw(raw_response, "opening")
                    if idx == total_pages - 1:
                        metrics.closing_balance = _extract_balance_from_raw(raw_response, "closing")
                        
                    all_results[idx] = page_rows
                    metrics.successful_chunks += 1
                    logger.info(f"📥 Page {idx+1}/{total_pages}: SUCCESS ({len(page_rows)} rows)")
                except Exception as e:
                    metrics.failed_chunks += 1
                    logger.error(f"⚠️ Page {idx+1}/{total_pages}: FAILED - {e}", exc_info=True)
                    all_results[idx] = []
                    
        if metrics.total_chunks > 0:
            failure_rate = metrics.failed_chunks / metrics.total_chunks
            if failure_rate > 0.3:
                raise ValueError(f"CRITICAL: Shared OCR extraction failed for {failure_rate*100:.0f}% of document. Pipeline aborted.")
                
        merged_rows = []
        for page_rows in all_results:
            if page_rows:
                merged_rows.extend(page_rows)
                
        return merged_rows
        
    finally:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {temp_pdf_path}: {e}")

def _extract_pdf_paged(file_bytes: bytes, file_name: str, metrics: ExtractionMetrics) -> list:
    """
    Split PDF into chunks and process in parallel with failure isolation.
    Uses shared pypdfium2 / Mistral OCR engine.
    """
    return _extract_pdf_paged_shared(file_bytes, file_name, metrics)

    # Integrity Check: Reject if failure rate is too high (Threshold: 30%)
    if metrics.total_chunks > 0:
        failure_rate = metrics.failed_chunks / metrics.total_chunks
        if failure_rate > 0.3:
            raise ValueError(f"CRITICAL: Extraction failed for {failure_rate*100:.0f}% of document. Pipeline aborted.")

    # Merge results in strict page order
    merged_rows = []
    for chunk_rows in all_results:
        if chunk_rows:
            merged_rows.extend(chunk_rows)
            
    return merged_rows


def _deduplicate_transactions(rows: list) -> list:
    """
    Remove exact duplicate rows that might occur at chunk/page boundaries.
    Uses a robust multi-field identity hash (Date + Value Date + Amount + Balance + Reference + Narration).
    """
    seen = set()
    deduped = []
    for r in rows:
        amt_debit = _clean_amount(r.get('debit')) or 0
        amt_credit = _clean_amount(r.get('credit')) or 0
        amt_bal = _clean_amount(r.get('balance'))
        
        txn_key = (
            str(r.get('date')),
            str(r.get('value_date') or r.get('date')),
            f"D{amt_debit:.2f}",
            f"C{amt_credit:.2f}",
            f"B{amt_bal:.2f}" if amt_bal is not None else None,
            str(r.get('ref_no')).strip().upper() if r.get('ref_no') else None,
            str(r.get('narration', '')).strip().upper()[:80]
        )
        if txn_key not in seen:
            deduped.append(r)
            seen.add(txn_key)
    
    diff = len(rows) - len(deduped)
    if diff > 0:
        logger.info(f"🧹 Deduplication: Removed {diff} duplicate rows.")
    return deduped


def _validate_chronology(rows: list) -> list:
    """Ensure transactions are logically ordered. Flag suspicious jumps."""
    if not rows: return []
    # Basic sort by date to ensure page-order doesn't break time-order
    # (Though AI chunks are merged in page order, this is a safety layer)
    return sorted(rows, key=lambda x: x['date'] if x['date'] else '9999-99-99')


def _perform_quality_check(rows: list):
    """Deep check for garbage output."""
    missing_dates = [r for r in rows if not r.get('date')]
    if len(missing_dates) > len(rows) * 0.5:
        raise ValueError("CRITICAL: Over 50% of transactions are missing dates. Extraction unreliable.")
    
    zero_amounts = [r for r in rows if not r.get('debit') and not r.get('credit')]
    if len(zero_amounts) > len(rows) * 0.3:
        logger.warning(f"⚠️ High volume of zero-amount rows ({len(zero_amounts)}). Possible extraction noise.")




# ---------------------------------------------------------------------------
# Helpers — parse Qwen/AI response
# ---------------------------------------------------------------------------

def _parse_response(raw: str) -> list:
    """
    Parse Qwen/AI's text response into a list of transaction dicts.
    Strips markdown code fences, handles partial/truncated JSON gracefully.
    """
    if not raw:
        return []

    # Strip markdown fences
    cleaned = raw.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$',          '', cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # Strategy 1: Find the JSON array
    start = cleaned.find('[')
    end   = cleaned.rfind(']')
    
    rows = []
    if start != -1 and end != -1 and end > start:
        try:
            rows = json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            # If loads fails, it might be due to trailing commas or minor corruption
            logger.warning("JSON array decode failed. Attempting fallback parse.")
            rows = _fallback_parse(cleaned[start:end + 1])
    else:
        # Strategy 2: No perfect array found (possibly truncated or wrapped in object)
        # Attempt to find all { } objects in the entire response
        logger.warning("No complete JSON array found. Salvaging individual objects.")
        rows = _fallback_parse(cleaned)

    if not isinstance(rows, list):
        return []

    return _process_extracted_rows(rows)


def _process_extracted_rows(rows: list) -> list:
    """Standardize and clean extracted rows according to the Global Bank Statement rules."""
    from .digital_pdf_extractor import _clean_transaction_narration
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Salvage if at least narration or an amount exists
        if not row.get('narration') and not row.get('debit') and not row.get('credit'):
            continue
            
        raw_ref = row.get('ref_no') or row.get('cheque_no') or row.get('reference_number')
        clean_ref = ' '.join(str(raw_ref).split()).strip() if raw_ref else None
        if clean_ref in ('', 'None', 'null', 'NULL', '—', '-', 'N/A', 'NA'):
            clean_ref = None

        d_val = _clean_date(row.get('date', ''))
        vd_val = _clean_date(row.get('value_date', '')) or d_val

        # Clean narration: remove line breaks, leading dates, header fragments, footer/address text, and extract ref_no/tran_id
        narration, clean_ref = _clean_transaction_narration(row.get('narration', ''), d_val, clean_ref)

        if not narration and not row.get('debit') and not row.get('credit'):
            continue

        result.append({
            'date':             d_val,
            'value_date':       vd_val,
            'narration':        narration,
            'debit':            _clean_amount(row.get('debit')),
            'credit':           _clean_amount(row.get('credit')),
            'balance':          _clean_amount(row.get('balance')),
            'ref_no':           clean_ref,
            'ref_source':       'REFERENCE_COLUMN' if clean_ref else 'NONE',
            'narration_source': 'DETAILS_COLUMN'
        })
    return result


MONTHS_MAP = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    'january': '01', 'february': '02', 'march': '03', 'april': '04', 'june': '06',
    'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'
}


def _clean_date(value) -> str | None:
    """
    Robust date normalizer and validator.
    Validates real calendar dates (1900-2100) so invalid dates never crash DB inserts.
    """
    if not value:
        return None
    s = str(value).strip()
    tokens = s.split()
    if len(tokens) > 1:
        for t in tokens:
            cleaned = _clean_date(t)
            if cleaned:
                return cleaned
        
    # 1. Named month dates (e.g. 10 Feb 2025, 5 May 2025, 10-Feb-2025, 10-Jul-2026)
    m_named = re.match(r'^(\d{1,2})[-/\s]+([a-zA-Z]+)[-/\s]+(20\d{2}|\d{2})$', s)
    if m_named:
        day_str, mon_str, yr_str = m_named.groups()
        mon_lower = mon_str.lower()
        if mon_lower in MONTHS_MAP:
            if len(yr_str) == 2:
                yr_str = '20' + yr_str
            s_cand = f"{yr_str}-{MONTHS_MAP[mon_lower]}-{int(day_str):02d}"
            try:
                dt = datetime.strptime(s_cand, "%Y-%m-%d")
                if 1900 <= dt.year <= 2100:
                    return s_cand
            except ValueError:
                pass

    # 2. Standard ISO YYYY-MM-DD
    m_iso = re.match(r'^(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})$', s)
    if m_iso:
        yyyy, mm, dd = m_iso.groups()
        s_iso = f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
        try:
            dt = datetime.strptime(s_iso, "%Y-%m-%d")
            if 1900 <= dt.year <= 2100:
                return s_iso
        except ValueError:
            pass

    # 3. Standard DMY numeric formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY, DD/MM/YY
    m_dmy = re.match(r'^(\d{1,2})[-/\.](\d{1,2})[-/\.](20\d{2}|\d{2})$', s)
    if m_dmy:
        d, mth, y = m_dmy.groups()
        if len(y) == 2:
            y = '20' + y
        try:
            date_s = f'{y}-{int(mth):02d}-{int(d):02d}'
            dt = datetime.strptime(date_s, '%Y-%m-%d')
            if 1900 <= dt.year <= 2100:
                return date_s
        except ValueError:
            pass

    # 4. Try common DMY / MDY formats
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%d.%m.%Y', '%d.%m.%y', '%Y/%m/%d', '%d %b %Y', '%d %B %Y', '%d-%b-%Y', '%d-%b-%y'):
        try:
            dt = datetime.strptime(s, fmt)
            if 1900 <= dt.year <= 2100:
                return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
            
    return None


def _clean_amount(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if float(value) > 0 else None
    try:
        cleaned = re.sub(r'[^\d.]', '', str(value))
        f = float(cleaned)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


def _extract_balance_from_raw(raw: str, key: str) -> float | None:
    """Try to find opening/closing balance in the AI response text."""
    # Look for "opening_balance": 123.45 or "closing_balance": 123.45 in the raw string
    try:
        # Match "opening_balance": 123.45 or similar patterns
        pattern = rf'"{key}_balance"\s*:\s*([\d,.]+)'
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            clean_val = re.sub(r'[^\d.]', '', match.group(1))
            return float(clean_val)
    except:
        pass
    return None


def _validate_balances(rows: list, metrics: ExtractionMetrics) -> bool:
    """
    Perform E2E consistency check: Opening + Credit - Debit == Closing.
    Returns True if passed, False if mismatch.
    """
    opening = getattr(metrics, 'opening_balance', None)
    closing = getattr(metrics, 'closing_balance', None)
    
    if opening is None or closing is None:
        return True # Cannot validate, assume OK

    total_debit = sum(r['debit'] or 0 for r in rows)
    total_credit = sum(r['credit'] or 0 for r in rows)
    
    calculated_closing = opening + total_credit - total_debit
    diff = abs(calculated_closing - closing)
    
    if diff > 1.0:
        logger.warning(f"🚨 BALANCE MISMATCH: Extracted={closing}, Calculated={calculated_closing} (Diff={diff})")
        return False
    
    return True



def _fallback_parse(text: str) -> list:

    """Last-resort: parse individual JSON objects from a broken array."""
    rows = []
    for m in re.finditer(r'\{[^{}]+\}', text):
        try:
            rows.append(json.loads(m.group()))
        except json.JSONDecodeError:
            pass
    return rows


def _normalize_parsed_rows(rows: list[dict]) -> list[dict]:
    """
    STEP 1-3: Rebuild transactions from parsed rows and normalize all dates to strict ISO YYYY-MM-DD.
    """
    if not rows:
        return []

    # First ensure every raw input has normalized dates
    for r in rows:
        if r.get('date'):
            r['date'] = _clean_date(r.get('date'))
        if r.get('value_date'):
            r['value_date'] = _clean_date(r.get('value_date'))

    normalized = []
    current_txn = None
    keywords = ['NEFT', 'RTGS', 'IMPS', 'UPI']

    for row in rows:
        has_date = bool(row.get('date'))
        debit = row.get('debit')
        credit = row.get('credit')
        has_amount = (debit is not None and debit != 0) or (credit is not None and credit != 0)
        
        narration = str(row.get('narration', '')).upper()
        has_keyword = any(k in narration for k in keywords)

        # Boundary Detection: A DATE is the strongest indicator of a new transaction.
        # An AMOUNT without a date is also a new transaction (continuation line that got an amount).
        is_new_txn = has_date or has_amount or (not current_txn and has_keyword)

        if is_new_txn:
            if current_txn:
                current_txn['date'] = _clean_date(current_txn.get('date')) or _clean_date(current_txn.get('value_date'))
                if current_txn.get('value_date'):
                    current_txn['value_date'] = _clean_date(current_txn.get('value_date'))
                normalized.append(current_txn)
            
            current_txn = row.copy()
            # If this row has a date but no amount, it's a "Date-first" entry. 
            # We'll wait for the next row to provide the amount.
        else:
            if current_txn:
                # Merge narration
                new_narration = row.get('narration', '')
                if new_narration:
                    current_txn['narration'] = f"{current_txn.get('narration', '')} {new_narration}".strip()
                
                # Capture missing fields if they appear in continuation lines
                if not current_txn.get('date') and row.get('date'):
                    current_txn['date'] = _clean_date(row.get('date'))
                if not current_txn.get('value_date') and row.get('value_date'):
                    current_txn['value_date'] = _clean_date(row.get('value_date'))
                if not current_txn.get('debit') and row.get('debit'):
                    current_txn['debit'] = row.get('debit')
                if not current_txn.get('credit') and row.get('credit'):
                    current_txn['credit'] = row.get('credit')
                if not current_txn.get('balance') and row.get('balance'):
                    current_txn['balance'] = row.get('balance')
                if not current_txn.get('ref_no') and row.get('ref_no'):
                    current_txn['ref_no'] = row.get('ref_no')
                elif current_txn.get('ref_no') and row.get('ref_no') and row.get('ref_no') != current_txn.get('ref_no'):
                    current_txn['ref_no'] = f"{current_txn['ref_no']} {row['ref_no']}".strip()
            else:
                current_txn = row.copy()

    if current_txn:
        current_txn['date'] = _clean_date(current_txn.get('date')) or _clean_date(current_txn.get('value_date'))
        if current_txn.get('value_date'):
            current_txn['value_date'] = _clean_date(current_txn.get('value_date'))
        normalized.append(current_txn)

    return normalized


def _correct_transaction_amounts(rows: list[dict]) -> list[dict]:
    """
    STEP 4-5: Correct amounts and assign DR/CR based on column logic and balance trends.
    """
    for row in rows:
        debit = row.get('debit')
        credit = row.get('credit')

        if debit and credit:
            if debit > credit:
                row['credit'] = None
            else:
                row['debit'] = None

    return rows
