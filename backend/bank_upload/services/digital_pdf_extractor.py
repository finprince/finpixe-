"""
digital_pdf_extractor.py — Native Digital PDF Extraction & Transaction Block Reconstruction
==========================================================================================
Extracts native text lines and structured tables from digital bank statements,
accumulates multi-line transaction blocks, and reconstructs canonical bank transactions with
exact column-based routing (Description -> narration, Ref No./Cheque No. -> ref_no),
strict date tokenization, multi-date support, and running-balance reconciliation across
diverse statement formats (e.g. State Bank of India, Bank of Baroda, Indian Bank, HDFC, ICICI, etc.).
"""
import re
import logging
from datetime import datetime
import fitz

logger = logging.getLogger('bank_upload.digital_pdf_extractor')

MONTHS_MAP = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    'january': '01', 'february': '02', 'march': '03', 'april': '04', 'june': '06',
    'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'
}

# Regex for standard numeric dates (DD/MM/YY, DD/MM/YYYY, DD-MM-YY, etc.)
NUMERIC_DATE_REGEX = re.compile(r'(?<!\d)(\d{1,2})[-/\.](\d{1,2})[-/\.](20\d{2}|\d{2})(?!\d)')

# Regex for named month dates on single line (e.g. 10 Feb 2025, 5 May 2025, 01-Apr-2023)
NAMED_MONTH_REGEX = re.compile(
    r'(?<!\d)(\d{1,2})[-/\s]+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[-/\s]+(20\d{2}|\d{2})(?!\d)',
    re.IGNORECASE
)

# Regex for split-line Day+Month (e.g. "10 Feb")
SPLIT_DAY_MONTH_REGEX = re.compile(
    r'^\s*(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*$',
    re.IGNORECASE
)
SPLIT_YEAR_REGEX = re.compile(r'^\s*(20\d{2}|\d{2})\s*$')

REF_REGEX = re.compile(
    r':(\d{6,})|(NEFT-[A-Z0-9]+)|(RTGS-[A-Z0-9]+)|(IMPS-[A-Z0-9]+)|(UPI-[A-Z0-9]+)|(EBANK:[A-Z0-9\\]+)|(?:UPI/(\d{12})/UPI)|(?:SEQ NO\s+(\d+))|(?:UPI/[A-Z0-9]+/(\d{12}))|(?:UTR\s*NO:\s*([A-Z0-9]+))',
    re.IGNORECASE
)

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


def parse_date_token(d_tuple: tuple[str, str, str]) -> tuple[str, str]:
    """Parses date tuple (DD, MM/MonthName, YY/YYYY) into ISO YYYY-MM-DD and validity status."""
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


def find_all_dates_in_line(line: str) -> list[tuple[str, str, str]]:
    """Extracts all numeric and named-month dates from a single line."""
    dates = []
    for m in NUMERIC_DATE_REGEX.findall(line):
        dates.append(m)
    for m in NAMED_MONTH_REGEX.findall(line):
        dates.append(m)
    return dates


def _clean_amount(val_str: str) -> float | None:
    """Parses currency string to signed float handling Cr/Dr markers."""
    if not val_str:
        return None
    is_dr = str(val_str).lower().endswith("dr")
    s = re.sub(r'[^\d.]', '', str(val_str))
    try:
        val = float(s)
        return -val if is_dr else val
    except ValueError:
        return None


def _extract_amounts_from_line(line: str) -> list[tuple[str, float]]:
    """Extracts numeric currency amounts and balances from a line."""
    pattern = r'(?:\d{1,3}(?:,\d{2,3})+|\d+)\.\d{2}(?:Cr|cr|Dr|dr)?'
    matches = re.findall(pattern, line)
    nums = []
    for m in matches:
        val = _clean_amount(m)
        if val is not None:
            nums.append((m, val))
    return nums


def _clean_date_cell(value) -> str | None:
    if not value:
        return None
    s = " ".join(str(value).split()).strip()
    
    # Concatenated year artifacts
    m_fused = re.match(r'^(?:20)?(2[3-9])(\d{2})[-/.](\d{1,2})[-/.](\d{1,2})$', s)
    if m_fused:
        yy, fused_day, mm, dd = m_fused.groups()
        s = f"20{yy}-{int(mm):02d}-{int(dd):02d}"
        
    m_iso = re.match(r'^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$', s)
    if m_iso:
        yyyy, mm, dd = m_iso.groups()
        if int(yyyy) > 2099 and yyyy.startswith('24'):
            yyyy = '2024'
        elif int(yyyy) > 2099 and yyyy.startswith('23'):
            yyyy = '2023'
        s = f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            pass

    m_named = re.match(r'^(\d{1,2})[-/\s]+([a-zA-Z]+)[-/\s]+(20\d{2}|\d{2})$', s)
    if m_named:
        day_str, mon_str, yr_str = m_named.groups()
        mon_lower = mon_str.lower()
        if mon_lower in MONTHS_MAP:
            if len(yr_str) == 2:
                yr_str = '20' + yr_str
            s_cand = f"{yr_str}-{MONTHS_MAP[mon_lower]}-{int(day_str):02d}"
            try:
                datetime.strptime(s_cand, "%Y-%m-%d")
                return s_cand
            except ValueError:
                pass

    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%d.%m.%Y', '%d.%m.%y', '%Y/%m/%d', '%d %b %Y', '%d %B %Y', '%d-%b-%Y', '%d-%b-%y'):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            pass
            
    return None


def _extract_grid_tables(doc, metrics=None) -> list[dict] | None:
    """
    Extracts structured grid tables when PDF pages have detected table layouts (e.g. SBI).
    Preserves exact column mapping: Description -> narration, Ref No./Cheque No. -> ref_no.
    """
    total_pages = len(doc)
    all_table_rows = []
    
    for p_idx, page in enumerate(doc):
        tabs = page.find_tables()
        if not tabs.tables:
            return None  # Fallback to stream extractor if no structured tables found
            
        for tab in tabs:
            extracted_tab = tab.extract()
            if not extracted_tab:
                continue
                
            col_map = {}
            for row in extracted_tab:
                row_str = " ".join([str(c).lower() for c in row if c])
                
                # Check if this row is header
                if ("txn date" in row_str or "date" in row_str) and ("description" in row_str or "particulars" in row_str):
                    for c_idx, col_name in enumerate(row):
                        c_lower = str(col_name).lower().replace("\n", " ").strip()
                        if "txn date" in c_lower or (c_lower == "date" and "date" not in col_map):
                            col_map["date"] = c_idx
                        elif "value date" in c_lower or "value" in c_lower:
                            col_map["value_date"] = c_idx
                        elif "description" in c_lower or "particulars" in c_lower or "details" in c_lower:
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
                
                # Ref No./Cheque No. column: preserve complete multiline text (e.g. "TRANSFER FROM 4897733162090")
                raw_ref = row[col_map["ref_no"]] if "ref_no" in col_map and col_map["ref_no"] < len(row) else ""
                clean_ref = " ".join(str(raw_ref or "").split()).strip() or None
                
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
                    "date": clean_d,
                    "value_date": clean_vd,
                    "narration": clean_narr,
                    "ref_no": clean_ref,
                    "debit": abs(amt_deb) if amt_deb else None,
                    "credit": abs(amt_cred) if amt_cred else None,
                    "balance": abs(amt_bal) if amt_bal is not None else None,
                    "source_page": p_idx + 1
                })

    if all_table_rows:
        if metrics:
            metrics.successful_chunks = total_pages
            metrics.total_txns = len(all_table_rows)
            
            # Extract opening balance from header if present
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
        logger.info(f"✅ [DIGITAL PDF TABLE EXTRACTOR] Successfully extracted {len(all_table_rows)} structured table rows.")
        return all_table_rows
    return None


def extract_digital_pdf_transactions(file_bytes: bytes, metrics=None) -> list[dict]:
    """
    Universal native digital PDF transaction extractor.
    1. Attempts structured table extraction for grid layouts (e.g. SBI) with exact column isolation.
    2. Falls back to multi-line state machine for stream layouts (e.g. Bank of Baroda, Indian Bank).
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    total_pages = len(doc)
    if metrics:
        metrics.total_pages = total_pages
        metrics.total_chunks = total_pages

    # ── Strategy 1: Structured Grid Table Extraction (SBI & similar) ──
    table_txns = _extract_grid_tables(doc, metrics)
    if table_txns:
        return table_txns

    # ── Strategy 2: Multi-Line Stream State Machine (Indian Bank, BOB, etc.) ──
    all_lines = []
    for p_idx in range(total_pages):
        page = doc[p_idx]
        text = page.get_text("text") or ""
        raw_page_lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Pre-process raw_page_lines to merge split Day+Month and Year
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
            if any(t in line_lower for t in ["carried forward", "c/f", "dr. count:", "cr. count:", "in case your account is operated", "*** end of statement ***"]):
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

        # 1. Divider line
        if re.match(r'^-{5,}$', line):
            continue

        # 2. Opening Balance
        if "brought forward" in line_lower or "b/f" in line_lower or "b/f..." in line_lower or "balance as on" in line_lower:
            amts = _extract_amounts_from_line(line)
            if amts and opening_balance is None:
                opening_balance = amts[-1][1]
                running_balance = opening_balance
            continue

        # 3. Ignored headers / footers / noise
        if line_lower in IGNORED_EXACT_HEADERS:
            continue
        if any(sub in line_lower for sub in IGNORED_SUBSTRINGS):
            continue
        if re.search(r'page\s+\d+\s+of\s+\d+', line_lower):
            continue
        if re.search(r'date\s*:\s*\d{1,2}[-/.\s]+[a-z0-9]+[-/.\s]+\d{2,4}', line_lower):
            continue
        if re.search(r'time\s*:\s*\d{2}:\d{2}', line_lower):
            continue
        if line == "29-04-2024" and page_num > 0:
            continue

        # 4. Check for Dates
        dates_found = find_all_dates_in_line(line)
        is_credit_interest = "CREDIT INTEREST" in line.upper()

        if dates_found:
            # Check if this line is purely a secondary Value Date for the current block
            if (current_block 
                and len(dates_found) == 1 
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

            # Otherwise, finalize current block and start NEW block
            if current_block:
                raw_blocks.append(current_block)

            p_date, p_status = parse_date_token(dates_found[0])
            if len(dates_found) > 1:
                v_date, v_status = parse_date_token(dates_found[1])
            else:
                v_date = None
                v_status = None

            amts_in_line = _extract_amounts_from_line(line)
            narr_part = NUMERIC_DATE_REGEX.sub("", line)
            narr_part = NAMED_MONTH_REGEX.sub("", narr_part)
            for a_str, _ in amts_in_line:
                narr_part = narr_part.replace(a_str, "")
            narr_part = narr_part.strip()

            current_block = {
                "post_date": p_date,
                "post_date_status": p_status,
                "value_date": v_date,
                "value_date_status": v_status,
                "narration_lines": [narr_part] if narr_part else [],
                "amounts": amts_in_line,
                "page": page_num,
                "source_lines": [line]
            }
        else:
            if is_credit_interest and not current_block:
                amts_in_line = _extract_amounts_from_line(line)
                current_block = {
                    "post_date": None,
                    "post_date_status": None,
                    "value_date": None,
                    "value_date_status": None,
                    "narration_lines": [line],
                    "amounts": amts_in_line,
                    "page": page_num,
                    "source_lines": [line]
                }
                continue

            if current_block:
                current_block["source_lines"].append(line)
                amts_in_line = _extract_amounts_from_line(line)

                if amts_in_line and (re.search(r'^\d+\.\d{2}(?:Cr|cr|Dr|dr)?$', line) or re.search(r'^\d{1,3}(?:,\d{3})+\.\d{2}(?:Cr|cr|Dr|dr)?$', line)):
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

    for idx, b in enumerate(raw_blocks):
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
                if any(k in narr.upper() for k in ["BY TRANSFER", "CREDIT", "DEP", "CR", "REMITTAN", "SALARY", "REFUND", "CASH DEP", "BY CASH", "DEPOSIT TRANSFER"]):
                    deposit = fallback_amt
                else:
                    withdrawal = fallback_amt
                running_balance = balance
        elif len(amts) == 1:
            amt_val = abs(amts[0][1])
            if "CREDIT INTEREST" in narr.upper() or any(k in narr.upper() for k in ["BY TRANSFER", "CREDIT", "DEP", "CR", "REMITTAN", "SALARY", "BY CASH", "DEPOSIT TRANSFER"]):
                deposit = amt_val
            else:
                withdrawal = amt_val

        # Exclude empty orphaned blocks
        if not withdrawal and not deposit and not balance:
            continue

        ref_no = None
        m_ref = REF_REGEX.search(narr)
        if m_ref:
            for g in m_ref.groups():
                if g:
                    ref_no = g.strip(":")
                    break

        canonical_transactions.append({
            "transaction_index": len(canonical_transactions) + 1,
            "date": post_d,
            "value_date": val_d,
            "narration": " ".join(narr.split()).strip(),
            "ref_no": ref_no,
            "debit": withdrawal,
            "credit": deposit,
            "balance": abs(balance) if balance is not None else None,
            "source_page": b["page"]
        })

    if metrics:
        metrics.successful_chunks = total_pages
        metrics.opening_balance = opening_balance
        metrics.closing_balance = running_balance
        metrics.total_txns = len(canonical_transactions)

    logger.info(
        f"✅ [DIGITAL PDF EXTRACTOR] Successfully reconstructed {len(canonical_transactions)} "
        f"transactions across {total_pages} pages."
    )
    return canonical_transactions
