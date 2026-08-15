import re
import fitz
from datetime import datetime

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
    
    # 1. Standard numeric formats: YYYY-MM-DD
    m_iso = re.search(r'(?<!\d)(20\d{2})[-/\.](\d{1,2})[-/\.](\d{1,2})(?!\d)', s)
    if m_iso:
        y, mth, d = m_iso.groups()
        try:
            date_s = f'{y}-{int(mth):02d}-{int(d):02d}'
            datetime.strptime(date_s, '%Y-%m-%d')
            return date_s
        except ValueError:
            pass

    # 2. Named month formats: 01-Apr-2023, 1 Feb 2025, 31 March 2024
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

    # 3. Standard numeric formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
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


def detect_pdf_statement_period(file_bytes_or_obj) -> tuple[str | None, str | None]:
    """
    Detects declared statement start and end period from bank statement PDF header text.
    Returns (start_date_iso, end_date_iso) e.g. ('2023-04-01', '2024-03-31') or (None, None).
    """
    try:
        if isinstance(file_bytes_or_obj, (bytes, bytearray)):
            doc = fitz.open(stream=file_bytes_or_obj, filetype='pdf')
        elif isinstance(file_bytes_or_obj, str):
            doc = fitz.open(file_bytes_or_obj)
        else:
            # File-like object (e.g. Django UploadedFile)
            content = file_bytes_or_obj.read()
            file_bytes_or_obj.seek(0)
            doc = fitz.open(stream=content, filetype='pdf')
    except Exception:
        return None, None

    text = ''
    try:
        for p in range(min(3, len(doc))):
            text += doc[p].get_text('text') + '\n'
    except Exception:
        return None, None

    # Replace newlines, tabs, and multiple spaces with a single space
    clean_text = re.sub(r'[\r\n\t\xa0]+', ' ', text)

    patterns = [
        r'STATEMENT\s+OF\s+ACCOUNT\s+(?:for\s+the\s+period\s+(?:of\s+)?|from\s+)?([0-9a-zA-Z\s\-/.]+?)\s+to\s+([0-9a-zA-Z\s\-/.]+)',
        r'Statement\s+From\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+To\s*:\s*([0-9a-zA-Z\s\-/.]+)',
        r'Account\s+Statement\s+from\s+([0-9a-zA-Z\s\-/.]+?)\s+to\s+([0-9a-zA-Z\s\-/.]+)',
        r'Statement\s+Period\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+(?:to|-)\s+([0-9a-zA-Z\s\-/.]+)',
        r'Period\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+(?:to|-)\s+([0-9a-zA-Z\s\-/.]+)',
        r'From\s+Date\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+To\s+Date\s*:\s*([0-9a-zA-Z\s\-/.]+)',
        r'From\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+To\s*:\s*([0-9a-zA-Z\s\-/.]+)',
        r'Txn\s+Date\s+from\s+([0-9a-zA-Z\s\-/.]+?)\s+to\s+([0-9a-zA-Z\s\-/.]+)',
        r'Transaction\s+Period\s*:\s*([0-9a-zA-Z\s\-/.]+?)\s+to\s+([0-9a-zA-Z\s\-/.]+)',
        # Direct explicit date range in header (e.g., "01-APR-2023 to 31-MAR-2024" or "01/04/2025 to 31/03/2026")
        r'(\d{1,2}[-/\.][a-zA-Z0-9]+[-/\.](?:20\d{2}|\d{2}))\s+(?:to|-)\s+(\d{1,2}[-/\.][a-zA-Z0-9]+[-/\.](?:20\d{2}|\d{2}))'
    ]

    for pat in patterns:
        for m in re.finditer(pat, clean_text, re.IGNORECASE):
            s_cand = clean_date_token(m.group(1))
            e_cand = clean_date_token(m.group(2))
            if s_cand and e_cand and s_cand <= e_cand:
                return s_cand, e_cand

    return None, None
