"""
digital_pdf_extractor.py - Native Digital PDF Extraction & Transaction Block Reconstruction
===========================================================================================
GLOBAL BANK STATEMENT COLUMN EXTRACTION ENGINE

Architecture:
    Strategy 1 -- Grid/table extraction (PyMuPDF find_tables): for banks with PDF table borders (SBI)
    Strategy 2 -- Coordinate-based column extraction: for banks with detectable header rows (HDFC, ICICI, Canara)
    Strategy 3 -- Multi-line stream state machine: fallback for stream-format banks (Indian Bank, BOB)

Column Authority Rule:
    The PDF physical column (determined by x-coordinate) is the ONLY authority for field assignment.
    Narration -> narration, Chq/Ref No. -> ref_no, Withdrawal -> debit, Deposit -> credit.
    ref_no is NEVER inferred from narration identifiers. Dedicated Chq/Ref fields attach to ref_no.
"""
import re
import logging
from datetime import datetime
from collections import defaultdict
import fitz

logger = logging.getLogger('bank_upload.digital_pdf_extractor')

MONTHS_MAP = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    'january': '01', 'february': '02', 'march': '03', 'april': '04', 'june': '06',
    'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'
}

NUMERIC_DATE_REGEX = re.compile(r'(?<!\d)(\d{1,2})[-/\.](\d{1,2})[-/\.](20\d{2}|\d{2})(?!\d)')
NAMED_MONTH_REGEX = re.compile(
    r'(?<!\d)(\d{1,2})[-/\s]+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-/\s]+(20\d{2}|\d{2})(?!\d)',
    re.IGNORECASE
)
SPLIT_DAY_MONTH_REGEX = re.compile(
    r'^\s*(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*$',
    re.IGNORECASE
)
SPLIT_YEAR_REGEX = re.compile(r'^\s*(20\d{2}|\d{2})\s*$')

IGNORED_EXACT_HEADERS = {
    "post date", "value", "value date", "date", "details", "chq.no.", "debit", "credit", "balance",
    "particulars", "withdrawal", "withdrawals", "deposit", "deposits", "date particulars", "chq no", "chq.no",
    "statement", "summary", "txn date", "description", "ref no./cheque", "ref no./cheque no.", "no."
}

IGNORED_SUBSTRINGS = (
    "statement of account", "account no :", "product:", "currency:", "int rate :", "cleared balance :",
    "drawing power:", "nominee name :", "ckyc id :", "branch code :", "phone no :", "email id :",
    "ifsc code :", "statement date", "statement from", "statement time", "page no.",
    "bank of baroda", "peelamedu", "address:", "helpline", "branch phone", "micr code", "a/c name",
    "nomination flag", "scheme description", "joint holders", "a/c number", "account open date",
    "https://cbdrpt001", "page no:", "page total:", "grand total:", "clrbal:", "*** end of statement ***",
    "carried forward", "c/f", "statement summary", "dr. count:", "cr. count:",
    "we are committed to treat customers", "in case your account is operated", "please contact your branch",
    "abbreviations used", "retd - returned", "cheques received in inward clearing",
    "unless the constituent notifies", "pending penal charges", "this is a computer generated",
    "transaction details", "account statement from", "cif no.", "ckycr number", "ifs code",
    "account description", "nomination registered", "balance as on", "interest rate",
    "mod balance", "please do not share your atm"
)

COLUMN_HEADER_ALIASES = {
    'date': ['date', 'txn date', 'transaction date', 'post date', 'posting date'],
    'narration': ['narration', 'description', 'particulars', 'details', 'transaction details', 'trans details'],
    'ref_no': [
        'chq./ref.no.', 'chq/ref no.', 'chq.no.', 'cheque no', 'ref no', 'reference no',
        'chq no', 'ref no./cheque no.', 'chq./ref.no', 'chq/ref', 'chq. no.', 'ref. no.',
        'cheque number', 'reference number', 'chq/ref no', 'instrument no', 'instrument number',
    ],
    'value_date': ['value dt', 'value date', 'val date', 'value dt.', 'val dt', 'effective date'],
    'debit': [
        'withdrawal amt.', 'withdrawal', 'withdrawals', 'debit', 'debit amt', 'debit amount',
        'withdrawal amt', 'dr amount', 'withdrawals(dr)', 'debit(dr)',
    ],
    'credit': [
        'deposit amt.', 'deposit', 'deposits', 'credit', 'credit amt', 'credit amount',
        'deposit amt', 'cr amount', 'deposits(cr)', 'credit(cr)',
    ],
    'balance': [
        'closing balance', 'balance', 'running balance', 'avl bal', 'available balance',
        'clg bal', 'bal', 'closing bal', 'running bal',
    ],
}

COORDINATE_NOISE_PATTERNS = [
    'opening balance', 'brought forward', 'carried forward',
    'statement summary', 'dr. count:', 'cr. count:', 'dr count',
    'total debit', 'total credit', 'page no', 'page total',
    'grand total', '*** end', 'generated on', 'generated by',
    'account no', 'ifsc', 'statement of account', 'account statement',
    'customer id', 'cif no', 'not require signature',
    'computer generated', 'hdfc bank house', 'lower parel',
    'senapati', 'registered office', 'gstin number', 'hdfcbank.com',
    'dr count', 'cr count', 'opening bal', 'closing bal',
    'debits', 'credits', 'disclaimer', 'unless the constituent',
    'pass sheet shall be deemed', 'beware of phishing', 'end of statement',
]


# ── Shared Helpers ──

def parse_date_token(d_tuple):
    day, month_part, year = d_tuple
    if len(year) == 2:
        year = "20" + year
    month_lower = month_part.lower()
    if month_lower in MONTHS_MAP:
        month = MONTHS_MAP[month_lower]
    else:
        month = f"{int(month_part):02d}"
    day = f"{int(day):02d}"
    date_str = f"{year}-{month}-{day}"
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str, "VALID"
    except ValueError:
        return date_str, "INVALID_DATE"


def find_all_dates_in_line(line):
    dates = []
    for m in NUMERIC_DATE_REGEX.findall(line):
        dates.append(m)
    for m in NAMED_MONTH_REGEX.findall(line):
        dates.append(m)
    return dates


def _clean_amount(val_str):
    if not val_str:
        return None
    is_dr = str(val_str).lower().endswith("dr")
    s = re.sub(r'[^\d.]', '', str(val_str))
    try:
        val = float(s)
        return -val if is_dr else val
    except ValueError:
        return None


def _extract_amounts_from_line(line):
    pattern = r'(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}(?:Cr|cr|Dr|dr)?'
    matches = re.findall(pattern, line)
    nums = []
    for m in matches:
        val = _clean_amount(m)
        if val is not None:
            nums.append((m, val))
    return nums


def _clean_date_cell(value):
    if not value:
        return None
    s = " ".join(str(value).split()).strip()
    # Check if multiple tokens exist (e.g. repeated dates from text overlay "29/02/24 29/02/24")
    tokens = s.split()
    if len(tokens) > 1:
        for t in tokens:
            cleaned = _clean_date_cell(t)
            if cleaned:
                return cleaned

    # 1. Named month formats: 10-Jul-2026, 01-Apr-2023, 1 Feb 2025, 31 March 2024
    m_named = re.match(r'^(\d{1,2})[-/\s]+([a-zA-Z]+)[-/\s]+(20\d{2}|\d{2})$', s)
    if m_named:
        d, m_str, y = m_named.groups()
        m_lower = m_str.lower()
        if m_lower in MONTHS_MAP:
            if len(y) == 2:
                y = '20' + y
            try:
                date_s = f'{y}-{MONTHS_MAP[m_lower]}-{int(d):02d}'
                dt = datetime.strptime(date_s, '%Y-%m-%d')
                if 1900 <= dt.year <= 2100:
                    return date_s
            except ValueError:
                pass

    # 2. Standard ISO numeric formats: YYYY-MM-DD
    m_iso = re.match(r'^(20\d{2})[-/\.](\d{1,2})[-/\.](\d{1,2})$', s)
    if m_iso:
        y, mth, d = m_iso.groups()
        try:
            date_s = f'{y}-{int(mth):02d}-{int(d):02d}'
            dt = datetime.strptime(date_s, '%Y-%m-%d')
            if 1900 <= dt.year <= 2100:
                return date_s
        except ValueError:
            pass

    # 3. Standard numeric formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY, DD/MM/YY
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

    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%d.%m.%Y', '%d.%m.%y',
                '%Y/%m/%d', '%d %b %Y', '%d %B %Y', '%d-%b-%Y', '%d-%b-%y'):
        try:
            dt = datetime.strptime(s, fmt)
            if 1900 <= dt.year <= 2100:
                return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


# ── Strategy 1: Grid/Table Extraction (SBI etc.) ──

def _extract_grid_tables(doc, metrics=None):
    """
    Extracts structured grid tables when PDF pages have detected table layouts (e.g. SBI).
    Preserves exact column mapping: Description -> narration, Ref No./Cheque No. -> ref_no.
    """
    total_pages = len(doc)
    all_table_rows = []
    for p_idx, page in enumerate(doc):
        tabs = page.find_tables()
        if not tabs.tables:
            return None
        for tab in tabs:
            extracted_tab = tab.extract()
            if not extracted_tab:
                continue
            col_map = {}
            for row in extracted_tab:
                row_str = " ".join([str(c).lower() for c in row if c])
                if (("txn date" in row_str or "date" in row_str)
                        and ("description" in row_str or "particulars" in row_str or "narration" in row_str)):
                    for c_idx, col_name in enumerate(row):
                        c_lower = str(col_name).lower().replace("\n", " ").strip()
                        if "txn date" in c_lower or (c_lower == "date" and "date" not in col_map):
                            col_map["date"] = c_idx
                        elif "value date" in c_lower or "value" in c_lower:
                            col_map["value_date"] = c_idx
                        elif ("description" in c_lower or "particulars" in c_lower
                              or "details" in c_lower or "narration" in c_lower):
                            col_map["narration"] = c_idx
                        elif "ref" in c_lower or "cheque" in c_lower or "chq" in c_lower:
                            col_map["ref_no"] = c_idx
                        elif "debit" in c_lower or "withdrawal" in c_lower:
                            col_map["debit"] = c_idx
                        elif "credit" in c_lower or "deposit" in c_lower:
                            col_map["credit"] = c_idx
                        elif "balance" in c_lower:
                            col_map["balance"] = c_idx
                    continue
                if not col_map:
                    continue
                raw_date = row[col_map["date"]] if "date" in col_map and col_map["date"] < len(row) else None
                clean_d = _clean_date_cell(raw_date)
                if not clean_d:
                    continue
                raw_vdate = row[col_map["value_date"]] if "value_date" in col_map and col_map["value_date"] < len(row) else None
                clean_vd = _clean_date_cell(raw_vdate) or clean_d
                raw_narr = row[col_map["narration"]] if "narration" in col_map and col_map["narration"] < len(row) else ""
                clean_narr = " ".join(str(raw_narr or "").split()).strip()
                raw_ref = row[col_map["ref_no"]] if "ref_no" in col_map and col_map["ref_no"] < len(row) else ""
                clean_ref = " ".join(str(raw_ref or "").split()).strip() or None
                if clean_ref in ("", "None", "null", "NULL", "---", "-", "N/A", "NA"):
                    clean_ref = None
                raw_deb = row[col_map["debit"]] if "debit" in col_map and col_map["debit"] < len(row) else None
                raw_cred = row[col_map["credit"]] if "credit" in col_map and col_map["credit"] < len(row) else None
                raw_bal = row[col_map["balance"]] if "balance" in col_map and col_map["balance"] < len(row) else None
                amt_deb = _clean_amount(raw_deb)
                amt_cred = _clean_amount(raw_cred)
                amt_bal = _clean_amount(raw_bal)
                if amt_deb is None and amt_cred is None and amt_bal is None:
                    continue
                all_table_rows.append({
                    "transaction_index": len(all_table_rows) + 1,
                    "date": clean_d, "value_date": clean_vd,
                    "narration": clean_narr, "ref_no": clean_ref,
                    "ref_source": "REFERENCE_COLUMN" if clean_ref else "NONE",
                    "narration_source": "DETAILS_COLUMN",
                    "debit": abs(amt_deb) if amt_deb else None,
                    "credit": abs(amt_cred) if amt_cred else None,
                    "balance": abs(amt_bal) if amt_bal is not None else None,
                    "source_page": p_idx + 1,
                })
    if all_table_rows:
        if metrics:
            metrics.successful_chunks = total_pages
            metrics.total_txns = len(all_table_rows)
            opening_bal = None
            p1_text = doc[0].get_text("text") or ""
            m_bal_on = re.search(r'balance\s+as\s+on[^\n:]*:\s*([\d,.]+)', p1_text, re.IGNORECASE)
            if m_bal_on:
                opening_bal = _clean_amount(m_bal_on.group(1))
            elif all_table_rows[0].get("balance") is not None:
                first_bal = all_table_rows[0]["balance"]
                first_dr = all_table_rows[0].get("debit") or 0
                first_cr = all_table_rows[0].get("credit") or 0
                opening_bal = round(first_bal - first_cr + first_dr, 2)
            metrics.opening_balance = opening_bal
            if all_table_rows[-1].get("balance") is not None:
                metrics.closing_balance = all_table_rows[-1].get("balance")
        logger.info(f"[STRATEGY 1: GRID TABLE] Extracted {len(all_table_rows)} structured rows.")
        return all_table_rows
    return None


# ── Strategy 2: Coordinate-Based Column Extraction (HDFC, ICICI, Canara and similar) ──

def _classify_column_header(text):
    text_clean = text.strip()
    if len(text_clean) > 30 or len(text_clean.split()) > 4:
        return None
    h = text_clean.lower().rstrip('.')
    for col, aliases in COLUMN_HEADER_ALIASES.items():
        for alias in aliases:
            if h == alias:
                return col
    for col, aliases in COLUMN_HEADER_ALIASES.items():
        for alias in aliases:
            if h.startswith(alias) and len(alias) >= 3:
                return col
    for col, aliases in COLUMN_HEADER_ALIASES.items():
        for alias in aliases:
            if alias in h and len(alias) >= 4:
                return col
    return None


def _detect_column_anchors(page):
    """
    Scan page for column header keywords.
    Returns (col_anchors dict {col: x0}, header_y float) or None.
    """
    blocks = page.get_text("dict")["blocks"]
    candidates = {}
    for block in blocks:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span['text'].strip()
                if not text or len(text) < 2:
                    continue
                col = _classify_column_header(text)
                if col and col not in candidates:
                    candidates[col] = {'x0': span['bbox'][0], 'y0': span['bbox'][1]}
    if len(candidates) < 4 or 'date' not in candidates:
        return None
    y_vals = [v['y0'] for v in candidates.values()]
    y_mean = sum(y_vals) / len(y_vals)
    if max(y_vals) - min(y_vals) > 12:
        candidates = {col: info for col, info in candidates.items()
                      if abs(info['y0'] - y_mean) <= 10}
        if len(candidates) < 4 or 'date' not in candidates:
            return None
        y_mean = sum(v['y0'] for v in candidates.values()) / len(candidates)
    col_anchors = {col: info['x0'] for col, info in candidates.items()}
    return col_anchors, y_mean


def _assign_span_column(x0, col_anchors):
    """
    Assign a span's x0 position to a logical column.
    """
    if not col_anchors:
        return None
    date_anchor = col_anchors.get('date', 0)
    amount_anchors = [anc for col, anc in col_anchors.items() if col in ('ref_no', 'debit', 'credit', 'balance')]
    first_amount_anchor = min(amount_anchors) if amount_anchors else 9999

    if x0 <= date_anchor + 30:
        return 'date'
    if x0 < first_amount_anchor - 15:
        return 'narration'

    sorted_right = sorted(
        [(col, anc) for col, anc in col_anchors.items() if col not in ('date', 'narration')],
        key=lambda x: x[1]
    )
    best_col = None
    for col, anchor in sorted_right:
        if x0 >= anchor - 20:
            best_col = col
    return best_col


def _is_coord_noise(texts):
    combined = ' '.join(str(t) for t in texts if t).lower().strip()
    return any(p in combined for p in COORDINATE_NOISE_PATTERNS)


def _parse_coord_date(s):
    if not s:
        return None
    s = s.strip()
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%d-%m-%Y', '%d-%m-%y', '%d.%m.%Y',
                '%Y-%m-%d', '%d %b %Y', '%d-%b-%Y', '%d-%b-%y', '%d %B %Y'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def _parse_coord_amount(s):
    if not s:
        return None
    s = str(s).strip().replace(',', '')
    try:
        return float(s)
    except ValueError:
        return None


def _extract_coordinate_transactions(doc, metrics=None):
    """
    Strategy 2: Coordinate-based column extraction.
    """
    col_anchors = None
    header_y = None
    for page_idx, page in enumerate(doc):
        result = _detect_column_anchors(page)
        if result:
            col_anchors, header_y = result
            logger.info(f"[COORD] Page {page_idx+1}: anchors={col_anchors} header_y={header_y:.1f}")
            break
    if not col_anchors:
        return None

    all_spans = []
    for page_idx, page in enumerate(doc):
        page_result = _detect_column_anchors(page)
        page_header_y = page_result[1] if page_result else None
        if page_result and len(page_result[0]) >= len(col_anchors):
            col_anchors = page_result[0]

        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span['text'].strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = span['bbox']
                    # Only filter top area if this page has a detected table header row
                    if page_header_y and y0 <= page_header_y + 2:
                        continue
                    col = _assign_span_column(x0, col_anchors)
                    all_spans.append({'col': col, 'text': text, 'x0': x0, 'y0': y0, 'page': page_idx + 1})

    if not all_spans:
        return None

    all_spans.sort(key=lambda s: (s['page'], round(s['y0'] / 3) * 3, s['x0']))

    visual_rows = []
    current_row = []
    prev_y = None
    for span in all_spans:
        y = span['y0']
        if prev_y is None or abs(y - prev_y) > 4:
            if current_row:
                visual_rows.append(current_row)
            current_row = [span]
            prev_y = y
        else:
            current_row.append(span)
    if current_row:
        visual_rows.append(current_row)

    transactions = []
    current_txn = None
    pending_leading_narr = []

    for row in visual_rows:
        by_col = defaultdict(list)
        for s in row:
            if s['col']:
                by_col[s['col']].append(s['text'])

        date_parts = by_col.get('date', [])
        narr_parts = list(by_col.get('narration', []))
        ref_parts = by_col.get('ref_no', [])
        vd_parts = by_col.get('value_date', [])
        deb_parts = by_col.get('debit', [])
        cred_parts = by_col.get('credit', [])
        bal_parts = by_col.get('balance', [])

        all_texts = list(date_parts) + narr_parts + ref_parts + vd_parts + deb_parts + cred_parts + bal_parts
        if _is_coord_noise(all_texts):
            if current_txn:
                transactions.append(current_txn)
                current_txn = None
            pending_leading_narr = []
            continue

        date_strings = []
        date_narr_overflow = []
        for t in date_parts:
            if _parse_coord_date(t):
                date_strings.append(t)
            else:
                date_narr_overflow.append(t)

        all_narr = date_narr_overflow + narr_parts
        narr_text = ' '.join(all_narr).strip()
        ref_str = ' '.join(ref_parts).strip() or None
        if ref_str in ("", "None", "null", "NULL", "---", "-", "N/A", "NA"):
            ref_str = None
        vd_str = ' '.join(vd_parts).strip()
        deb_str = ' '.join(deb_parts).strip()
        cred_str = ' '.join(cred_parts).strip()
        bal_str = ' '.join(bal_parts).strip()

        clean_d = _parse_coord_date(' '.join(date_strings)) if date_strings else None

        if clean_d:
            if current_txn:
                transactions.append(current_txn)
            clean_vd = _parse_coord_date(vd_str) or clean_d
            deb_amt = _parse_coord_amount(deb_str)
            cred_amt = _parse_coord_amount(cred_str)
            bal_amt = _parse_coord_amount(bal_str)

            combined_narr = pending_leading_narr + ([narr_text] if narr_text else [])
            pending_leading_narr = []

            current_txn = {
                'date': clean_d, 'value_date': clean_vd,
                'narration_parts': combined_narr,
                'ref_parts': [ref_str] if ref_str else [],
                'debit': abs(deb_amt) if deb_amt and deb_amt > 0 else None,
                'credit': abs(cred_amt) if cred_amt and cred_amt > 0 else None,
                'balance': bal_amt,
            }
        elif current_txn:
            if narr_text:
                current_txn['narration_parts'].append(narr_text)
            if ref_str:
                current_txn['ref_parts'].append(ref_str)
            if deb_str and current_txn['debit'] is None:
                deb_amt = _parse_coord_amount(deb_str)
                if deb_amt and deb_amt > 0:
                    current_txn['debit'] = abs(deb_amt)
            if cred_str and current_txn['credit'] is None:
                cred_amt = _parse_coord_amount(cred_str)
                if cred_amt and cred_amt > 0:
                    current_txn['credit'] = abs(cred_amt)
            if bal_str and current_txn['balance'] is None:
                current_txn['balance'] = _parse_coord_amount(bal_str)

            # If the row had a dedicated "Chq: ..." label and the transaction already has amount & balance:
            if re.search(r'^(?:chq|cheque|ref\s*no|reference\s*no|instrument\s*no)\s*:\s*', narr_text, re.IGNORECASE) and (current_txn['debit'] or current_txn['credit']) and current_txn['balance']:
                transactions.append(current_txn)
                current_txn = None
        else:
            if narr_text:
                pending_leading_narr.append(narr_text)

    if current_txn:
        transactions.append(current_txn)

    canonical = []
    for txn in transactions:
        narration = re.sub(r'\s+', ' ', ' '.join(p for p in txn['narration_parts'] if p)).strip()
        ref_no = ''.join(p for p in txn['ref_parts'] if p).strip() or None
        
        # If ref_no was not in dedicated column, check for "Chq: <num>" or "Ref No: <num>"
        if not ref_no:
            m_chq = re.search(r'(?:^|\s)(?:chq|cheque|ref\s*no|reference\s*no|instrument\s*no)\s*:\s*([a-zA-Z0-9]+)', narration, re.IGNORECASE)
            if m_chq:
                ref_no = m_chq.group(1).strip()

        balance = txn['balance']
        if balance is not None:
            balance = abs(balance)
        if txn['debit'] is None and txn['credit'] is None and balance is None:
            continue
        canonical.append({
            "transaction_index": len(canonical) + 1,
            "date": txn['date'], "value_date": txn['value_date'],
            "narration": narration, "ref_no": ref_no,
            "ref_source": "REFERENCE_COLUMN" if ref_no else "NONE",
            "narration_source": "DETAILS_COLUMN",
            "debit": txn['debit'], "credit": txn['credit'],
            "balance": balance, "source_page": 0,
        })

    if not canonical:
        return None

    if metrics:
        metrics.successful_chunks = len(doc)
        metrics.total_txns = len(canonical)
        first = canonical[0]
        first_bal = first.get('balance') or 0
        first_deb = first.get('debit') or 0
        first_cred = first.get('credit') or 0
        metrics.opening_balance = round(first_bal - first_cred + first_deb, 2)
        if canonical[-1].get('balance') is not None:
            metrics.closing_balance = canonical[-1]['balance']

    logger.info(f"[STRATEGY 2: COORDINATE] Extracted {len(canonical)} transactions.")
    return canonical


# ── Strategy 3: Multi-Line Stream State Machine (Indian Bank, BOB, and similar) ──

def _extract_stream_transactions(doc, metrics=None):
    """
    Strategy 3: Multi-line stream state machine for stream-format bank statements.
    Uses date detection as transaction boundaries.
    Uses running balance to determine debit vs credit direction.
    ref_no is ALWAYS None -- never inferred from narration.
    """
    total_pages = len(doc)
    all_lines = []

    for p_idx in range(total_pages):
        page = doc[p_idx]
        text = page.get_text("text") or ""
        raw_page_lines = [l.strip() for l in text.split("\n") if l.strip()]
        merged_page_lines = []
        i = 0
        while i < len(raw_page_lines):
            line = raw_page_lines[i]
            m_split = SPLIT_DAY_MONTH_REGEX.match(line)
            if m_split and (i + 1) < len(raw_page_lines):
                next_line = raw_page_lines[i + 1]
                m_yr = SPLIT_YEAR_REGEX.match(next_line)
                if m_yr:
                    merged_date_str = f"{m_split.group(1)} {m_split.group(2)} {m_yr.group(1)}"
                    merged_page_lines.append(merged_date_str)
                    i += 2
                    continue
            merged_page_lines.append(line)
            i += 1
        in_page_footer = False
        for line in merged_page_lines:
            line_lower = line.lower()
            if any(t in line_lower for t in [
                "carried forward", "c/f", "dr. count:", "cr. count:",
                "in case your account is operated", "*** end of statement ***"
            ]):
                in_page_footer = True
                continue
            if in_page_footer:
                continue
            all_lines.append((p_idx + 1, line))

    raw_blocks = []
    current_block = None
    opening_balance = None
    running_balance = None

    for page_num, line in all_lines:
        line_lower = line.lower()
        if re.match(r'^-{5,}$', line):
            continue
        if ("brought forward" in line_lower or "b/f" in line_lower
                or "b/f..." in line_lower or "balance as on" in line_lower):
            amts = _extract_amounts_from_line(line)
            if amts and opening_balance is None:
                opening_balance = amts[-1][1]
                running_balance = opening_balance
            continue
        if line_lower in IGNORED_EXACT_HEADERS:
            continue
        if any(sub in line_lower for sub in IGNORED_SUBSTRINGS):
            continue
        if re.search(r'page\s+\d+\s+of\s+\d+', line_lower):
            continue
        # Ignore statement header date ranges like 'To :31-Mar-2024' or 'Statement From : ...' or 'Date :29-04-2024'
        if re.search(r'^(?:statement\s+(?:from|to|date|time)|date|time|to)\s*:\s*', line_lower):
            continue

        dates_found = find_all_dates_in_line(line)
        is_credit_interest = "CREDIT INTEREST" in line.upper()
        amts_in_line = _extract_amounts_from_line(line)

        if dates_found:
            # Only treat as secondary value date if THIS line has NO amounts
            if (current_block
                    and len(dates_found) == 1
                    and not amts_in_line
                    and not current_block["narration_lines"]
                    and not current_block["amounts"]
                    and current_block["post_date"] is not None
                    and current_block["value_date"] is None):
                v_date, v_status = parse_date_token(dates_found[0])
                current_block["value_date"] = v_date
                current_block["value_date_status"] = v_status
                rem = NUMERIC_DATE_REGEX.sub("", line)
                rem = NAMED_MONTH_REGEX.sub("", rem).strip()
                if rem:
                    current_block["narration_lines"].append(rem)
                continue
            if current_block:
                raw_blocks.append(current_block)
            p_date, p_status = parse_date_token(dates_found[0])
            if len(dates_found) > 1:
                v_date, v_status = parse_date_token(dates_found[1])
            else:
                v_date = None
                v_status = None
            narr_part = NUMERIC_DATE_REGEX.sub("", line)
            narr_part = NAMED_MONTH_REGEX.sub("", narr_part)
            for a_str, _ in amts_in_line:
                narr_part = narr_part.replace(a_str, "")
            narr_part = narr_part.strip()
            current_block = {
                "post_date": p_date, "post_date_status": p_status,
                "value_date": v_date, "value_date_status": v_status,
                "narration_lines": [narr_part] if narr_part else [],
                "amounts": amts_in_line, "page": page_num, "source_lines": [line],
            }
        else:
            if is_credit_interest and not current_block:
                amts_in_line = _extract_amounts_from_line(line)
                current_block = {
                    "post_date": None, "post_date_status": None,
                    "value_date": None, "value_date_status": None,
                    "narration_lines": [line], "amounts": amts_in_line,
                    "page": page_num, "source_lines": [line],
                }
                continue
            if current_block:
                current_block["source_lines"].append(line)
                if (amts_in_line
                        and (re.search(r'^\d+\.\d{2}(?:Cr|cr|Dr|dr)?$', line)
                             or re.search(r'^\d{1,3}(?:,\d{3})+\.\d{2}(?:Cr|cr|Dr|dr)?$', line))):
                    current_block["amounts"].extend(amts_in_line)
                elif amts_in_line:
                    current_block["amounts"].extend(amts_in_line)
                    narr_part = line
                    for a_str, _ in amts_in_line:
                        narr_part = narr_part.replace(a_str, "")
                    narr_part = narr_part.strip()
                    if narr_part:
                        current_block["narration_lines"].append(narr_part)
                else:
                    current_block["narration_lines"].append(line)

    if current_block:
        raw_blocks.append(current_block)

    canonical_transactions = []
    running_balance = opening_balance

    for b in raw_blocks:
        post_d = b["post_date"]
        val_d = b["value_date"] or post_d
        narr = " ".join([l for l in b["narration_lines"] if l]).strip()
        amts = b["amounts"]
        withdrawal = None
        deposit = None
        balance = None

        if len(amts) >= 2:
            balance = amts[-1][1]
            candidate_amts = amts[:-1]
            resolved_amt = None
            resolved_type = None
            if running_balance is not None:
                for _, a_val in reversed(candidate_amts):
                    a_abs = abs(a_val)
                    calc_dr = round(running_balance - a_abs, 2)
                    calc_cr = round(running_balance + a_abs, 2)
                    if abs(calc_dr - balance) <= 0.05:
                        resolved_amt = a_abs
                        resolved_type = "dr"
                        break
                    elif abs(calc_cr - balance) <= 0.05:
                        resolved_amt = a_abs
                        resolved_type = "cr"
                        break
            if resolved_amt is not None:
                if resolved_type == "dr":
                    withdrawal = resolved_amt
                else:
                    deposit = resolved_amt
                running_balance = balance
            else:
                fallback_amt = abs(candidate_amts[-1][1])
                if any(k in narr.upper() for k in [
                    "BY TRANSFER", "CREDIT", "DEP", "REMITTAN", "SALARY",
                    "REFUND", "CASH DEP", "BY CASH", "DEPOSIT TRANSFER"
                ]):
                    deposit = fallback_amt
                else:
                    withdrawal = fallback_amt
                running_balance = balance
        elif len(amts) == 1:
            amt_val = abs(amts[0][1])
            if ("CREDIT INTEREST" in narr.upper()
                    or any(k in narr.upper() for k in [
                        "BY TRANSFER", "CREDIT", "DEP", "REMITTAN", "SALARY", "BY CASH", "DEPOSIT TRANSFER"
                    ])):
                deposit = amt_val
            else:
                withdrawal = amt_val

        if not withdrawal and not deposit and not balance:
            continue

        canonical_transactions.append({
            "transaction_index": len(canonical_transactions) + 1,
            "date": post_d, "value_date": val_d,
            "narration": " ".join(narr.split()).strip(),
            "ref_no": None, "ref_source": "NONE",
            "narration_source": "DETAILS_COLUMN",
            "debit": withdrawal, "credit": deposit,
            "balance": abs(balance) if balance is not None else None,
            "source_page": b["page"],
        })

    if metrics:
        metrics.successful_chunks = total_pages
        metrics.opening_balance = opening_balance
        metrics.closing_balance = running_balance
        metrics.total_txns = len(canonical_transactions)

    logger.info(
        f"[STRATEGY 3: STREAM] Reconstructed {len(canonical_transactions)} "
        f"transactions across {total_pages} pages."
    )
    return canonical_transactions


# ── Main Entry Point ──

def extract_digital_pdf_transactions(file_bytes, metrics=None):
    """
    Universal native digital PDF transaction extractor.

    Tries three strategies in priority order:
    1. Grid/table extraction (for SBI and banks with PDF table borders).
    2. Coordinate-based column extraction (for HDFC, ICICI, Canara and similar).
    3. Multi-line stream state machine (fallback for Indian Bank, BOB, etc.).

    All strategies produce the same canonical DTO:
    {
        "date": "YYYY-MM-DD",
        "value_date": "YYYY-MM-DD",
        "narration": "...",
        "ref_no": null | "...",
        "ref_source": "REFERENCE_COLUMN" | "NONE",
        "narration_source": "DETAILS_COLUMN",
        "debit": null | float,
        "credit": null | float,
        "balance": null | float,
    }
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    if metrics:
        metrics.total_pages = total_pages
        metrics.total_chunks = total_pages

    table_txns = _extract_grid_tables(doc, metrics)
    if table_txns:
        logger.info("[EXTRACTION] Using Strategy 1: Grid Table")
        return table_txns

    coord_txns = _extract_coordinate_transactions(doc, metrics)
    if coord_txns:
        logger.info("[EXTRACTION] Using Strategy 2: Coordinate-Based Column")
        return coord_txns

    logger.info("[EXTRACTION] Using Strategy 3: Stream State Machine")
    return _extract_stream_transactions(doc, metrics)
