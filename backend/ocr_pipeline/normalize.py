from .schema import CanonicalInvoiceSchema, CanonicalInvoiceItem
import logging
import re
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

logger = logging.getLogger(__name__)

def log_canonical_schema_locked(invoice_no: str):
    logger.info(f"[CANONICAL_SCHEMA_LOCKED] invoice_no='{invoice_no}'")

def log_schema_drift_detected(field: str, expected_type: str, actual_type: str):
    logger.warning(f"[SCHEMA_DRIFT_DETECTED] field='{field}' expected='{expected_type}' actual='{actual_type}'")

# ── OCR & MAPPING CONSTANTS ──────────────────────────────────────────────────
_OCR_DIGIT_MAP = str.maketrans({
    'o': '0', 'O': '0',
    'l': '1', 'I': '1', 'L': '1',
    'S': '5', 'Z': '2',
    'G': '6', 'B': '8',
})

# [GSTIN_REGEX] (Requirement #1)
GSTIN_PATTERN = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')

def validate_gstin_checksum(gstin: str) -> bool:
    """
    Validates GSTIN using checksum digit (Mod 36).
    """
    if not gstin or len(gstin) != 15:
        return False
    
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    try:
        factor = 1
        total = 0
        for i in range(14):
            val = chars.find(gstin[i])
            if val == -1: return False
            digit = val * factor
            total += (digit // 36) + (digit % 36)
            factor = 2 if factor == 1 else 1
        
        checksum = (36 - (total % 36)) % 36
        return chars[checksum] == gstin[14]
    except:
        return False

def normalize_gstin_safe(gstin: Any) -> str:
    """
    [PHASE 4] Non-destructive GSTIN normalization.
    Only applies OCR heuristics if the original fails checksum AND the 
    result of correction yields a valid checksum.
    """
    if is_empty(gstin): return ""
    raw = str(gstin).strip().upper().replace(" ", "")
    
    # Clean noise: remove common OCR artifacts like leading/trailing special chars
    raw = re.sub(r'[^A-Z0-9]', '', raw)

    # 1. If already valid by REGEX or CHECKSUM, DO NOT MUTATE (Requirement #1)
    if GSTIN_PATTERN.match(raw) or validate_gstin_checksum(raw):
        logger.info(f"[GSTIN_VALIDATED] '{raw}' (Normalization skipped)")
        return raw
    
    # 2. Try OCR corrections only if the length is plausible (15)
    if len(raw) == 15:
        corrected = raw.translate(_OCR_DIGIT_MAP)
        if validate_gstin_checksum(corrected) or GSTIN_PATTERN.match(corrected):
            logger.info(f"[GSTIN_CORRECTED] original='{raw}' corrected='{corrected}'")
            return corrected
    
    # 3. If still invalid, return raw but log warning
    logger.warning(f"[GSTIN_INVALID] checksum/regex failed for '{raw}'")
    return raw

def recover_buyer_gstin(invoice: Any, current_val: str) -> Optional[str]:
    """
    Production Phase 3: Deterministic Buyer GSTIN Recovery.
    Recovers GSTIN from the Buyer OCR block using checksum and regex verification.
    """
    import os
    # 1. Verification of Flag
    if not os.getenv("NORMALIZER_BUYER_RECOVERY", "false").lower() == "true":
        return None

    # 2. Prefer existing structured extraction metadata first.
    address_str = ""
    if isinstance(invoice, dict):
        address_str = (invoice.get("billing_address") or invoice.get("buyer_address") or 
                       invoice.get("header", {}).get("billing_address") or 
                       invoice.get("header", {}).get("buyer_address") or "")
    
    if address_str:
        cleaned_addr = re.sub(r'[^A-Z0-9]', '', str(address_str).upper())
        for idx in range(len(cleaned_addr) - 14):
            cand = cleaned_addr[idx:idx+15]
            if GSTIN_PATTERN.match(cand) and validate_gstin_checksum(cand):
                logger.info(f"[BUYER_GSTIN_RECOVERY_ADDR_HIT] recovered='{cand}'")
                return cand

    # 3. Retrieve raw OCR text for layout search
    ocr_text = ""
    if isinstance(invoice, dict):
        ocr_text = invoice.get("_pdf_ocr_text") or invoice.get("_raw_text") or ""
    
    if not ocr_text:
        return None

    # 4. Extract Buyer OCR region using boundary regex tokens
    start_pattern = r"(?:Buyer\s*\(Bill\s*to\)|Details\s*of\s*Receiver\s*\(Billed\s*to\)|Details\s*of\s*Receiver|Billed\s*to|Dtails\s*oi\s*Rocolvor\s*Dlcd\s*to|Dlcd\s*to|Bill\s*to)"
    stop_tokens = r"(?:Place\s*of\s*Supply|Puce\s*ol\s*Supply|Dated|Delivery\s*Note|Invoice\s*No|Voucher\s*No|Total|Description|Sl\s*No|E-Way|E\s*WAY)"
    match = re.search(fr"{start_pattern}(.*?){stop_tokens}", ocr_text, re.DOTALL | re.IGNORECASE)
    
    buyer_block = ""
    if match:
        buyer_block = match.group(1).strip()
        logger.info(f"[BUYER_GSTIN_RECOVERY_BLOCK_HIT] block_len={len(buyer_block)}")
    else:
        match_desperate = re.search(fr"{start_pattern}(.{{1,500}}?)", ocr_text, re.DOTALL | re.IGNORECASE)
        if match_desperate:
            buyer_block = match_desperate.group(1).strip()
            logger.info(f"[BUYER_GSTIN_RECOVERY_DESPERATE_HIT] block_len={len(buyer_block)}")
        else:
            logger.info("[BUYER_GSTIN_RECOVERY_ABORT] Buyer OCR block could not be isolated.")
            return None

    # 5. Clean whitespace, punctuation, separators, and OCR artefacts
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', buyer_block).upper()

    # 6. Scan for contiguous 15-character sequences and test substitutions
    for i in range(len(cleaned) - 14):
        cand = cleaned[i:i+15]
        
        if GSTIN_PATTERN.match(cand) and validate_gstin_checksum(cand):
            logger.info(f"[BUYER_GSTIN_RECOVERY_RAW_HIT] recovered='{cand}'")
            return cand
            
        cand_list = list(cand)
        for pos in [0, 1]:
            if cand_list[pos] in ('O', 'o'): cand_list[pos] = '0'
            elif cand_list[pos] in ('I', 'l', 'L'): cand_list[pos] = '1'
            elif cand_list[pos] == 'S': cand_list[pos] = '5'
            elif cand_list[pos] == 'B': cand_list[pos] = '8'
            elif cand_list[pos] == 'Z': cand_list[pos] = '2'
        for pos in range(2, 7):
            if cand_list[pos] == '0': cand_list[pos] = 'O'
            elif cand_list[pos] == '1': cand_list[pos] = 'I'
            elif cand_list[pos] == '5': cand_list[pos] = 'S'
            elif cand_list[pos] == '8': cand_list[pos] = 'B'
            elif cand_list[pos] == '2': cand_list[pos] = 'Z'
        for pos in range(7, 11):
            if cand_list[pos] in ('O', 'o'): cand_list[pos] = '0'
            elif cand_list[pos] in ('I', 'l', 'L'): cand_list[pos] = '1'
            elif cand_list[pos] == 'S': cand_list[pos] = '5'
            elif cand_list[pos] == 'B': cand_list[pos] = '8'
            elif cand_list[pos] == 'Z': cand_list[pos] = '2'
        if cand_list[11] == '0': cand_list[11] = 'O'
        elif cand_list[11] == '1': cand_list[11] = 'I'
        elif cand_list[11] == '5': cand_list[11] = 'S'
        elif cand_list[11] == '8': cand_list[11] = 'B'
        elif cand_list[11] == '2': cand_list[11] = 'Z'
        if cand_list[13] != 'Z':
            if cand_list[13] in ('2', '7', 'S', 's'):
                cand_list[13] = 'Z'
                
        corrected = "".join(cand_list)
        if GSTIN_PATTERN.match(corrected) and validate_gstin_checksum(corrected):
            logger.info(f"[BUYER_GSTIN_RECOVERY_CORRECTED_HIT] original='{cand}' corrected='{corrected}'")
            return corrected

    logger.info("[BUYER_GSTIN_RECOVERY_ABORT] No valid GSTIN candidates found.")
    return None


EMPTY_VALUES = [None, "", [], {}, 0, 0.0, "0.0", "0.00", "—", "N/A", "null", "MISSING", "nan", "NaN"]

# ── UTILITIES ────────────────────────────────────────────────────────────────

def is_empty(val: Any) -> bool:
    """Strict check for empty values to prevent destructive overwrites."""
    if val in EMPTY_VALUES:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, str) and val.lower() == "missing":
        return True
    return False

def normalize_amount(amount: Any) -> float:
    if is_empty(amount):
        return 0.0
    if isinstance(amount, (int, float)):
        return float(amount)
    raw = str(amount).strip()
    try:
        # Attempt direct parsing first if it is a valid numeric string
        direct_clean = re.sub(r'^(?:Rs\.?|INR|USD|EUR|GBP|₹|\$|€|£)\s*', '', raw, flags=re.IGNORECASE)
        direct_clean = direct_clean.replace(',', '')
        return float(direct_clean)
    except (ValueError, TypeError):
        pass

    raw_sub = re.sub(r'^(?:Rs\.?|INR|USD|EUR|GBP|₹|\$|€|£)\s*', '', raw, flags=re.IGNORECASE)
    compacted = re.sub(r'(?<=\d)\s+(?=\d)', '', raw_sub)
    ocr_fixed = compacted.translate(_OCR_DIGIT_MAP)
    try:
        cleaned = re.sub(r'[^\d.-]', '', ocr_fixed)
        result = float(cleaned) if cleaned else 0.0
        return result
    except (ValueError, TypeError):
        return 0.0

def normalize_date(date_val: Any) -> str:
    """Robust date normalization to dd-mm-yyyy with exhaustive format support."""
    if is_empty(date_val): return ""
    if isinstance(date_val, datetime): 
        return date_val.strftime("%d-%m-%Y")
    
    raw = str(date_val).strip()
    logger.info(f"[DATE_PARSE_ATTEMPT] '{raw}'")
    
    # Remove boundary noise
    raw_clean = re.sub(r'^[^a-zA-Z0-9]+', '', raw)
    raw_clean = re.sub(r'[^a-zA-Z0-9]+$', '', raw_clean)
    
    # Standardize separators
    clean_str = re.sub(r'[./\\]', '-', raw_clean)
    
    _FORMATS = [
        "%d-%m-%Y", "%Y-%m-%d", "%d-%m-%y", "%m-%d-%Y",
        "%d %b %Y", "%d-%b-%Y", "%d-%b-%y", "%b %d %Y",
        "%d %B %Y", "%d-%B-%Y", "%B %d, %Y", "%d/%m/%Y",
        "%Y/%m/%d", "%m/%d/%Y", "%d.%m.%Y", "%d %b %y",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"
    ]
    
    for fmt in _FORMATS:
        try:
            dt = datetime.strptime(clean_str, fmt)
            res = dt.strftime("%d-%m-%Y")
            logger.info(f"[DATE_PARSE_SUCCESS] '{raw}' -> '{res}' (fmt: {fmt})")
            return res
        except:
            try:
                dt = datetime.strptime(raw, fmt)
                res = dt.strftime("%d-%m-%Y")
                logger.info(f"[DATE_PARSE_SUCCESS] '{raw}' -> '{res}' (fmt: {fmt})")
                return res
            except: continue
            
    logger.warning(f"[DATE_PARSE_FAIL] Could not parse: '{raw}'")
    return raw

def normalize_state(state: Any) -> str:
    """Canonical mapping for Indian States and UTs."""
    if is_empty(state): return ""
    raw = str(state).strip()
    
    # FREEZE RAW VALUE
    raw_frozen = raw
    
    value = re.sub(r'\s+', ' ', raw)
    value = re.sub(r'\bcode\s*:?\s*$', '', value, flags=re.I)
    value = value.rstrip(",:- ")
    value = value.strip()
    
    # Semantic match
    upper_val = value.upper()
    upper_val = re.sub(r'^\d+\s*[-/]?\s*', '', upper_val)
    upper_val = re.sub(r'\s*[-/]?\s*\d+$', '', upper_val)

    STATE_MAP = {
        "TN": "Tamil Nadu", "TAMIL NADU": "Tamil Nadu", "TAMILNADU": "Tamil Nadu",
        "KA": "Karnataka", "KARNATAKA": "Karnataka",
        "KL": "Kerala", "KERALA": "Kerala",
        "AP": "Andhra Pradesh", "ANDHRA PRADESH": "Andhra Pradesh",
        "TS": "Telangana", "TELANGANA": "Telangana",
        "MH": "Maharashtra", "MAHARASHTRA": "Maharashtra",
        "DL": "Delhi", "DELHI": "Delhi", "NEW DELHI": "Delhi",
        "GJ": "Gujarat", "GUJARAT": "Gujarat",
        "HR": "Haryana", "HARYANA": "Haryana",
        "PB": "Punjab", "PUNJAB": "Punjab",
        "RJ": "Rajasthan", "RAJASTHAN": "Rajasthan",
        "UP": "Uttar Pradesh", "UTTAR PRADESH": "Uttar Pradesh",
        "WB": "West Bengal", "WEST BENGAL": "West Bengal",
    }
    
    for kw, canonical in STATE_MAP.items():
        if upper_val == kw or upper_val == canonical.upper():
            if len(canonical) < len(raw_frozen) * 0.85:
                logger.warning(f"[FIELD_NORMALIZATION_DIFF] field=place_of_supply raw='{raw_frozen}' normalized='{canonical}'")
            return canonical
            
    if len(value) < len(raw_frozen) * 0.85:
        logger.warning(f"[FIELD_NORMALIZATION_DIFF] field=place_of_supply raw='{raw_frozen}' normalized='{value}'")
    return value.title()

def fix_encoding_corruption(val: Any) -> str:
    """
    [PHASE 11.9] Heuristic to fix common UTF-8 -> Latin-1 double-encoding corruption.
    Example: "Zoho â€“ Invoice" -> "Zoho – Invoice"
    """
    if not isinstance(val, str) or not val:
        return val
    
    # Common corruption sequences for en-dash, em-dash, smart quotes
    corrupt_chars = ["\u00e2", "\u0080", "\u0093", "\u0094", "\u0099", "\u0082", "\u00ac"]
    if any(c in val for c in corrupt_chars):
        try:
            # Re-encode as Latin-1 then decode as UTF-8
            fixed = val.encode('latin-1').decode('utf-8')
            logger.info(f"[ENCODING_RECOVERY] Fixed corrupted string: '{val[:20]}...' -> '{fixed[:20]}...'")
            return fixed
        except Exception:
            pass
    return val

def sanitize_description(desc: Any) -> str:
    """Isolates item descriptions from HSN/SAC codes and OCR table noise."""
    if is_empty(desc): return ""
    raw = fix_encoding_corruption(str(desc).strip())
    # Remove SAC/HSN codes and labels
    raw = re.sub(r'(?i)\b(HSN|SAC|HSN/SAC)(\s*CODE)?\s*[:/-]?\s*\d+', '', raw)
    # Remove common meta-noise
    raw = re.sub(r'(?i)\bGST\s*\d+\s*%', '', raw)
    raw = re.sub(r'[|]', '', raw)
    res = re.sub(r'\s+', ' ', raw).strip()
    return res

def merge_item_continuations(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Structurally merges multiline descriptions that were split into separate rows."""
    if not items: return []
    logger.info(f"[FORENSIC_MERGE_START] items_in={len(items)}")
    merged = []
    for item in items:
        # Support both snake_case and Title Case
        desc = item.get("description") or item.get("Item Name") or ""
        qty = item.get("qty") or item.get("Qty") or 0
        taxable = item.get("taxable_value") or item.get("Taxable Value") or 0
        rate = item.get("rate") or item.get("Item Rate") or 0
        
        # A continuation row typically has a description but no financial participation
        is_continuation = False
        if not is_empty(desc) and is_empty(qty) and is_empty(taxable) and is_empty(rate):
            is_continuation = True
            
        if is_continuation and merged:
            prev_desc = merged[-1].get("description") or merged[-1].get("Item Name") or ""
            new_desc = prev_desc + " " + desc
            # Update whichever key exists
            if "description" in merged[-1]: merged[-1]["description"] = new_desc
            if "Item Name" in merged[-1]: merged[-1]["Item Name"] = new_desc
            logger.info(f"[FORENSIC_MERGE_HIT] Merged continuation: '{desc[:15]}...' into '{prev_desc[:15]}...'")
        else:
            merged.append(item)
            
    # Post-merge cleanup
    for item in merged:
        if "description" in item: item["description"] = sanitize_description(item["description"])
        if "Item Name" in item: item["Item Name"] = sanitize_description(item["Item Name"])
        
    logger.info(f"[FORENSIC_MERGE_END] items_out={len(merged)}")
    return merged

def lossless_preserve(existing: Any, incoming: Any, field_name: str = "") -> Any:
    """
    STRICT preservation logic: Valid values must NEVER be replaced by empty defaults.
    If both are present, prioritizes 'existing' unless 'incoming' is significantly better.
    """
    if is_empty(existing):
        return incoming
    if is_empty(incoming):
        return existing
    
    # If both are non-empty, prefer the one with more content (for strings)
    if isinstance(existing, str) and isinstance(incoming, str):
        if len(incoming.strip()) > len(existing.strip()):
            return incoming
    
    return existing

def _clean_bill_to_ocr_extract(raw: str) -> str:
    """
    Post-processes an OCR-window-extracted bill_to string.

    Handles three common OCR artifacts:
      1. OCR prefix glued to company name  e.g. "NaneACCUTURN" → "ACCUTURN"
      2. Trailing table-column noise words that bleed into the same text run
         e.g. "ACCUTURN PVT LTD Wachillo No. Adess13nT Mode ol Transport..."
      3. Markdown pipe-table rows from Mistral OCR multi-column layout.
         Mistral OCR renders the buyer block as a two-column table:
           Left col  → Name, Address lines (buyer info)
           Right col → Vehicle No., Mode of Transport, E-Way Bill (transport)
         This stage extracts only left-column cells and discards right-column
         transport metadata, producing a clean buyer address string.

    Only applies light transformations; does NOT modify if < 5 chars or empty.
    Returns empty string if the input is a pipe-table with no usable content.
    """
    if not raw or len(raw.strip()) < 5:
        return raw
    v = raw.strip()

    # ── STAGE 1: PIPE-TABLE PARSER (Mistral OCR Markdown Table Output) ────────
    # Activated only when '|' is present.  Iterates each markdown table row,
    # collects left-column buyer cells, discards right-column transport cells.
    if '|' in v:
        # Right-column transport / routing keywords to discard
        _TRANSPORT_RE = re.compile(
            r'(?:Vehicle\s*No|Mode\s*(?:ol|of)\s*Transport|'
            r'E[\s\-]*WAY[\s\-]*BILL|LR\s*No|Dispatch|'
            r'Name\s*of\s*(?:the\s*)?[Tt]ransport|'
            r'Buyer\s*Order|E\.?\s*Way\s*Bill|'
            r'Lorry\s*Receipt|Consignment)',
            re.IGNORECASE
        )
        # Field-label prefixes to strip from cell text (Name:, Address:)
        _LABEL_RE = re.compile(
            r'^(?:Name\s*:\s*|Address\s*:\s*|Addr\s*:\s*)',
            re.IGNORECASE
        )
        # Skip cells that look like GSTIN values (state-code + alpha)
        _GSTIN_CELL_RE = re.compile(r'^\d{2}[A-Z0-9]{3,}', re.IGNORECASE)
        # Skip cells that are purely State / Code metadata rows
        _STATE_CODE_RE = re.compile(
            r'^State\s*(?:Code|:)|^State\s*:\s*State\s*Code',
            re.IGNORECASE
        )

        collected = []
        for line in v.split('\n'):
            if '|' not in line:
                stripped = line.strip()
                if stripped and not _TRANSPORT_RE.search(stripped):
                    collected.append(stripped)
                continue
            # Markdown table row — iterate cells
            cells = [c.strip() for c in line.split('|')]
            for cell in cells:
                if not cell or cell == '---' or set(cell) <= {'-', ' '}:
                    continue
                # Discard cells that ARE transport keywords
                if _TRANSPORT_RE.search(cell):
                    continue
                # Strip field-label prefix (Name:, Address:)
                cleaned = _LABEL_RE.sub('', cell).strip()
                if not cleaned:
                    continue
                # Skip GSTIN-like values (not part of postal address)
                if _GSTIN_CELL_RE.match(cleaned):
                    continue
                # Skip pure State / Code metadata
                if _STATE_CODE_RE.match(cleaned):
                    continue
                collected.append(cleaned)

        if collected:
            v = ', '.join(collected)
        else:
            # Pipe-table had no usable left-column content; return empty so
            # the caller falls back to a different source rather than storing noise.
            return ''

    # ── STAGE 2: LEGACY NOISE STRIPPING (non-table or post-table cleanup) ────
    # Strip OCR-garbled label prefixes glued directly to the company name
    v = re.sub(r'^(?:Nane?(?=[A-Z])|Name?(?=[A-Z])|Nam?e?:\s*|Nane:\s*)', '', v).strip()
    # Strip trailing transport-column labels that bleed into a text run
    _BILL_TO_NOISE_STOP = (
        r'\s+(?:'
        r'Wach(?:illo|illo)?\s*No|Machine\s*No|'
        r'Mode\s*(?:ol|of)\s*Transport|'
        r'Adess\s*\d|Address\s*\d|'
        r'GSTN(?:UD|:)|GSTIN\s*(?:UD|:)|'
        r'Buyer\s*Order|E\s*WAY(?:OLL|BILL|\s*Bill)'
        r')'
    )
    parts = re.split(_BILL_TO_NOISE_STOP, v, maxsplit=1, flags=re.IGNORECASE)
    v = parts[0].strip().rstrip(' |,-')
    return v

def sanitize_address(addr: str, field_name: str = "address") -> str:
    """
    CRITICAL ADDRESS SANITIZATION (Non-Destructive)
    Preserves locality, city, state.
    Converts multiline to single space preserving order.
    """
    if is_empty(addr): return ""
    raw = str(addr)
    
    # HIGH CONFIDENCE PROTECTION
    is_high_confidence = len(raw) > 40
    
    value = re.sub(r'\s+', ' ', raw)
    value = value.strip(",:- \n\r")
    
    if len(value) < len(raw) * 0.85:
        logger.warning(f"[ADDRESS_TRUNCATION_BLOCKED] field={field_name} raw_len={len(raw)} normalized_len={len(value)} preserved_raw=True")
        return raw.strip()
    
    if not is_high_confidence:
        if len(value) < len(raw) * 0.85:
            logger.warning(f"[ADDRESS_RECOVERY] Sanitization wiped address. Preserving raw. original='{raw[:30]}...'")
            return raw.strip()
            
    logger.info(f"[ADDRESS_SANITIZED] original_len={len(raw)} final_len={len(value)}")
    return value

def derive_branch_from_address(addr: str) -> str:
    """Infers branch from known location keywords."""
    if is_empty(addr): return ""
    upper_addr = str(addr).upper()
    BRANCH_MAP = {
        "ANNUR": "ANNUR",
        "COIMBATORE": "COIMBATORE",
        "CHENNAI": "CHENNAI",
        "HOSUR": "HOSUR",
        "POLLACHI": "POLLACHI"
    }
    for kw, branch in BRANCH_MAP.items():
        if kw in upper_addr:
            logger.info(f"[BRANCH_DERIVED] Found '{kw}' in address -> '{branch}'")
            return branch
    return ""

def get_normalized_export_record(invoice: Any, tenant_id: str = None) -> Dict[str, Any]:
    """
    STRICT CANONICAL NORMALIZER.
    Provides ONE authoritative snake_case record.
    """
    import time
    t_start_norm = time.time()
    tenant_gstin = None
    tenant_name = None
    tenant_address_keywords = set()
    if tenant_id:
        try:
            from asgiref.sync import async_to_sync, sync_to_async
            
            @sync_to_async
            def get_tenant_threadsafe():
                from core.models import Tenant
                return Tenant.objects.filter(id=str(tenant_id)).first()
                
            try:
                tenant = async_to_sync(get_tenant_threadsafe)()
            except Exception:
                from core.models import Tenant
                tenant = Tenant.objects.filter(id=str(tenant_id)).first()
                
            if tenant:
                tenant_gstin = (tenant.gstin or "").strip().upper()
                tenant_name = (tenant.name or "").strip().lower()
                for field_val in [tenant.name, tenant.branch_name, tenant.address_line1, tenant.address_line2, tenant.address_line3, tenant.city]:
                    if field_val:
                        words = [w.strip().lower() for w in re.split(r'\W+', str(field_val)) if len(w.strip()) > 3]
                        tenant_address_keywords.update(words)
        except Exception as e:
            logger.error(f"[TENANT_ISOLATION_INIT_FAIL] tenant_id={tenant_id} error={e}")

    def get_strict(keys, default=""):
        if isinstance(invoice, dict):
            # 1. Root level
            for k in keys:
                if not is_empty(invoice.get(k)): return invoice.get(k), f"root.{k}"
            # 2. Header level
            header = invoice.get('header', {})
            if isinstance(header, dict):
                for k in keys:
                    if not is_empty(header.get(k)): return header.get(k), f"header.{k}"
            # 3. Sections level
            sections = invoice.get('sections', {})
            if isinstance(sections, dict):
                sub = sections.get('supplier_details', {})
                if isinstance(sub, dict):
                    for k in keys:
                        mapped_k = "supplier_invoice_no" if k == "invoice_no" else k
                        if not is_empty(sub.get(mapped_k)): return sub.get(mapped_k), f"sections.supplier.{k}"
                        if not is_empty(sub.get(k)): return sub.get(k), f"sections.supplier.{k}"
                buyer = sections.get('buyer_details', {}) or sections.get('customer_details', {}) or sections.get('recipient_details', {})
                if isinstance(buyer, dict):
                    for k in keys:
                        if not is_empty(buyer.get(k)): return buyer.get(k), f"sections.buyer.{k}"
                        if k in ("buyer_gstin", "bill_to_gstin") and not is_empty(buyer.get("gstin")):
                            return buyer.get("gstin"), f"sections.buyer.gstin"
                consignee = sections.get('consignee_details', {}) or sections.get('ship_to_details', {})
                if isinstance(consignee, dict):
                    for k in keys:
                        if not is_empty(consignee.get(k)): return consignee.get(k), f"sections.consignee.{k}"
                        if k in ("consignee_gstin", "ship_to_gstin") and not is_empty(consignee.get("gstin")):
                            return consignee.get("gstin"), f"sections.consignee.gstin"
            # 4. Check Title Case Aliases (Idempotency)
            TITLE_ALIASES = {
                "invoice_no": "Invoice No", "invoice_date": "Date", "vendor_name": "Name",
                "gstin": "GSTIN", "branch": "Branch", "place_of_supply": "Place of Supply",
                "total_taxable_value": "Total Taxable Value", "invoice_total": "Total Invoice Value",
                "total_igst": "Total IGST", "total_cgst": "Total CGST", "total_sgst": "Total SGST/UTGST",
                "irn": "IRN", "ack_no": "Ack. No.", "ack_date": "Ack. Date", "hsn_sac": "HSN/SAC"
            }
            for k in keys:
                alias = TITLE_ALIASES.get(k)
                if alias and not is_empty(invoice.get(alias)):
                    return invoice.get(alias), f"alias.{alias}"
            
            # 5. Item Level Promotion (Last Resort Fallback)
            items = invoice.get('items') or invoice.get('sections', {}).get('items') or []
            if items and isinstance(items, list) and len(items) > 0:
                # Check if we are looking up a numeric total field
                NUMERIC_KEYS = {
                    "total_taxable_value", "taxable_value", "subtotal",
                    "total_igst", "igst",
                    "total_cgst", "cgst",
                    "total_sgst", "sgst", "utgst",
                    "total_cess", "cess", "cess_amount",
                    "total_invoice_value", "invoice_total", "total_amount", "grand_total",
                    "round_off", "rounding", "adjustment", "rounding_adjustment"
                }
                
                for k in keys:
                    is_numeric_field = (k in NUMERIC_KEYS)
                    alias = TITLE_ALIASES.get(k)
                    
                    if is_numeric_field:
                        has_val = False
                        total_sum = 0.0
                        for item in items:
                            if isinstance(item, dict):
                                val = item.get(k)
                                if is_empty(val) and alias:
                                    val = item.get(alias)
                                if not is_empty(val):
                                    has_val = True
                                    total_sum += normalize_amount(val)
                        if has_val:
                            return total_sum, f"items.sum.{k}"
                    else:
                        primary = items[0]
                        if isinstance(primary, dict):
                            if not is_empty(primary.get(k)): return primary.get(k), f"items[0].{k}"
                            if alias and not is_empty(primary.get(alias)):
                                return primary.get(alias), f"items[0].alias.{alias}"

        return default, "NONE"

    # ── [SEMANTIC OWNERSHIP FIX] ──
    # 'billing_address' means 'Customer Billing Address' (Bill To).
    # It must NEVER be used to populate the Vendor/Supplier Address (Bill From).
    raw_from, _ = get_strict(["bill_address_from", "bill_from", "vendor_address", "supplier_address", "seller_address"])
    raw_to, _ = get_strict(["bill_address_to", "bill_to", "customer_address", "billing_address_to", "billing_address"])

    # ── [PIPE_TABLE_GARBAGE_DETECT] ─────────────────────────────────────────────
    # Mistral OCR renders the buyer block as a multi-column Markdown table.
    # When Qwen returns billing_address as a pipe-table string (e.g.
    #   "| | | | Vehicle No. : | | | | | Name : ACCUTURN MACHINERS PVT LTD")
    # the value is noise as a postal address but may contain a buyer name.
    # Strategy:
    #   1. Extract buyer name candidate from the 'Name :' label.
    #   2. Reset raw_to to empty so the OCR window slicer can recover
    #      the full multi-line address block from the raw OCR text.
    # This variable is consumed by the buyer_name fallback below.
    _qwen_buyer_name_candidate = ""
    if not is_empty(raw_to) and '|' in str(raw_to):
        _name_m = re.search(r'Name\s*:\s*([A-Z][^|\n]{2,80})', str(raw_to), re.IGNORECASE)
        if _name_m:
            _qwen_buyer_name_candidate = _name_m.group(1).strip().rstrip(', |')
            logger.info(f"[PIPE_TABLE_BUYER_NAME_EXTRACTED] candidate='{_qwen_buyer_name_candidate}'")
        logger.info(
            f"[PIPE_TABLE_GARBAGE_RESET] billing_address is pipe-table noise; "
            f"resetting raw_to so window slicer recovers full address. "
            f"buyer_name_candidate='{_qwen_buyer_name_candidate}'"
        )
        raw_to = ""  # reset: triggers OCR window slicer below

    # ── [PHASE 11.9] WINDOW_SLICER FALLBACK (HARDENED) ──
    if is_empty(raw_from) or is_empty(raw_to):
        ocr_text = invoice.get("_pdf_ocr_text") if isinstance(invoice, dict) else ""
        if ocr_text:
            if is_empty(raw_from):
                logger.info("[ADDRESS_ROLE_CLASSIFIED] target='bill_from' status='missing' — skipping destructive fallback to prevent customer contamination")

            if is_empty(raw_to):
                logger.info("[BILL_TO_WINDOW_ATTEMPT]")
                # Buyer (Bill to) / Details of Receiver (Billed to) -> Stop Tokens
                # Expanded start patterns and stop tokens to handle multiline/collapsed OCR better and handle OCR misreads
                start_pattern = r"(?:Buyer\s*\(Bill\s*to\)|Details\s*of\s*Receiver\s*\(Billed\s*to\)|Details\s*of\s*Receiver|Billed\s*to|Dtails\s*oi\s*Rocolvor\s*Dlcd\s*to|Dlcd\s*to|Bill\s*to)"
                stop_tokens = r"(?:Place\s*of\s*Supply|Puce\s*ol\s*Supply|Dated|Delivery\s*Note|Invoice\s*No|Voucher\s*No|Total|Description|Sl\s*No|E-Way|E\s*WAY)"
                match = re.search(fr"{start_pattern}(.*?){stop_tokens}", ocr_text, re.DOTALL | re.IGNORECASE)
                if match: 
                    raw_to = _clean_bill_to_ocr_extract(match.group(1).strip())
                    logger.info(f"[BILL_TO_WINDOW_HIT] raw_len={len(match.group(1).strip())} cleaned_len={len(raw_to)} value={repr(raw_to[:80])}")
                else:
                    # Try a more desperate match if the above failed
                    match = re.search(fr"{start_pattern}(.{{1,500}}?)", ocr_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        raw_to = _clean_bill_to_ocr_extract(match.group(1).strip())
                        logger.info(f"[BILL_TO_WINDOW_DESPERATE_HIT] raw_len={len(match.group(1).strip())} cleaned_len={len(raw_to)} value={repr(raw_to[:80])}")

    # ── [TENANT-BRANCH ISOLATION GUARD] ──
    # Wipe vendor address if it leaks customer (tenant) data
    if raw_from and tenant_address_keywords:
        bill_from_words = [w.strip().lower() for w in re.split(r'\W+', str(raw_from)) if len(w.strip()) > 3]
        matches = [w for w in bill_from_words if w in tenant_address_keywords]
        if len(matches) >= 4 or (len(bill_from_words) > 0 and len(matches) / len(bill_from_words) > 0.6):
            logger.warning(f"[TENANT_ISOLATION_WARN] Extracted bill_from address '{raw_from}' matches tenant address keywords {matches}. Wiping bill_from to prevent customer address contamination.")
            raw_from = ""

    if tenant_gstin and raw_from and tenant_gstin in raw_from.upper():
        logger.warning(f"[TENANT_ISOLATION_WARN] Extracted bill_from contains tenant GSTIN '{tenant_gstin}'. Wiping bill_from to prevent contamination.")
        raw_from = ""

    # ── [ADDRESS_DUPLICATION_GUARD] ──
    # If the AI accidentally cloned the buyer address into the vendor address, wipe the vendor address
    # so we don't contaminate the 'bill_from' field with a customer address.
    if raw_from and raw_to:
        clean_from = sanitize_address(raw_from)
        clean_to = sanitize_address(raw_to)
        if clean_from and clean_from == clean_to:
            logger.warning(f"[ADDRESS_DUPLICATION_BLOCKED] bill_from and bill_to are identical. Clearing bill_from to prevent customer address contamination.")
            raw_from = ""

    bill_from = sanitize_address(raw_from, field_name="bill_from")
    bill_to = sanitize_address(raw_to, field_name="bill_to")
    
    branch = get_strict(["branch"])[0] or derive_branch_from_address(bill_to) or derive_branch_from_address(bill_from)

    vendor_name_val = fix_encoding_corruption(str(get_strict(["vendor_name", "supplier_name", "name"])[0]))
    vendor_name_clean = vendor_name_val.strip().lower()
    if tenant_name and (vendor_name_clean == tenant_name or vendor_name_clean == "main branch"):
        logger.warning(f"[TENANT_ISOLATION_WARN] Extracted vendor_name '{vendor_name_val}' matches tenant name '{tenant_name}'. Wiping to prevent contamination.")
        vendor_name_val = ""

    gstin_val = normalize_gstin_safe(get_strict(["gstin", "vendor_gstin", "supplier_gstin"])[0])
    if tenant_gstin and gstin_val and gstin_val.upper() == tenant_gstin:
        logger.warning(f"[TENANT_ISOLATION_WARN] Extracted GSTIN '{gstin_val}' matches tenant GSTIN '{tenant_gstin}'. Wiping vendor GSTIN to prevent contamination.")
        gstin_val = ""

    # Run GSTIN Ownership Classifier
    from ocr_pipeline.gstin_classifier import GSTINOwnershipClassifier
    raw_text = ""
    if isinstance(invoice, dict):
        raw_text = invoice.get("_pdf_ocr_text") or invoice.get("_raw_text") or ""
    
    extracted_data_dict = {}
    if isinstance(invoice, dict):
        extracted_data_dict = {
            "gstin": gstin_val,
            "vendor_gstin": get_strict(["vendor_gstin", "supplier_gstin"])[0],
            "buyer_gstin": get_strict(["buyer_gstin", "bill_to_gstin"])[0],
            "consignee_gstin": get_strict(["consignee_gstin", "ship_to_gstin"])[0],
            "vendor_name": vendor_name_val
        }
    
    classification = GSTINOwnershipClassifier.classify_gstins(raw_text, extracted_data_dict, tenant_id)
    
    # ── SCHEMA INTEGRITY GATE: CROSS-ROLE POLLUTION DETECTION ──
    v_gst = (classification.get("canonical_vendor_gstin") or gstin_val or "").strip().upper()
    
    b_gst = (classification.get("canonical_buyer_gstin") or "").strip().upper()
    c_gst = (classification.get("canonical_consignee_gstin") or "").strip().upper()
    
    raw_buyer_val, _ = get_strict(["buyer_gstin", "bill_to_gstin"])
    raw_consignee_val, _ = get_strict(["consignee_gstin", "ship_to_gstin"])
    
    from vendors.vendor_validation_logic import canonicalize_gstin_ocr
    b_gst_raw = canonicalize_gstin_ocr(raw_buyer_val).strip().upper()
    c_gst_raw = canonicalize_gstin_ocr(raw_consignee_val).strip().upper()
    
    if v_gst and len(v_gst) == 15:
        if (b_gst and len(b_gst) == 15 and v_gst == b_gst) or (c_gst and len(c_gst) == 15 and v_gst == c_gst):
            msg = f"[SCHEMA_INTEGRITY_VIOLATION] Cross-role GSTIN pollution detected! vendor_gstin={v_gst} matches buyer_gstin={b_gst} or consignee_gstin={c_gst}"
            logger.error(msg)
            raise ValueError(msg)
        if (b_gst_raw and len(b_gst_raw) == 15 and v_gst == b_gst_raw) or (c_gst_raw and len(c_gst_raw) == 15 and v_gst == c_gst_raw):
            msg = f"[SCHEMA_INTEGRITY_VIOLATION] Cross-role GSTIN pollution detected! vendor_gstin={v_gst} matches raw buyer_gstin={b_gst_raw} or raw consignee_gstin={c_gst_raw}"
            logger.error(msg)
            raise ValueError(msg)
            
    if classification.get("vendor_gstin"):
        gstin_val = classification["vendor_gstin"]

    buyer_name_val, _ = get_strict(["buyer_name", "customer_name", "bill_to_name"])
    buyer_name_val = fix_encoding_corruption(str(buyer_name_val)) if buyer_name_val else ""
    if not buyer_name_val:
        # Priority 1: Use candidate saved from Qwen's pipe-table billing_address
        # (extracted before raw_to was reset for the window slicer).
        if _qwen_buyer_name_candidate:
            buyer_name_val = fix_encoding_corruption(_qwen_buyer_name_candidate)
            logger.info(f"[BUYER_NAME_PIPE_TABLE] value='{buyer_name_val}'")

        # Priority 2: Extract 'Name :' label from the cleaned bill_to string.
        # Covers cases where the window slicer recovered a pipe-table row
        # that still contains an inline 'Name : VALUE' label.
        if not buyer_name_val and bill_to:
            _name_m = re.search(r'Name\s*:\s*([A-Z][^,;\n|]{2,80})', str(bill_to), re.IGNORECASE)
            if _name_m:
                buyer_name_val = fix_encoding_corruption(_name_m.group(1).strip())
                logger.info(f"[BUYER_NAME_LABEL] value='{buyer_name_val}'")

        # Priority 3: Original comma/semicolon/newline split (guarded against pipe noise).
        if not buyer_name_val and bill_to:
            parts = re.split(r'[,;\n]', str(bill_to))
            if parts:
                cand = parts[0].strip()
                if cand and not re.match(r'^\d', cand) and '|' not in cand:
                    buyer_name_val = cand

    from vendors.vendor_validation_logic import canonicalize_gstin_ocr
    record = {
        "invoice_no": fix_encoding_corruption(str(get_strict(["invoice_no", "invoice_number", "bill_no", "supplier_invoice_no"])[0])),
        "invoice_date": normalize_date(get_strict(["invoice_date", "date", "bill_date", "supplier_invoice_date"])[0]),
        "vendor_name": vendor_name_val,
        "buyer_name": buyer_name_val,
        "gstin": gstin_val,
        "raw_gstin": classification.get("raw_vendor_gstin") or gstin_val,
        "canonical_gstin": canonicalize_gstin_ocr(gstin_val),
        "branch": fix_encoding_corruption(str(branch)),
        "bill_from": fix_encoding_corruption(str(bill_from)),
        "bill_to": fix_encoding_corruption(str(bill_to)),
        "place_of_supply": normalize_state(get_strict(["place_of_supply", "vendor_state", "state"])[0]),
        "total_taxable_value": normalize_amount(get_strict(["total_taxable_value", "taxable_value", "subtotal"])[0]),
        "total_igst": normalize_amount(get_strict(["total_igst", "igst"])[0]),
        "total_cgst": normalize_amount(get_strict(["total_cgst", "cgst"])[0]),
        "total_sgst": normalize_amount(get_strict(["total_sgst", "sgst", "utgst"])[0]),
        "total_cess": normalize_amount(get_strict(["total_cess", "cess", "cess_amount"])[0]),
        "round_off": normalize_amount(get_strict(["round_off", "rounding", "adjustment", "rounding_adjustment"])[0]),
        "total_invoice_value": normalize_amount(get_strict(["total_invoice_value", "invoice_total", "total_amount", "grand_total"])[0]),
        "irn": str(get_strict(["irn"])[0]).strip(),
        "ack_no": str(get_strict(["ack_no"])[0]).strip(),
        "ack_date": normalize_date(get_strict(["ack_date"])[0]),
        "hsn_sac": str(get_strict(["hsn_sac", "hsn", "sac"])[0]).strip(),
        
        # Explicit GSTIN Role Fields
        "vendor_gstin": classification.get("vendor_gstin") or "",
        "buyer_gstin": classification.get("buyer_gstin") or "",
        "consignee_gstin": classification.get("consignee_gstin") or "",
        "ship_to_gstin": classification.get("ship_to_gstin") or "",
        "bill_to_gstin": classification.get("bill_to_gstin") or "",
        "raw_vendor_gstin": classification.get("raw_vendor_gstin") or "",
        "raw_buyer_gstin": classification.get("raw_buyer_gstin") or "",
        "raw_consignee_gstin": classification.get("raw_consignee_gstin") or "",
        "raw_bill_to_gstin": classification.get("raw_bill_to_gstin") or "",
        "raw_ship_to_gstin": classification.get("raw_ship_to_gstin") or "",
        "canonical_vendor_gstin": classification.get("canonical_vendor_gstin") or "",
        "canonical_buyer_gstin": classification.get("canonical_buyer_gstin") or "",
        "canonical_consignee_gstin": classification.get("canonical_consignee_gstin") or "",
        "canonical_bill_to_gstin": classification.get("canonical_bill_to_gstin") or "",
        "canonical_ship_to_gstin": classification.get("canonical_ship_to_gstin") or "",
    }

    # ── [HEADER_GST_RATE_ENRICHMENT] ────────────────────────────────────────────
    # Evidence: items correctly carry cgst_rate=9.0 but no top-level header
    # cgst_rate/sgst_rate key exists in extracted_data, causing forensic reports
    # to score header GST rate as 0.
    # Fix: derive header rates from (total_cgst / total_taxable_value) * 100,
    # snapped to the nearest standard GST rate.
    # This is strictly additive — it never overwrites any Qwen-extracted value.
    _h_taxable = record.get("total_taxable_value", 0.0) or 0.0
    _h_cgst    = record.get("total_cgst", 0.0) or 0.0
    _h_sgst    = record.get("total_sgst", 0.0) or 0.0
    _h_igst    = record.get("total_igst", 0.0) or 0.0
    if _h_taxable > 0:
        if _h_cgst > 0 and _h_igst == 0:
            record["header_cgst_rate"] = snap_to_standard_gst_rate((_h_cgst / _h_taxable) * 100)
            record["header_sgst_rate"] = snap_to_standard_gst_rate((_h_sgst / _h_taxable) * 100)
            record["cgst_rate"] = record["header_cgst_rate"]
            record["sgst_rate"] = record["header_sgst_rate"]
            logger.info(
                f"[HEADER_GST_RATE] cgst_rate={record['header_cgst_rate']}% "
                f"sgst_rate={record['header_sgst_rate']}% "
                f"(from total_cgst={_h_cgst}/total_taxable={_h_taxable})"
            )
        elif _h_igst > 0:
            record["header_igst_rate"] = snap_to_standard_gst_rate((_h_igst / _h_taxable) * 100)
            record["igst_rate"] = record["header_igst_rate"]
            logger.info(
                f"[HEADER_GST_RATE] igst_rate={record['header_igst_rate']}% "
                f"(from total_igst={_h_igst}/total_taxable={_h_taxable})"
            )


    # ── [TOTALS & POS OCR REGION EXTRACTION FALLBACK] (Requirement D) ──
    if isinstance(invoice, dict):
        ocr_text = invoice.get("_pdf_ocr_text") or invoice.get("_raw_text") or ""
        if ocr_text:
            # 1. Place of Supply / State
            if is_empty(record.get("place_of_supply")):
                # Check different variations
                pos_match = re.search(r'(?i)Place\s*of\s*(?:Supply|Su|S)?\s*[:/-]?\s*([0-9a-zA-Z\s-]+)', ocr_text)
                if pos_match:
                    pos_val = pos_match.group(1).strip()
                    record["place_of_supply"] = normalize_state(pos_val)
                    logger.info(f"[REGION_FALLBACK_EXTRACTED] Place of Supply='{record['place_of_supply']}' (source='{pos_val}')")
                
                # State Name fallback
                if is_empty(record.get("place_of_supply")):
                    # Search for known states in the billing address first
                    bill_to_str = str(record.get("bill_to", "")).upper()
                    found_state = None
                    states = [
                        "Tamil Nadu", "Karnataka", "Kerala", "Andhra Pradesh", "Telangana",
                        "Maharashtra", "Delhi", "Gujarat", "Haryana", "Punjab", "Rajasthan",
                        "Uttar Pradesh", "West Bengal"
                    ]
                    for st in states:
                        if st.upper() in bill_to_str:
                            found_state = st
                            break
                    if found_state:
                        record["place_of_supply"] = found_state
                        logger.info(f"[STATE_FALLBACK_BILL_TO] Place of Supply derived from billing address: '{found_state}'")
                    else:
                        # Search for explicit State: Tamil Nadu or State Code: Tamil Nadu or similar in ocr_text
                        state_match = re.search(r'(?i)(?:State|State\s*Name|State\s*Code|POS)\s*[:/-]?\s*([0-9a-zA-Z\s-]+)', ocr_text)
                        if state_match:
                            pos_val = state_match.group(1).strip()
                            record["place_of_supply"] = normalize_state(pos_val)
                            logger.info(f"[STATE_FALLBACK_STATE_MATCH] Place of Supply='{record['place_of_supply']}' (source='{pos_val}')")
                            
            # 2. Total Taxable Value
            if normalize_amount(record.get("total_taxable_value")) == 0.0:
                taxable_match = re.search(r'(?i)(?:Total\s*Taxable\s*Value|Taxable\s*Amt|Taxable\s*Value|Subtotal|Sub\s*Total)\s*[:/-]?\s*([0-9,.]+)', ocr_text)
                if taxable_match:
                    record["total_taxable_value"] = normalize_amount(taxable_match.group(1))
                    logger.info(f"[REGION_FALLBACK_EXTRACTED] Total Taxable Value={record['total_taxable_value']}")
            
            # 3. Total CGST
            if normalize_amount(record.get("total_cgst")) == 0.0:
                cgst_match = re.search(r'(?i)(?:CGST\s*Total|Total\s*CGST|CGST)\s*[:/-]?\s*([0-9,.]+)', ocr_text)
                if cgst_match:
                    record["total_cgst"] = normalize_amount(cgst_match.group(1))
                    logger.info(f"[REGION_FALLBACK_EXTRACTED] Total CGST={record['total_cgst']}")
            
            # 4. Total SGST
            if normalize_amount(record.get("total_sgst")) == 0.0:
                sgst_match = re.search(r'(?i)(?:SGST\s*Total|Total\s*SGST|SGST|UTGST)\s*[:/-]?\s*([0-9,.]+)', ocr_text)
                if sgst_match:
                    record["total_sgst"] = normalize_amount(sgst_match.group(1))
                    logger.info(f"[REGION_FALLBACK_EXTRACTED] Total SGST={record['total_sgst']}")
            
            # 5. Total IGST
            if normalize_amount(record.get("total_igst")) == 0.0:
                igst_match = re.search(r'(?i)(?:IGST\s*Total|Total\s*IGST|IGST)\s*[:/-]?\s*([0-9,.]+)', ocr_text)
                if igst_match:
                    record["total_igst"] = normalize_amount(igst_match.group(1))
                    logger.info(f"[REGION_FALLBACK_EXTRACTED] Total IGST={record['total_igst']}")
            
            # 6. Total Invoice Value
            if normalize_amount(record.get("total_invoice_value")) == 0.0:
                total_match = re.search(r'(?i)(?:Total\s*Invoice\s*Value|Total\s*Amount|Grand\s*Total|Total|Amount\s*Chargeable)\s*[:/-]?\s*([0-9,.]+)', ocr_text)
                if total_match:
                    record["total_invoice_value"] = normalize_amount(total_match.group(1))
                    logger.info(f"[REGION_FALLBACK_EXTRACTED] Total Invoice Value={record['total_invoice_value']}")

    # [PHASE 13 FIX] Fallback to GSTIN state code if still empty (OUTSIDE of ocr_text block)
    if is_empty(record.get("place_of_supply")) and record.get("gstin"):
        state_code = record["gstin"][:2]
        GST_STATE_CODES = {
            "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
            "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
            "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
            "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
            "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
            "16": "Tripura", "17": "Meghalaya", "18": "Assam",
            "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
            "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
            "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra",
            "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
            "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
            "34": "Puducherry", "35": "Andaman and Nicobar Islands",
            "36": "Telangana", "37": "Andhra Pradesh (New)"
        }
        if state_code in GST_STATE_CODES:
            record["place_of_supply"] = GST_STATE_CODES[state_code]
            logger.info(f"[STATE_FALLBACK_GSTIN] Place of Supply='{record['place_of_supply']}' derived from GSTIN '{record['gstin']}'")


    # Preserve underscores
    if isinstance(invoice, dict):
        for k, v in invoice.items():
            if k.startswith("_"): record[k] = v
            
    # [PHASE 11.9] FORENSIC EXPORT LOG
    logger.info(f"[HSN_EXPORT_READY] inv={record.get('invoice_no')} hsn_sac='{record.get('hsn_sac')}'")
    logger.info(f"[EXPORT_FINAL_ROW] inv={record.get('invoice_no')} name={record.get('vendor_name')} total={record.get('total_invoice_value')}")
    
    norm_duration_ms = int((time.time() - t_start_norm) * 1000) if 't_start_norm' in locals() else 0
    from ocr_pipeline.pipeline_telemetry import PipelineStageTelemetry
    PipelineStageTelemetry.record_stage(
        "Normalizer",
        invoice if isinstance(invoice, dict) else {},
        record,
        norm_duration_ms
    )

    return record

def resolve_uom(raw_uom: str, tenant_id: str = None) -> str:
    """
    Resolves a raw UOM string to a standard symbol from the database (InventoryUnit model).
    If the database is empty for the tenant, it seeds standard units dynamically
    so that we don't have hardcoded mapping lists in our resolver.
    """
    if not raw_uom:
        return "nos"
        
    uom_clean = str(raw_uom).strip().lower()
    
    # Try importing model locally to avoid circular dependencies
    try:
        from inventory.models import InventoryUnit
        
        # Check if units exist for this tenant, if not, seed standard ones
        if tenant_id and not InventoryUnit.objects.filter(tenant_id=tenant_id).exists():
            standard_units = [
                {"name": "Numbers", "symbol": "nos"},
                {"name": "Kilograms", "symbol": "kg"},
                {"name": "Grams", "symbol": "gm"},
                {"name": "Meters", "symbol": "m"},
                {"name": "Centimeters", "symbol": "cm"},
                {"name": "Liters", "symbol": "l"},
                {"name": "Milliliters", "symbol": "ml"},
                {"name": "Box", "symbol": "box"},
                {"name": "Pouch", "symbol": "pch"},
                {"name": "Set", "symbol": "set"},
                {"name": "Pieces", "symbol": "pcs"},
                {"name": "Dozen", "symbol": "doz"},
                {"name": "Bag", "symbol": "bag"},
                {"name": "Bundle", "symbol": "bdl"},
                {"name": "Can", "symbol": "can"},
                {"name": "Bottle", "symbol": "btl"},
            ]
            for u in standard_units:
                InventoryUnit.objects.create(tenant_id=tenant_id, name=u["name"], symbol=u["symbol"])
                
        # Query active units
        q = InventoryUnit.objects.filter(is_active=True)
        if tenant_id:
            q = q.filter(tenant_id=tenant_id)
            
        units = list(q)
        # Try matching by symbol or name
        for unit in units:
            if unit.symbol.lower() == uom_clean or unit.name.lower() == uom_clean:
                return unit.symbol
    except Exception as e:
        logger.warning(f"[UOM_RESOLVER_DB_ERROR] {e}")
        
    # Fallback mappings if DB query fails or has no match
    FALLBACK_MAP = {
        "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
        "gm": "gm", "grams": "gm", "gram": "gm",
        "m": "m", "meter": "m", "meters": "m",
        "cm": "cm", "centimeters": "cm", "centimeter": "cm",
        "l": "l", "liter": "l", "liters": "l",
        "ml": "ml", "milliliter": "ml", "milliliters": "ml",
        "box": "box", "boxes": "box",
        "pch": "pch", "pouch": "pch", "pouches": "pch",
        "set": "set", "sets": "set",
        "pcs": "pcs", "piece": "pcs", "pieces": "pcs",
        "doz": "doz", "dozen": "doz", "dozens": "doz",
        "bag": "bag", "bags": "bag",
        "bdl": "bdl", "bundle": "bdl", "bundles": "bdl",
        "can": "can", "cans": "can",
        "btl": "btl", "bottle": "btl", "bottles": "btl",
        "nos": "nos", "number": "nos", "numbers": "nos", "unit": "nos", "units": "nos",
    }
    return FALLBACK_MAP.get(uom_clean, uom_clean)

def snap_to_standard_gst_rate(rate: float) -> float:
    standard_rates = [0.0, 0.25, 1.5, 2.5, 3.0, 5.0, 6.0, 9.0, 12.0, 14.0, 18.0, 28.0]
    for r in standard_rates:
        if abs(rate - r) < 0.2:
            return r
    return round(rate, 2)

def get_normalized_items(invoice: Any, tenant_id: str = None) -> List[Dict[str, Any]]:
    """
    CANONICAL ITEM NORMALIZER.
    """
    items_source = []
    if isinstance(invoice, dict):
        items_source = invoice.get('sections', {}).get('items') or invoice.get('items') or invoice.get('line_items') or []
    
    normalized_items = []
    for item in items_source:
        if not isinstance(item, dict): continue
        
        desc = (item.get("description") or item.get("desc") or item.get("particulars") or item.get("item_name") or item.get("Item Name") or "")
        if not desc: continue
        
        taxable = normalize_amount(item.get("taxable_value") or item.get("amount") or item.get("Taxable Value"))
        # Track whether quantity was explicitly provided or is a fallback default.
        # If Qwen returns quantity=null (e.g. because only rate is visible on the row),
        # the `or 1.0` below kicks in. We record this so we can derive qty later.
        _raw_qty_value = item.get("qty") or item.get("quantity") or item.get("Qty")
        _qty_was_explicit = _raw_qty_value is not None and normalize_amount(_raw_qty_value) > 0
        qty = normalize_amount(_raw_qty_value or 1.0)
        
        ig_amt = normalize_amount(item.get("igst") or item.get("igst_amount") or item.get("IGST"))
        cg_amt = normalize_amount(item.get("cgst") or item.get("cgst_amount") or item.get("CGST"))
        sg_amt = normalize_amount(item.get("sgst") or item.get("sgst_amount") or item.get("SGST/UTGST"))
        ce_amt = normalize_amount(item.get("cess") or item.get("cess_amount") or item.get("CESS") or item.get("cess_val"))

        def extract_rate_from_keys(prefix):
            pattern = re.compile(rf'(?i){prefix}\s*@\s*([\d.]+)\s*%')
            for k in item.keys():
                match = pattern.search(k)
                if match:
                    try:
                        return float(match.group(1))
                    except:
                        pass
            return 0.0

        def parse_tax_rate(val):
            if val is None:
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            raw = str(val).strip()
            raw = raw.replace("%", "").strip()
            try:
                cleaned = re.sub(r'[^\d.-]', '', raw)
                return float(cleaned) if cleaned else 0.0
            except (ValueError, TypeError):
                return 0.0

        def get_tax_rate(key_prefix, tax_amount):
            rate_from_key = extract_rate_from_keys(key_prefix)
            if rate_from_key > 0.0:
                return rate_from_key

            for suffix in ["_rate", "_pct", "_percent", "_%", "_tax_rate", "_percentage"]:
                val = (
                    item.get(f"{key_prefix}{suffix}") or 
                    item.get(f"{key_prefix.upper()}{suffix.upper()}") or 
                    item.get(f"{key_prefix.upper()}{suffix}") or
                    item.get(f"{key_prefix}{suffix.upper()}")
                )
                if val is not None:
                    parsed = parse_tax_rate(val)
                    if parsed > 0.0:
                        return parsed
            if taxable > 0 and tax_amount > 0:
                return (tax_amount / taxable) * 100
            return 0.0

        ig_rate = snap_to_standard_gst_rate(get_tax_rate("igst", ig_amt))
        cg_rate = snap_to_standard_gst_rate(get_tax_rate("cgst", cg_amt))
        sg_rate = snap_to_standard_gst_rate(get_tax_rate("sgst", sg_amt))
        ce_rate = round(get_tax_rate("cess", ce_amt), 2)

        # Check for direct GST rate extraction keys
        gst_direct_rate = 0.0
        for suffix in ["gst_rate", "gst_pct", "gst_percent", "gst_percentage", "gst_%", "tax_rate", "tax_pct", "tax_percent", "tax_percentage", "tax_%", "GST_RATE", "GST_PCT", "GST_PERCENT", "GST_PERCENTAGE"]:
            val = item.get(suffix)
            if val is not None:
                parsed = parse_tax_rate(val)
                if parsed > 0.0:
                    gst_direct_rate = snap_to_standard_gst_rate(parsed)
                    break

        # Precise GST snap logic for computed_gst_rate
        computed_gst = 0.0
        if ig_rate > 0:
            computed_gst = ig_rate
        elif cg_rate > 0 or sg_rate > 0:
            computed_gst = cg_rate + sg_rate
        elif gst_direct_rate > 0:
            computed_gst = gst_direct_rate
        else:
            # fallback rate estimation from amount
            if taxable > 0:
                if ig_amt > 0:
                    computed_gst = snap_to_standard_gst_rate((ig_amt / taxable) * 100)
                elif cg_amt > 0 or sg_amt > 0:
                    computed_gst = snap_to_standard_gst_rate(((cg_amt + sg_amt) / taxable) * 100)

        # Base rate (Unit Price) derived from taxable_value / qty if unspecified or 0
        raw_rate = normalize_amount(item.get("rate") or item.get("unit_price") or item.get("Item Rate"))
        if raw_rate <= 0 and qty > 0:
            derived_rate = round(taxable / qty, 2)
        else:
            derived_rate = raw_rate

        # [QTY_DERIVATION] If qty was not explicitly provided by the AI (defaulted to 1.0)
        # but we have both rate and taxable_value, derive qty = taxable / rate.
        # This handles the case where Qwen correctly sets quantity=null and rate=12.00,
        # so normalize.py can still reconstruct the actual quantity.
        if not _qty_was_explicit and derived_rate > 0 and taxable > 0:
            derived_qty = round(taxable / derived_rate, 3)
            if derived_qty != 1.0:  # avoid no-op overwrite
                logger.info(
                    f"[QTY_DERIVED_FROM_RATE] desc='{desc}' taxable={taxable} rate={derived_rate} "
                    f"derived_qty={derived_qty} (qty was null/missing from AI output)"
                )
                qty = derived_qty

        normalized_item = {
            "description": desc,
            "hsn_sac": str(item.get("hsn_sac") or item.get("hsn_code") or item.get("HSN/SAC") or item.get("hsn") or item.get("sac") or ""),
            "qty": qty,
            "uom": resolve_uom(item.get("uom") or item.get("unit") or item.get("UOM") or "", tenant_id=tenant_id),
            "rate": derived_rate,
            "taxable_value": taxable,
            "igst": ig_amt,
            "cgst": cg_amt,
            "sgst": sg_amt,
            "total_amount": normalize_amount(item.get("total_amount") or item.get("amount") or item.get("Invoice Value")),
            "igst_rate": ig_rate,
            "cgst_rate": cg_rate,
            "sgst_rate": sg_rate,
            "cess_rate": ce_rate,
            "computed_gst_rate": computed_gst,
        }
        # Copy other custom/original keys to prevent loss of fields (like item_code, etc.)
        for k, v in item.items():
            if k not in normalized_item:
                normalized_item[k] = v

        normalized_items.append(normalized_item)
        
    return merge_item_continuations(normalized_items)

def get_canonical_export_record(invoice: Any, tenant_id: str = None) -> Dict[str, Any]:
    """
    PHASE 4: CANONICAL SCHEMA STABILIZATION
    Provides ONE authoritative normalized export record using CanonicalInvoiceSchema.
    DOWNSTREAM SYSTEMS MUST ONLY USE THIS.
    """
    import copy
    
    # ── [DEFENSIVE UNWRAPPING] ──
    if isinstance(invoice, str):
        try:
            invoice = json.loads(invoice)
        except: pass
    
    if isinstance(invoice, dict):
        invoice = copy.deepcopy(invoice) # Prevent DTO leakage by copying at the boundary
        if not tenant_id:
            tenant_id = invoice.get('tenant_id') or invoice.get('upload_session_id')
        unwrapped = invoice.get('reply_json') or invoice.get('data') or invoice.get('reply')
        if unwrapped:
            if isinstance(unwrapped, str):
                try:
                    parsed = json.loads(unwrapped)
                    if isinstance(parsed, dict):
                        for k, v in invoice.items():
                            if k not in ['reply_json', 'data', 'reply'] and k not in parsed:
                                parsed[k] = v
                        invoice = parsed
                except: pass
            elif isinstance(unwrapped, dict):
                for k, v in invoice.items():
                    if k not in ['reply_json', 'data', 'reply'] and k not in unwrapped:
                        unwrapped[k] = v
                invoice = unwrapped

    # ── [FORENSIC NORMALIZATION LOGS] ──
    import time
    t_start_trans = time.time()
    import hashlib
    input_hash = hashlib.md5(json.dumps(invoice, sort_keys=True, default=str).encode()).hexdigest()
    logger.info(f"[NORMALIZATION_START] record_id={invoice.get('record_id')} invoice_no={invoice.get('invoice_no')}")
    logger.info(f"[NORMALIZATION_INPUT_HASH] {input_hash}")

    # ── [PHASE 11.9] FORENSIC DTO AUDIT ──
    logger.info(f"[DTO_PRE_VALIDATION] record_id={invoice.get('record_id')} keys={list(invoice.keys())}")

    raw_header = get_normalized_export_record(invoice, tenant_id=tenant_id)
    raw_items = get_normalized_items(invoice, tenant_id=tenant_id)

    # ── [PHASE 3: DETERMINISTIC RECOVERY & PROPAGATION] ──
    import os
    hsn_prop_enabled = os.getenv("NORMALIZER_HSN_PROPAGATION", "true").lower() == "true"
    buyer_rec_enabled = os.getenv("NORMALIZER_BUYER_RECOVERY", "true").lower() == "true"
    
    # 1. Buyer GSTIN Recovery
    if buyer_rec_enabled:
        current_buyer_gstin = raw_header.get("buyer_gstin") or ""
        if not (current_buyer_gstin and len(current_buyer_gstin) == 15 and validate_gstin_checksum(current_buyer_gstin)):
            recovered = recover_buyer_gstin(invoice, current_buyer_gstin)
            if recovered:
                raw_header["buyer_gstin"] = recovered
                raw_header["canonical_buyer_gstin"] = recovered
                raw_header["bill_to_gstin"] = recovered
                raw_header["canonical_bill_to_gstin"] = recovered
                logger.info(f"[AUDIT_DETERMINISTIC_CORRECTION] {json.dumps({
                    'prefix': '[AUDIT_DETERMINISTIC_CORRECTION]',
                    'timestamp': datetime.now().isoformat() + 'Z',
                    'invoice_id': str(invoice.get('record_id') or invoice.get('id') or ''),
                    'page_number': int(invoice.get('page_number') or invoice.get('page_index') or 1),
                    'line_number': 0,
                    'feature': 'BUYER_RECOVERY',
                    'before_value': current_buyer_gstin,
                    'after_value': recovered,
                    'reason': 'Recovered from Buyer block with checksum verification',
                    'feature_flag': 'NORMALIZER_BUYER_RECOVERY'
                })}")

    # 2. HSN Propagation
    if hsn_prop_enabled and raw_items:
        valid_hsns = []
        for item in raw_items:
            h = str(item.get("hsn_sac") or item.get("hsn_code") or "").strip()
            if h and h not in ('"', "''", "tt", "11", "None", "null") and len(h) >= 2:
                valid_hsns.append(h)
        unique_valid_hsns = list(set(valid_hsns))
        
        prev_hsn = None
        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                continue
            hsn = str(item.get("hsn_sac") or item.get("hsn_code") or "").strip()
            is_empty_hsn = not hsn or hsn in ("None", "null")
            is_ditto = hsn in ('"', "''", "tt", "11")
            
            desc = str(item.get("description") or "").lower()
            is_boundary = any(keyword in desc for keyword in ["total", "subtotal", "tax taxable", "round off", "cgst", "sgst", "igst", "net amount"])
            
            if is_boundary or not desc.strip():
                prev_hsn = None
                continue
                
            if not is_empty_hsn and not is_ditto:
                if len(hsn) >= 2:
                    prev_hsn = hsn
                else:
                    prev_hsn = None
                continue
                
            allowed = False
            reason = ""
            if is_ditto:
                allowed = True
                reason = f"Explicit ditto OCR match ('{hsn}')"
            elif is_empty_hsn:
                if len(unique_valid_hsns) == 1:
                    allowed = True
                    reason = "Single HSN invoice implicit propagation"
                else:
                    reason = "Skipped: multiple HSN regions exist without explicit ditto"
                    
            if allowed and prev_hsn:
                orig_hsn = hsn
                item["hsn_sac"] = prev_hsn
                item["hsn_code"] = prev_hsn
                if "raw_hsn" in item:
                    item["raw_hsn"] = prev_hsn
                if "canonical_hsn" in item:
                    item["canonical_hsn"] = prev_hsn
                    
                logger.info(f"[AUDIT_DETERMINISTIC_CORRECTION] {json.dumps({
                    'prefix': '[AUDIT_DETERMINISTIC_CORRECTION]',
                    'timestamp': datetime.now().isoformat() + 'Z',
                    'invoice_id': str(invoice.get('record_id') or invoice.get('id') or ''),
                    'page_number': int(invoice.get('page_number') or invoice.get('page_index') or 1),
                    'line_number': idx + 1,
                    'feature': 'HSN_PROPAGATION',
                    'before_value': orig_hsn,
                    'after_value': prev_hsn,
                    'reason': reason,
                    'feature_flag': 'NORMALIZER_HSN_PROPAGATION'
                })}")
            else:
                prev_hsn = None
    
    # Create raw/intermediate schema dict first

    schema_data = {
        "invoice_no": str(raw_header.get("invoice_no", "")),
        "invoice_date": str(raw_header.get("invoice_date", "")),
        "vendor_name": str(raw_header.get("vendor_name", "")),
        "buyer_name": str(raw_header.get("buyer_name", "") or raw_header.get("customer_name", "")),
        "raw_buyer_name": str(raw_header.get("raw_buyer_name") or raw_header.get("buyer_name") or ""),
        "canonical_buyer_name": str(raw_header.get("canonical_buyer_name") or raw_header.get("buyer_name") or ""),
        "gstin": str(raw_header.get("gstin", "")),

        "raw_gstin": str(raw_header.get("raw_gstin", "")),
        "canonical_gstin": str(raw_header.get("canonical_gstin", "")),
        "branch": str(raw_header.get("branch", "")),
        "bill_from": str(raw_header.get("bill_from", "")),
        "bill_to": str(raw_header.get("bill_to", "")),
        "place_of_supply": str(raw_header.get("place_of_supply", "")),
        "total_taxable_value": normalize_amount(raw_header.get("total_taxable_value", 0)),
        "total_igst": normalize_amount(raw_header.get("total_igst", 0)),
        "total_cgst": normalize_amount(raw_header.get("total_cgst", 0)),
        "total_sgst": normalize_amount(raw_header.get("total_sgst", 0)),
        "total_cess": normalize_amount(raw_header.get("total_cess", 0)),
        "round_off": normalize_amount(raw_header.get("round_off", 0)),
        "total_invoice_value": normalize_amount(raw_header.get("total_invoice_value", 0)),
        "irn": str(raw_header.get("irn", "")),
        "ack_no": str(raw_header.get("ack_no", "")),
        "ack_date": str(raw_header.get("ack_date", "")),
        "cgst_rate": normalize_amount(raw_header.get("cgst_rate", 0)),
        "sgst_rate": normalize_amount(raw_header.get("sgst_rate", 0)),
        "igst_rate": normalize_amount(raw_header.get("igst_rate", 0)),
        "header_cgst_rate": normalize_amount(raw_header.get("header_cgst_rate", 0)),
        "header_sgst_rate": normalize_amount(raw_header.get("header_sgst_rate", 0)),
        "header_igst_rate": normalize_amount(raw_header.get("header_igst_rate", 0)),

        
        # Explicit GSTIN Role Fields
        "vendor_gstin": str(raw_header.get("vendor_gstin", "")),
        "buyer_gstin": str(raw_header.get("buyer_gstin", "")),
        "consignee_gstin": str(raw_header.get("consignee_gstin", "")),
        "ship_to_gstin": str(raw_header.get("ship_to_gstin", "")),
        "bill_to_gstin": str(raw_header.get("bill_to_gstin", "")),
        "raw_vendor_gstin": str(raw_header.get("raw_vendor_gstin", "")),
        "raw_buyer_gstin": str(raw_header.get("raw_buyer_gstin", "")),
        "raw_consignee_gstin": str(raw_header.get("raw_consignee_gstin", "")),
        "raw_bill_to_gstin": str(raw_header.get("raw_bill_to_gstin", "")),
        "raw_ship_to_gstin": str(raw_header.get("raw_ship_to_gstin", "")),
        "canonical_vendor_gstin": str(raw_header.get("canonical_vendor_gstin", "")),
        "canonical_buyer_gstin": str(raw_header.get("canonical_buyer_gstin", "")),
        "canonical_consignee_gstin": str(raw_header.get("canonical_consignee_gstin", "")),
        "canonical_bill_to_gstin": str(raw_header.get("canonical_bill_to_gstin", "")),
        "canonical_ship_to_gstin": str(raw_header.get("canonical_ship_to_gstin", "")),

        "items": [copy.deepcopy(item) for item in raw_items],
        "warnings": invoice.get("_warning_flags", []) if isinstance(invoice, dict) else []
    }

    # 3. Deterministic Tax Distribution
    if os.getenv("NORMALIZER_TAX_DISTRIBUTION", "true").lower() == "true":
        total_taxable = schema_data.get("total_taxable_value", 0.0)
        total_cgst = schema_data.get("total_cgst", 0.0)
        total_sgst = schema_data.get("total_sgst", 0.0)
        total_igst = schema_data.get("total_igst", 0.0)
        
        sum_taxables = sum(normalize_amount(item.get("taxable_value")) for item in schema_data.get("items", []))
        tolerance_val = float(os.getenv("NORMALIZER_TAX_TOLERANCE", "1.00"))
        
        taxables_match = abs(total_taxable - sum_taxables) <= tolerance_val
        
        all_taxes_zero = all(
            normalize_amount(item.get("cgst")) == 0.0 and 
            normalize_amount(item.get("sgst")) == 0.0 and 
            normalize_amount(item.get("igst")) == 0.0 and
            normalize_amount(item.get("cgst_rate")) == 0.0 and 
            normalize_amount(item.get("sgst_rate")) == 0.0 and 
            normalize_amount(item.get("igst_rate")) == 0.0
            for item in schema_data.get("items", [])
        )
        
        is_igst = total_igst > 0
        has_items = len(schema_data.get("items", [])) > 0
        
        if (total_cgst > 0 and total_sgst > 0 and total_taxable > 0 and 
            taxables_match and all_taxes_zero and not is_igst and has_items):
            
            raw_cgst_rate = (total_cgst / total_taxable) * 100
            raw_sgst_rate = (total_sgst / total_taxable) * 100
            
            cgst_rate = snap_to_standard_gst_rate(raw_cgst_rate)
            sgst_rate = snap_to_standard_gst_rate(raw_sgst_rate)
            
            # Strict snap verify: calculated rate must snap precisely within 0.1% of standard rate
            if abs(cgst_rate - raw_cgst_rate) <= 0.1 and abs(sgst_rate - raw_sgst_rate) <= 0.1:
                logger.info(f"[TAX_DISTRIBUTION_ELIGIBLE] cgst_rate={cgst_rate} sgst_rate={sgst_rate}")
                for idx, item in enumerate(schema_data.get("items", [])):
                    orig_cgst = item.get("cgst", 0.0)
                    orig_sgst = item.get("sgst", 0.0)
                    orig_cgst_rate = item.get("cgst_rate", 0.0)
                    orig_sgst_rate = item.get("sgst_rate", 0.0)
                    
                    item_taxable = normalize_amount(item.get("taxable_value"))
                    item["cgst_rate"] = cgst_rate
                    item["sgst_rate"] = sgst_rate
                    item["cgst"] = round(item_taxable * (cgst_rate / 100.0), 2)
                    item["sgst"] = round(item_taxable * (sgst_rate / 100.0), 2)
                    item["total_amount"] = item_taxable + item["cgst"] + item["sgst"]
                    
                    logger.info(f"[AUDIT_DETERMINISTIC_CORRECTION] {json.dumps({
                        'prefix': '[AUDIT_DETERMINISTIC_CORRECTION]',
                        'timestamp': datetime.now().isoformat() + 'Z',
                        'invoice_id': str(invoice.get('record_id') or invoice.get('id') or ''),
                        'page_number': int(invoice.get('page_number') or invoice.get('page_index') or 1),
                        'line_number': idx + 1,
                        'feature': 'TAX_DISTRIBUTION',
                        'before_value': f"CGST={orig_cgst}({orig_cgst_rate}%), SGST={orig_sgst}({orig_sgst_rate}%)",
                        'after_value': f"CGST={item['cgst']}({item['cgst_rate']}%), SGST={item['sgst']}({item['sgst_rate']}%)",
                        'reason': f"Distributed header rates (calculated={raw_cgst_rate:.2f}%, snapped={cgst_rate}%)",
                        'feature_flag': 'NORMALIZER_TAX_DISTRIBUTION'
                    })}")
            else:
                logger.warning(f"[TAX_DISTRIBUTION_ABORT] Snapped rates cgst={cgst_rate}% sgst={sgst_rate}% deviate too far from raw values ({raw_cgst_rate:.2f}%, {raw_sgst_rate:.2f}%)")
    
    # Promote HSN/SAC from the first item if missing in header
    primary_item = raw_items[0] if raw_items else {}

    logger.info(f"[HSN_TRACE_INPUT] primary_item_keys={list(primary_item.keys())}")
    
    if is_empty(schema_data.get("hsn_sac")):
        schema_data["hsn_sac"] = (
            primary_item.get("hsn_sac")
            or primary_item.get("hsn")
            or primary_item.get("sac")
            or ""
        )
        logger.info(f"[HSN_CANONICALIZED] value='{schema_data['hsn_sac']}' source=primary_item")
    else:
        logger.info(f"[HSN_CANONICALIZED] value='{schema_data['hsn_sac']}' source=header")
        
    # ── Run Pre-processing Canonicalization Layer ──
    from ocr_pipeline.canonicalizer import DocumentIdentityCanonicalizer
    schema_data = DocumentIdentityCanonicalizer.canonicalize_invoice(schema_data)
    
    # Map raw_items in schema_data to CanonicalInvoiceItem
    canonical_items = []
    for item in schema_data.get("items", []):
        try:
            c_item = CanonicalInvoiceItem(
                description=str(item.get("description", "")),
                hsn_sac=str(item.get("hsn_sac", "")),
                qty=normalize_amount(item.get("qty", 0.0)),
                uom=str(item.get("uom", "")),
                rate=normalize_amount(item.get("rate", 0.0)),
                taxable_value=normalize_amount(item.get("taxable_value", 0.0)),
                igst=normalize_amount(item.get("igst", 0.0)),
                cgst=normalize_amount(item.get("cgst", 0.0)),
                sgst=normalize_amount(item.get("sgst", 0.0)),
                total_amount=normalize_amount(item.get("total_amount", 0.0)),
                igst_rate=normalize_amount(item.get("igst_rate", 0.0)),
                cgst_rate=normalize_amount(item.get("cgst_rate", 0.0)),
                sgst_rate=normalize_amount(item.get("sgst_rate", 0.0)),
                cess_rate=normalize_amount(item.get("cess_rate", 0.0)),
                raw_item_name=str(item.get("raw_item_name", "")),
                canonical_item_name=str(item.get("canonical_item_name", "")),
                raw_hsn=str(item.get("raw_hsn", "")),
                canonical_hsn=str(item.get("canonical_hsn", "")),
                
                # Manual matching fields
                inventory_item_id=item.get("inventory_item_id"),
                inventory_match_strategy=item.get("inventory_match_strategy"),
                inventory_match_level=item.get("inventory_match_level"),
                inventory_match_confidence=item.get("inventory_match_confidence"),
                match_source=item.get("match_source"),
                matched_item_name=item.get("matched_item_name"),
                canonical_name=item.get("canonical_name"),
                item_status=item.get("item_status"),
            )
            canonical_items.append(c_item)
        except Exception as ie:
            logger.error(f"[DTO_ITEM_COERCION_FAIL] item={item} error={ie}")

    schema_data["items"] = canonical_items
    
    try:
        canonical_obj = CanonicalInvoiceSchema(**schema_data)
        logger.info(f"[DTO_POST_VALIDATION] record_id={invoice.get('record_id')} status=VALID")
    except Exception as se:
        logger.error(f"[DTO_VALIDATION_ERROR] record_id={invoice.get('record_id')} error={se} payload={json.dumps(schema_data, default=str)[:1000]}")
        # Ensure Pydantic items are converted back to dicts so they serialize correctly
        if "items" in schema_data:
            schema_data["items"] = [
                i.dict() if hasattr(i, "dict") else (i.model_dump() if hasattr(i, "model_dump") else i)
                for i in schema_data["items"]
            ]
        # Fallback to dictionary if Pydantic fails, but don't wipe data
        canonical_obj = type('Obj', (object,), {
            "dict": lambda self: schema_data, 
            "model_dump": lambda self: schema_data,
            "invoice_no": schema_data.get("invoice_no")
        })()
    
    # Forensic Log
    log_canonical_schema_locked(canonical_obj.invoice_no)

    # Convert back to dict for pipeline compatibility but ensure it's frozen
    try:
        if hasattr(canonical_obj, "dict"):
            canonical_record = canonical_obj.dict()
        else:
            canonical_record = canonical_obj.model_dump()
    except Exception as e_dict:
        logger.error(f"[NORMALIZATION_DICT_FAIL] error={e_dict}")
        canonical_record = schema_data

    # Preserve internal lifecycle fields (underscore fields)
    # ── [CRITICAL FIX] ──
    # Guard was previously `k not in canonical_record`, which failed for Pydantic
    # fields like `_pdf_ocr_text: Optional[str] = None` — these ARE in canonical_record
    # (serialized as None) so the real value from `invoice` was silently dropped.
    # Changed to `not canonical_record.get(k)` so any falsy/None Pydantic default
    # is overwritten by the actual non-empty input value (e.g. OCR text).
    if isinstance(invoice, dict):
        for k, v in invoice.items():
            if k.startswith("_") and not canonical_record.get(k):
                canonical_record[k] = v

                
    output_hash = hashlib.md5(json.dumps(canonical_record, sort_keys=True, default=str).encode()).hexdigest()
    logger.info(f"[NORMALIZATION_OUTPUT_HASH] {output_hash}")

    # [PHASE 6] Translator Verification Diff
    monitored_fields = ["invoice_no", "gstin", "vendor_name", "total_invoice_value", "total_cgst", "total_sgst", "total_igst"]
    input_vals = {f: invoice.get(f) if isinstance(invoice, dict) else None for f in monitored_fields}
    for f in monitored_fields:
        in_v = input_vals.get(f)
        out_v = canonical_record.get(f)
        if str(in_v) != str(out_v):
            logger.info(f"[TRANSLATOR_MUTATION] field={f} input='{in_v}' output='{out_v}'")
        else:
            logger.info(f"[TRANSLATOR_PASSTHROUGH] field={f} value='{out_v}'")

    trans_duration_ms = int((time.time() - t_start_trans) * 1000) if 't_start_trans' in locals() else 0
    from ocr_pipeline.pipeline_telemetry import PipelineStageTelemetry
    PipelineStageTelemetry.record_stage(
        "Translator",
        {"input_keys_count": len(invoice) if isinstance(invoice, dict) else 0},
        {"output_keys_count": len(canonical_record)},
        trans_duration_ms
    )

    return canonical_record

def get_ui_payload(invoice: Any) -> Dict[str, Any]:
    """
    UI EGRESS MAPPING.
    STRICT CANONICAL PASSTHROUGH.
    [PHASE 11.9] Removed Title Case conversion. Frontend now expects canonical keys.
    """
    ui_payload = get_canonical_export_record(invoice)
    
    # Forensic Row Audit
    logger.debug(f"[CANONICAL_ROW_KEYS] keys={list(ui_payload.keys())}")
    logger.debug(f"[TABLE_RENDER_VALUE] invoice_no='{ui_payload.get('invoice_no')}' total='{ui_payload.get('total_invoice_value')}'")
                
    return ui_payload

print("[NORMALIZE_EXPORT_CHECK]", "lossless_preserve" in globals())
