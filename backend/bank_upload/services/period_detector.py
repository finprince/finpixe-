"""
period_detector.py
==================
Universal Bank Statement Period Detector & Canonical Range Model.

Detects declared statement start and end period from bank statement PDF text/metadata.
Distinguishes statement-level metadata range from individual transaction dates.

Canonical Model:
{
    "statement_start_date": "YYYY-MM-DD" | None,
    "statement_end_date": "YYYY-MM-DD" | None,
    "statement_range_source": "STATEMENT_METADATA" | "TRANSACTION_DATE_FALLBACK" | "NONE"
}
"""
import re
import logging
from datetime import datetime
import fitz

logger = logging.getLogger('bank_upload.period_detector')

MONTHS_MAP = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
    'january': '01', 'february': '02', 'march': '03', 'april': '04', 'june': '06',
    'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12'
}


def clean_date_token(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip().replace('\xa0', ' ')
    
    # 1. Named month formats: 10-Jul-2026, 01-Apr-2023, 1 Feb 2025, 31 March 2024, Jul 10 2026
    m_named = re.search(r'(?<!\d)(\d{1,2})[-/\s]+([a-zA-Z]+)[-/\s]+(20\d{2}|\d{2})(?!\d)', s)
    if m_named:
        d, m_str, y = m_named.groups()
        m_lower = m_str.lower()
        if m_lower in MONTHS_MAP:
            if len(y) == 2:
                y = '20' + y
            try:
                date_s = f'{y}-{MONTHS_MAP[m_lower]}-{int(d):02d}'
                datetime.strptime(date_s, '%Y-%m-%d')
                return date_s
            except ValueError:
                pass

    m_named_rev = re.search(r'([a-zA-Z]+)[-/\s]+(\d{1,2})[,\s]+(20\d{2}|\d{2})(?!\d)', s)
    if m_named_rev:
        m_str, d, y = m_named_rev.groups()
        m_lower = m_str.lower()
        if m_lower in MONTHS_MAP:
            if len(y) == 2:
                y = '20' + y
            try:
                date_s = f'{y}-{MONTHS_MAP[m_lower]}-{int(d):02d}'
                datetime.strptime(date_s, '%Y-%m-%d')
                return date_s
            except ValueError:
                pass

    # 2. Standard ISO numeric formats: YYYY-MM-DD
    m_iso = re.search(r'(?<!\d)(20\d{2})[-/\.](\d{1,2})[-/\.](\d{1,2})(?!\d)', s)
    if m_iso:
        y, mth, d = m_iso.groups()
        try:
            date_s = f'{y}-{int(mth):02d}-{int(d):02d}'
            datetime.strptime(date_s, '%Y-%m-%d')
            return date_s
        except ValueError:
            pass

    # 3. Standard numeric formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY, DD/MM/YY
    m_dmy = re.search(r'(?<!\d)(\d{1,2})[-/\.](\d{1,2})[-/\.](20\d{2}|\d{2})(?!\d)', s)
    if m_dmy:
        d, mth, y = m_dmy.groups()
        if len(y) == 2:
            y = '20' + y
        try:
            date_s = f'{y}-{int(mth):02d}-{int(d):02d}'
            datetime.strptime(date_s, '%Y-%m-%d')
            return date_s
        except ValueError:
            pass

    return None


def detect_statement_range_canonical(file_bytes_or_obj, transaction_dates=None) -> dict:
    """
    Universal statement date range detection.

    Returns canonical dict:
    {
        "statement_start_date": "YYYY-MM-DD" | None,
        "statement_end_date": "YYYY-MM-DD" | None,
        "statement_range_source": "STATEMENT_METADATA" | "TRANSACTION_DATE_FALLBACK" | "NONE"
    }
    """
    try:
        if isinstance(file_bytes_or_obj, (bytes, bytearray)):
            doc = fitz.open(stream=file_bytes_or_obj, filetype='pdf')
        elif isinstance(file_bytes_or_obj, str):
            doc = fitz.open(file_bytes_or_obj)
        else:
            content = file_bytes_or_obj.read()
            file_bytes_or_obj.seek(0)
            doc = fitz.open(stream=content, filetype='pdf')
    except Exception as e:
        logger.warning(f"Could not open PDF for period detection: {e}")
        doc = None

    if doc:
        text = ''
        try:
            pages_to_check = list(range(min(3, len(doc))))
            if len(doc) > 3:
                pages_to_check.append(len(doc) - 1)
            for p in pages_to_check:
                text += doc[p].get_text('text') + '\n'
        except Exception as e:
            logger.warning(f"Error reading text for period detection: {e}")

        clean_text = re.sub(r'[\r\n\t\xa0]+', ' ', text)

        patterns = [
            # 1. "between <date> and <date>" (Canara, ICICI, etc.)
            r'(?:statement\s+(?:for\s+a/c\s+[^\s]+\s+)?between|between)\s+([0-9a-zA-Z\s\-/.]+?)\s+and\s+([0-9a-zA-Z\s\-/.]+)',
            
            # 2. "statement of account for the period of/from <date> to <date>" (BOB, SBI, etc.)
            r'STATEMENT\s+OF\s+ACCOUNT\s+(?:for\s+the\s+period\s+(?:of\s+)?|from\s+)?([0-9a-zA-Z\s\-/.]+?)\s+(?:to|-|–|—)\s+([0-9a-zA-Z\s\-/.]+)',
            
            # 3. "Statement From : <date> To : <date>" (Indian Bank, Axis, etc.)
            r'Statement\s+From\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+To\s*:\s*([0-9a-zA-Z\s\-/.]+)',
            
            # 4. "Account Statement from <date> to <date>"
            r'Account\s+Statement\s+from\s+([0-9a-zA-Z\s\-/.]+?)\s+(?:to|-|–|—)\s+([0-9a-zA-Z\s\-/.]+)',
            
            # 5. "Statement Period : <date> to <date>" or "Period : <date> - <date>"
            r'(?:Statement\s+Period|Transaction\s+Period|Period)\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+(?:to|-|–|—)\s+([0-9a-zA-Z\s\-/.]+)',
            
            # 6. "From Date : <date> To Date : <date>" or "From : <date> To : <date>" (HDFC, etc.)
            r'From\s+(?:Date\s*)?:\s*([0-9a-zA-Z\s\-/.]+?)\s+To\s+(?:Date\s*)?:\s*([0-9a-zA-Z\s\-/.]+)',
            
            # 7. "for the period <date> to <date>"
            r'for\s+the\s+period\s+(?:of\s+)?([0-9a-zA-Z\s\-/.]+?)\s+(?:to|-|–|—)\s+([0-9a-zA-Z\s\-/.]+)',
            
            # 8. "Txn Date from <date> to <date>"
            r'Txn\s+Date\s+from\s+([0-9a-zA-Z\s\-/.]+?)\s+(?:to|-|–|—)\s+([0-9a-zA-Z\s\-/.]+)',
            
            # 9. Explicit date range in header: "01-APR-2023 to 31-MAR-2024" or "01/06/2025 – 15/08/2025"
            r'(\d{1,2}[-/\.][a-zA-Z0-9]+[-/\.](?:20\d{2}|\d{2}))\s+(?:to|-|–|—)\s+(\d{1,2}[-/\.][a-zA-Z0-9]+[-/\.](?:20\d{2}|\d{2}))'
        ]

        for pat in patterns:
            for m in re.finditer(pat, clean_text, re.IGNORECASE):
                s_cand = clean_date_token(m.group(1))
                e_cand = clean_date_token(m.group(2))
                if s_cand and e_cand and s_cand <= e_cand:
                    logger.info(f"[PERIOD DETECT] Found statement period from metadata: {s_cand} -> {e_cand}")
                    return {
                        "statement_start_date": s_cand,
                        "statement_end_date": e_cand,
                        "statement_range_source": "STATEMENT_METADATA"
                    }

    # Fallback to minimum and maximum transaction dates if provided and valid
    if transaction_dates:
        valid_dates = sorted([d for d in transaction_dates if d and clean_date_token(d)])
        if valid_dates:
            min_d = clean_date_token(valid_dates[0])
            max_d = clean_date_token(valid_dates[-1])
            if min_d and max_d:
                logger.info(f"[PERIOD DETECT] Falling back to transaction dates: {min_d} -> {max_d}")
                return {
                    "statement_start_date": min_d,
                    "statement_end_date": max_d,
                    "statement_range_source": "TRANSACTION_DATE_FALLBACK"
                }

    return {
        "statement_start_date": None,
        "statement_end_date": None,
        "statement_range_source": "NONE"
    }


def detect_pdf_statement_period(file_bytes_or_obj) -> tuple[str | None, str | None]:
    """
    Backwards-compatible wrapper returning (start_date, end_date).
    """
    res = detect_statement_range_canonical(file_bytes_or_obj)
    return res["statement_start_date"], res["statement_end_date"]
