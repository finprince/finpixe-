"""
digital_pdf_extractor.py — Native Digital PDF Extraction & Explicit Line Classification
====================================================================================
Bypasses OCR table Markdown reconstruction for digital PDFs.
Extracts native text lines, classifies each line explicitly, and reconstructs canonical bank transactions.

Line Classification Taxonomy:
  - TRANSACTION_START        : Valid date anchor + transaction amount(s)
  - TRANSACTION_CONTINUATION : Continuation text belonging to preceding transaction
  - OPENING_BALANCE          : Initial "B/F" opening balance row
  - PAGE_HEADER              : Bank header, address, branch info, table headers
  - PAGE_FOOTER              : Page numbers, website links, disclaimer text
  - BLANK                    : Empty whitespace line
  - UNKNOWN                  : Unclassified text line
"""
import io
import re
import logging
import pypdf

logger = logging.getLogger('bank_upload.digital_pdf_extractor')

DATE_REGEX = re.compile(r'^\s*(\d{2})[-/\.](\d{2})[-/\.](\d{2,4})\b')
REF_REGEX = re.compile(r':(\d{6,})|(NEFT-[A-Z0-9]+)|(RTGS-[A-Z0-9]+)|(IMPS-[A-Z0-9]+)|(UPI-[A-Z0-9]+)|(EBANK:[A-Z0-9\\]+)', re.IGNORECASE)

IGNORED_HEADERS = [
    "BANK OF BARODA", "PEELAMEDU", "ADDRESS:", "HELPLINE", "BRANCH PHONE",
    "MICR CODE", "A/C Name", "City", "Tel No", "Nomination", "Scheme Description",
    "Joint Holders", "A/C Number", "Statement of account", "DATE PARTICULARS",
    "https://cbdrpt001", "Page No:", "Page Total:", "Grand Total:", "ClrBal:"
]


def _parse_date(date_str: str) -> str | None:
    m = DATE_REGEX.search(date_str)
    if not m:
        return None
    d, m_val, y = m.group(1), m.group(2), m.group(3)
    if len(y) == 2:
        y = "20" + y
    return f"{y}-{m_val}-{d}"


def _clean_amount(val_str: str) -> float | None:
    if not val_str:
        return None
    s = re.sub(r'[^\d.]', '', val_str)
    try:
        val = float(s)
        return val if val >= 0 else None
    except ValueError:
        return None


def _extract_amounts_from_line(line: str) -> list[tuple[str, float]]:
    pattern = r'(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}'
    matches = re.findall(pattern, line)
    nums = []
    for m in matches:
        val = _clean_amount(m)
        if val is not None:
            nums.append((m, val))
    return nums


def classify_line(line_text: str) -> tuple[str, str | None, list[tuple[str, float]]]:
    """
    Classifies a raw text line into explicit line classification taxonomy.
    """
    clean_t = line_text.strip()
    if not clean_t:
        return "BLANK", None, []

    if any(h in clean_t for h in IGNORED_HEADERS):
        if "Page Total:" in clean_t or "Grand Total:" in clean_t or "https://cbdrpt001" in clean_t:
            return "PAGE_FOOTER", None, []
        return "PAGE_HEADER", None, []

    amts = _extract_amounts_from_line(clean_t)

    if "B/F" in clean_t:
        return "OPENING_BALANCE", None, amts

    parsed_d = _parse_date(clean_t)
    if parsed_d and amts:
        return "TRANSACTION_START", parsed_d, amts
    elif parsed_d:
        return "TRANSACTION_START", parsed_d, []
    elif len(amts) >= 2:
        return "TRANSACTION_START", None, amts

    return "TRANSACTION_CONTINUATION", None, []


def extract_digital_pdf_transactions(file_bytes: bytes, metrics=None) -> list[dict]:
    """
    Native digital PDF transaction extractor with explicit line taxonomy classification.
    """
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    total_pages = len(reader.pages)
    if metrics:
        metrics.total_pages = total_pages
        metrics.total_chunks = total_pages

    native_lines = []
    for p_idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        lines = text.split("\n")
        for l_idx, l in enumerate(lines):
            l_clean = l.strip()
            line_type, parsed_d, amts = classify_line(l_clean)
            native_lines.append({
                "page": p_idx + 1,
                "line_index": l_idx,
                "text": l_clean,
                "classification": line_type,
                "date": parsed_d,
                "amounts": amts
            })

    canonical_transactions = []
    current_txn = None
    opening_balance = None
    running_balance = None

    for line_obj in native_lines:
        c_type = line_obj["classification"]
        text = line_obj["text"]
        amts = line_obj["amounts"]
        date_str = line_obj["date"]

        if c_type == "OPENING_BALANCE":
            if amts:
                opening_balance = amts[-1][1]
                running_balance = opening_balance
                if metrics:
                    metrics.opening_balance = opening_balance
                logger.info(f"[DIGITAL PDF EXTRACTOR] Captured Opening Balance: {opening_balance}")
            continue

        if c_type in ("PAGE_HEADER", "PAGE_FOOTER", "BLANK"):
            continue

        if c_type == "TRANSACTION_START":
            if current_txn:
                canonical_transactions.append(current_txn)

            withdrawal = None
            deposit = None
            balance = None

            if len(amts) >= 2:
                amt_val = amts[0][1]
                balance = amts[1][1]
            elif len(amts) == 1:
                amt_val = amts[0][1]
                balance = None
            else:
                amt_val = None
                balance = None

            if balance is not None and running_balance is not None and amt_val is not None:
                calc_if_withdrawal = round(running_balance - amt_val, 2)
                calc_if_deposit = round(running_balance + amt_val, 2)

                if abs(calc_if_withdrawal - balance) <= 0.05:
                    withdrawal = amt_val
                elif abs(calc_if_deposit - balance) <= 0.05:
                    deposit = amt_val
                else:
                    withdrawal = amt_val
                running_balance = balance
            elif amt_val is not None:
                withdrawal = amt_val

            narr_text = text
            if date_str:
                narr_text = DATE_REGEX.sub("", narr_text).strip()
            for a_raw, a_val in amts:
                narr_text = narr_text.replace(a_raw, "").strip()

            current_txn = {
                "date": date_str,
                "narration": narr_text,
                "debit": withdrawal,
                "credit": deposit,
                "balance": balance,
                "ref_no": None,
                "source_page": line_obj["page"]
            }
        elif c_type == "TRANSACTION_CONTINUATION":
            if current_txn:
                current_txn["narration"] += " " + text

    if current_txn:
        canonical_transactions.append(current_txn)

    # Reference Number Extraction & Narration Cleanup
    for txn in canonical_transactions:
        narr = txn["narration"]
        m = REF_REGEX.search(narr)
        if m:
            txn["ref_no"] = m.group(0).strip(":")
        txn["narration"] = " ".join(narr.split()).strip()

    if metrics:
        metrics.successful_chunks = total_pages
        metrics.closing_balance = running_balance
        metrics.total_txns = len(canonical_transactions)

    logger.info(
        f"✅ [DIGITAL PDF EXTRACTOR] Successfully reconstructed {len(canonical_transactions)} "
        f"transactions across {total_pages} pages."
    )
    return canonical_transactions
