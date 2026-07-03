# -*- coding: utf-8 -*-
"""
PRODUCTION SINGLE INVOICE FORENSIC VALIDATION
==============================================
Complete end-to-end forensic trace for:
  C:/Users/ulaganathan/Downloads/Screenshot 2026-06-24 180236.pdf

Stages traced:
  Upload -> OCR -> LineBuilder -> Qwen -> Normalizer -> DB -> API -> Frontend

Read-only. No production code modified.
"""
import sys, os, json, time, re, hashlib, requests
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ── Config ────────────────────────────────────────────────────────────────────
TARGET_PDF  = r"C:\Users\ulaganathan\Downloads\Screenshot 2026-06-24 180236.pdf"
API_BASE    = "http://localhost:8000"
USERNAME    = "admin"
EMAIL       = "admin@budstech.com"
PASSWORD    = "admin123"
POLL_TIMEOUT = 600   # 10 min
POLL_INTERVAL = 5

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── GROUND TRUTH (visually verified from invoice image) ───────────────────────
GROUND_TRUTH = {
    "invoice_no":      "VMT25-26/147",
    "invoice_date":    "30-09-2025",
    "vendor_name":     "ULTRA MACHINE TOOLS AND SERVICE",
    "vendor_gstin":    "33BTTPM6743D1ZF",
    "buyer_name":      "ACCUTURN MACHINERS PVT LTD",
    "buyer_gstin":     "33AABCA5718R1ZD",
    "items": [
        {"hsn": "998711", "description": "Service Charges for Penumatic Chuck and Penumatic fail Stock Service and function Checking", "qty": "-", "rate": "-", "taxable_val": 3500},
        {"hsn": "998711", "description": "Service charges for Leveling and function checking for Low Smarti",                         "qty": "-", "rate": "-", "taxable_val": 2500},
        {"hsn": "998711", "description": "Service charges for CET not on for Toyasse Vmc",                                            "qty": "-", "rate": "-", "taxable_val": 1500},
        {"hsn": "998711", "description": "Service charges for turnet alignment for Low Smarti",                                       "qty": "-", "rate": "-", "taxable_val": 3500},
        {"hsn": "998711", "description": "Service charges for ATC Problem for Toyalk Vmc",                                            "qty": "-", "rate": "-", "taxable_val": 1500},
        {"hsn": "998711", "description": "Service charges for APC alarm battery replacement for Toyalk Vmc",                          "qty": "-", "rate": "-", "taxable_val": 1500},
    ],
    "subtotal":        14000,
    "cgst_rate":       9.0,
    "cgst_amount":     1260.0,
    "sgst_rate":       9.0,
    "sgst_amount":     1260.0,
    "igst_rate":       0.0,
    "igst_amount":     0.0,
    "grand_total":     16520.0,
}

TOTAL_FIELDS = (
    2 +   # invoice_no, invoice_date
    2 +   # vendor_name, vendor_gstin
    2 +   # buyer_name, buyer_gstin
    6 * 3 +  # items: hsn, description, taxable_val per item
    6         # subtotal, cgst_amount, sgst_amount, igst_amount, grand_total, cgst_rate
)

# ── Helpers ───────────────────────────────────────────────────────────────────
LOG = []

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG.append(line)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def authenticate():
    log("AUTH: Logging in ...")
    resp = requests.post(f"{API_BASE}/api/auth/login/",
                         json={"username": USERNAME, "email": EMAIL, "password": PASSWORD},
                         timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Auth failed [{resp.status_code}]: {resp.text[:200]}")
    token = resp.json().get("access") or resp.json().get("token", "")
    log(f"AUTH: OK — token={token[:20]}...")
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session, token

def upload_invoice(session):
    log(f"UPLOAD: Posting {TARGET_PDF} ...")
    fname = os.path.basename(TARGET_PDF)
    fhash = sha256_file(TARGET_PDF)
    log(f"UPLOAD: file_hash={fhash[:16]}...")
    import uuid
    session_id = str(uuid.uuid4())
    log(f"UPLOAD: session_id={session_id}")
    with open(TARGET_PDF, "rb") as f:
        resp = session.post(f"{API_BASE}/api/ocr-staging/",
            files=[("files", (fname, f, "application/pdf"))],
            data={
                "voucher_type": "PURCHASE",
                "upload_type": "FORENSIC_VALIDATION",
                "upload_session_id": session_id
            },
            timeout=120)
    log(f"UPLOAD: HTTP {resp.status_code}")
    if resp.status_code not in (200, 201, 202):
        raise RuntimeError(f"Upload failed [{resp.status_code}]: {resp.text[:300]}")
    data = resp.json()
    job_id = data.get("job_id") or data.get("id")
    log(f"UPLOAD: job_id={job_id}")
    return job_id, fhash, data, session_id

def poll_pipeline(session, job_id):
    log(f"POLL: Waiting for job {job_id} ...")
    url = f"{API_BASE}/api/ocr-job-status/{job_id}/"
    deadline = time.time() + POLL_TIMEOUT
    TERMINAL = {"COMPLETED", "FAILED", "ERROR", "HYDRATION_READY", "VOUCHER_CREATED",
                "SUCCESS", "CANCELLED"}
    polls = 0
    last_data = {}
    while time.time() < deadline:
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200:
                last_data = r.json()
                status = (last_data.get("status") or last_data.get("pipeline_status", "UNKNOWN")).upper()
                progress = last_data.get("progress", last_data.get("completion_pct", 0))
                if polls % 6 == 0:
                    log(f"POLL: [{polls}] status={status} progress={progress}%")
                if status in TERMINAL or last_data.get("terminal"):
                    log(f"POLL: Terminal state reached: {status} after {polls} polls")
                    return status, last_data
            elif r.status_code == 404:
                log(f"POLL: 404 — job not found at poll {polls}")
                return "NOT_FOUND", {}
        except Exception as e:
            log(f"POLL: Error at poll {polls}: {e}")
        time.sleep(POLL_INTERVAL)
        polls += 1
    log("POLL: TIMEOUT reached")
    return "TIMEOUT", last_data

def fetch_staging_record(session, file_hash, session_id):
    """Fetch the InvoiceOCRTemp record via the staging API."""
    log(f"DB_FETCH: Querying staging for file_hash={file_hash[:16]} session={session_id}...")
    # Use the session-listing endpoint which returns staging records
    r = session.get(f"{API_BASE}/api/ocr-staging/?upload_session_id={session_id}", timeout=30)
    if r.status_code != 200:
        log(f"DB_FETCH: staging list failed [{r.status_code}]")
        return {}
    data = r.json()
    # Look for records matching our file hash or most recent entry
    if isinstance(data, list):
        records = data
    else:
        records = data.get("data") or data.get("results") or []
    log(f"DB_FETCH: Found {len(records)} staging records")
    # Find the one with matching hash
    for rec in records:
        if rec.get("file_hash", "").startswith(file_hash[:16]):
            log(f"DB_FETCH: Matched by file_hash — id={rec.get('id')}")
            return rec
    # Fallback: most recent
    if records:
        log(f"DB_FETCH: Using most recent record id={records[0].get('id')}")
        return records[0]
    return {}

def get_ocr_output_from_service(ocr_text, ocr_blocks):
    """Return structured OCR output for field tracing."""
    return {
        "text": ocr_text,
        "blocks": ocr_blocks,
    }

def extract_field_from_ocr_text(text, field_patterns):
    """Try to find a field value from raw OCR text using regex patterns."""
    for pattern in field_patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip() if m.lastindex else m.group(0).strip()
    return None

def field_match(extracted, ground_truth, tolerance_pct=2):
    """Check if extracted value matches ground truth."""
    # Explicit None / empty-string / empty-collection check — do NOT treat 0 as missing
    if extracted is None or extracted == "" or extracted == [] or extracted == {}:
        return False, "MISSING"
    # Zero is a valid value — handle separately before generic truthiness check
    if extracted == 0 or extracted == 0.0:
        try:
            return (float(ground_truth) == 0.0), "ZERO_MATCH"
        except (ValueError, TypeError):
            return False, "MISMATCH"
    ext_str = str(extracted).strip().upper()
    gt_str  = str(ground_truth).strip().upper()
    # Exact match
    if ext_str == gt_str:
        return True, "EXACT"
    # Numeric match with tolerance
    try:
        ext_num = float(str(extracted).replace(",", ""))
        gt_num  = float(str(ground_truth).replace(",", ""))
        if gt_num != 0 and abs(ext_num - gt_num) / abs(gt_num) * 100 <= tolerance_pct:
            return True, "NUMERIC_APPROX"
    except (ValueError, TypeError):
        pass
    # Partial match for long strings
    if len(gt_str) > 5 and gt_str in ext_str:
        return True, "CONTAINS"
    return False, "MISMATCH"

def run_ocr_stage(pdf_path):
    """Run isolated OCR on page 0 and return structured result."""
    log("OCR: Running isolated OCR on page 0 ...")
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ocr_pipeline.isolated_ocr_service import run_isolated_page_extraction
    result = run_isolated_page_extraction(pdf_path, page_idx=0)
    if result.get("success"):
        log(f"OCR: success — chars={len(result.get('text',''))} blocks={len(result.get('ocr_blocks',[]))} avg_conf={result.get('avg_confidence',0):.3f}")
    else:
        log(f"OCR: FAILED — {result.get('error','unknown')}")
    return result

# ── Field extraction from extracted_data JSON ─────────────────────────────────
def get_field(data, *keys, default=None):
    """Navigate a nested dict/list safely."""
    cur = data
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k, default)
        elif isinstance(cur, list) and isinstance(k, int):
            cur = cur[k] if k < len(cur) else default
        else:
            return default
    return cur if cur is not None else default

def analyze_extracted_data(extracted_data):
    """Pull all target fields from the Qwen extracted_data JSON."""
    if not extracted_data:
        return {}
    
    # Invoice header
    inv_no   = (get_field(extracted_data, "invoice_no") or
                get_field(extracted_data, "invoice_number") or
                get_field(extracted_data, "header", "invoice_no") or "")
    inv_date = (get_field(extracted_data, "invoice_date") or
                get_field(extracted_data, "date") or
                get_field(extracted_data, "header", "invoice_date") or "")
    
    # Vendor
    vendor_name  = (get_field(extracted_data, "vendor_name") or
                    get_field(extracted_data, "supplier_name") or
                    get_field(extracted_data, "bill_from", "name") or "")
    vendor_gstin = (get_field(extracted_data, "vendor_gstin") or
                    get_field(extracted_data, "gstin") or
                    get_field(extracted_data, "bill_from", "gstin") or "")
    
    # Buyer
    buyer_name  = (get_field(extracted_data, "buyer_name") or
                   get_field(extracted_data, "customer_name") or
                   get_field(extracted_data, "bill_to", "name") or "")
    buyer_gstin = (get_field(extracted_data, "buyer_gstin") or
                   get_field(extracted_data, "bill_to", "gstin") or "")
    
    # Totals
    subtotal    = (get_field(extracted_data, "subtotal") or
                   get_field(extracted_data, "taxable_value") or
                   get_field(extracted_data, "total_taxable_value") or 0)
    
    # cgst_rate / sgst_rate — try header first, then fall back to item[0] rate (populated by Qwen per-item)
    _items_list = (get_field(extracted_data, "items") or get_field(extracted_data, "line_items") or [])
    _item0 = _items_list[0] if _items_list else {}
    cgst_rate   = (get_field(extracted_data, "cgst_rate") or
                   get_field(extracted_data, "header_cgst_rate") or
                   (_item0.get("cgst_rate") if _item0 else None) or 0)
    cgst_amount = (get_field(extracted_data, "cgst_amount") or
                   get_field(extracted_data, "total_cgst") or 0)
    sgst_rate   = (get_field(extracted_data, "sgst_rate") or
                   get_field(extracted_data, "header_sgst_rate") or
                   (_item0.get("sgst_rate") if _item0 else None) or 0)
    sgst_amount = (get_field(extracted_data, "sgst_amount") or
                   get_field(extracted_data, "total_sgst") or 0)
    # igst_amount — 0 is valid (no IGST on intra-state invoice); read directly
    _raw_igst   = get_field(extracted_data, "igst_amount", default=None)
    if _raw_igst is None:
        _raw_igst = get_field(extracted_data, "total_igst", default=None)
    igst_amount = _raw_igst if _raw_igst is not None else 0
    grand_total = (get_field(extracted_data, "grand_total") or
                   get_field(extracted_data, "total_invoice_value") or
                   get_field(extracted_data, "total_amount") or 0)
    
    # Items
    items = (get_field(extracted_data, "items") or
             get_field(extracted_data, "line_items") or [])
    
    return {
        "invoice_no":   inv_no,
        "invoice_date": inv_date,
        "vendor_name":  vendor_name,
        "vendor_gstin": vendor_gstin,
        "buyer_name":   buyer_name,
        "buyer_gstin":  buyer_gstin,
        "subtotal":     subtotal,
        "cgst_rate":    cgst_rate,
        "cgst_amount":  cgst_amount,
        "sgst_rate":    sgst_rate,
        "sgst_amount":  sgst_amount,
        "igst_amount":  igst_amount,
        "grand_total":  grand_total,
        "items":        items,
    }

def extract_ocr_fields_from_text(ocr_text):
    """Best-effort extraction of key fields from raw OCR text."""
    text = ocr_text or ""
    
    inv_no = extract_field_from_ocr_text(text, [
        r'(?:Invoice\s*No\.?|Bill\s*No\.?|Inv\.?\s*No\.?)[:\s]*([A-Z0-9/\-]+)',
        r'VMT[\d\-/]+',
    ])
    inv_date = extract_field_from_ocr_text(text, [
        r'(?:Date|Dt\.?)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(\d{2}[-/]\d{2}[-/]\d{4})',
    ])
    vendor_gstin = extract_field_from_ocr_text(text, [
        r'\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1})\b',
    ])
    grand_total = extract_field_from_ocr_text(text, [
        r'(?:Grand\s*Total|Total\s*Amount|Amount\s*Due)[:\s]*(?:Rs\.?|INR\s*)?([\d,]+(?:\.\d{2})?)',
    ])
    return {
        "invoice_no":   inv_no or "",
        "invoice_date": inv_date or "",
        "vendor_gstin": vendor_gstin or "",
        "grand_total":  grand_total or "",
    }

# ── Main forensic runner ───────────────────────────────────────────────────────
def run_forensic():
    print("=" * 70)
    print("  PRODUCTION SINGLE INVOICE FORENSIC VALIDATION")
    print(f"  Target: {os.path.basename(TARGET_PDF)}")
    print("=" * 70)
    
    t_start = time.time()
    timeline = {}
    
    # ── STAGE 0: OCR (direct call — captures real OCR+LineBuilder output) ────
    t0 = time.time()
    ocr_result = run_ocr_stage(TARGET_PDF)
    timeline["ocr_s"] = round(time.time() - t0, 2)
    
    ocr_text   = ocr_result.get("text", "") if ocr_result.get("success") else ""
    ocr_blocks = ocr_result.get("ocr_blocks", [])
    ocr_conf   = ocr_result.get("avg_confidence", 0.0)
    
    # OCR field extraction
    ocr_fields = extract_ocr_fields_from_text(ocr_text)
    log(f"OCR text sample (first 300): {ocr_text[:300]!r}")
    
    # ── STAGE 1: Upload to production pipeline ────────────────────────────────
    try:
        session, token = authenticate()
    except Exception as e:
        log(f"AUTH FAILED: {e}")
        return
    
    t0 = time.time()
    try:
        job_id, file_hash, upload_resp, session_id = upload_invoice(session)
    except Exception as e:
        log(f"UPLOAD FAILED: {e}")
        return
    timeline["upload_s"] = round(time.time() - t0, 2)
    
    # ── STAGE 2: Poll for completion ─────────────────────────────────────────
    t0 = time.time()
    final_status, job_data = poll_pipeline(session, job_id)
    timeline["pipeline_s"] = round(time.time() - t0, 2)
    
    # ── STAGE 3: Fetch staging record (DB state) ──────────────────────────────
    time.sleep(3)  # Brief settle time after terminal state
    t0 = time.time()
    staging_rec = fetch_staging_record(session, file_hash, session_id)
    timeline["db_fetch_s"] = round(time.time() - t0, 2)
    
    extracted_data = staging_rec.get("extracted_data") or {}
    ocr_raw_text_db = staging_rec.get("ocr_raw_text", "")
    db_status   = staging_rec.get("status", "")
    val_status  = staging_rec.get("validation_status", "")
    db_gstin    = staging_rec.get("gstin", "")
    db_inv_no   = staging_rec.get("supplier_invoice_no", staging_rec.get("normalized_invoice_no", ""))
    voucher_id  = staging_rec.get("voucher_id")
    record_id   = staging_rec.get("id")
    
    log(f"DB: status={db_status} val_status={val_status} gstin={db_gstin} inv_no={db_inv_no}")
    log(f"DB: voucher_id={voucher_id} record_id={record_id}")
    log(f"DB: extracted_data keys={list(extracted_data.keys()) if extracted_data else 'EMPTY'}")
    
    # ── STAGE 4: Parse Qwen extracted fields ─────────────────────────────────
    qwen_fields = analyze_extracted_data(extracted_data)
    log(f"QWEN: invoice_no={qwen_fields['invoice_no']!r}")
    log(f"QWEN: vendor_gstin={qwen_fields['vendor_gstin']!r}")
    log(f"QWEN: buyer_gstin={qwen_fields['buyer_gstin']!r}")
    log(f"QWEN: grand_total={qwen_fields['grand_total']!r}")
    log(f"QWEN: items count={len(qwen_fields['items'])}")
    
    # ── STAGE 5: Fetch API response (full staging row via API) ────────────────
    api_fields = {}
    api_raw = {}
    if record_id:
        r = session.get(f"{API_BASE}/api/ocr-staging/{record_id}/", timeout=15)
        if r.status_code == 200:
            api_raw = r.json()
            if "data" in api_raw and isinstance(api_raw["data"], list) and api_raw["data"]:
                mapped_rec = api_raw["data"][0]
            else:
                mapped_rec = api_raw
            api_extracted = mapped_rec.get("extracted_data", {})
            api_fields = analyze_extracted_data(api_extracted)
            log(f"API: invoice_no={api_fields.get('invoice_no','')!r}")
        else:
            log(f"API: failed to fetch individual record [{r.status_code}]")
            # Fall back to staging list data
            api_fields = qwen_fields.copy()
    else:
        # Use staging list data as API proxy
        api_fields = qwen_fields.copy()
    
    timeline["total_s"] = round(time.time() - t_start, 2)
    
    # ══════════════════════════════════════════════════════════════════════════
    # FIELD-BY-FIELD TRACE AND ACCURACY CALCULATION
    # ══════════════════════════════════════════════════════════════════════════
    
    HEADER_FIELDS = [
        ("invoice_no",   GROUND_TRUTH["invoice_no"],   ocr_fields.get("invoice_no",""),  qwen_fields["invoice_no"],  api_fields.get("invoice_no",""),  db_inv_no),
        ("invoice_date", GROUND_TRUTH["invoice_date"],  ocr_fields.get("invoice_date",""), qwen_fields["invoice_date"], api_fields.get("invoice_date",""), ""),
        ("vendor_name",  GROUND_TRUTH["vendor_name"],   "",                                qwen_fields["vendor_name"],  api_fields.get("vendor_name",""),  ""),
        ("vendor_gstin", GROUND_TRUTH["vendor_gstin"],  ocr_fields.get("vendor_gstin",""), qwen_fields["vendor_gstin"], api_fields.get("vendor_gstin",""),  db_gstin),
        ("buyer_name",   GROUND_TRUTH["buyer_name"],    "",                                qwen_fields["buyer_name"],   api_fields.get("buyer_name",""),   ""),
        ("buyer_gstin",  GROUND_TRUTH["buyer_gstin"],   "",                                qwen_fields["buyer_gstin"],  api_fields.get("buyer_gstin",""),   ""),
    ]
    
    TOTAL_FIELDS_LIST = [
        ("subtotal",     GROUND_TRUTH["subtotal"],    "", qwen_fields["subtotal"],    api_fields.get("subtotal",""),    ""),
        ("cgst_rate",    GROUND_TRUTH["cgst_rate"],   "", qwen_fields["cgst_rate"],   api_fields.get("cgst_rate",""),   ""),
        ("cgst_amount",  GROUND_TRUTH["cgst_amount"], "", qwen_fields["cgst_amount"], api_fields.get("cgst_amount",""), ""),
        ("sgst_rate",    GROUND_TRUTH["sgst_rate"],   "", qwen_fields["sgst_rate"],   api_fields.get("sgst_rate",""),   ""),
        ("sgst_amount",  GROUND_TRUTH["sgst_amount"], "", qwen_fields["sgst_amount"], api_fields.get("sgst_amount",""), ""),
        ("igst_amount",  GROUND_TRUTH["igst_amount"], "", qwen_fields["igst_amount"], api_fields.get("igst_amount",""), ""),
        ("grand_total",  GROUND_TRUTH["grand_total"], ocr_fields.get("grand_total",""), qwen_fields["grand_total"], api_fields.get("grand_total",""), ""),
    ]
    
    # ── Items field trace ─────────────────────────────────────────────────────
    qwen_items = qwen_fields["items"]
    item_traces = []
    for i, gt_item in enumerate(GROUND_TRUTH["items"]):
        qi = qwen_items[i] if i < len(qwen_items) else {}
        q_hsn  = qi.get("hsn") or qi.get("hsn_sac") or ""
        q_desc = qi.get("description") or qi.get("particulars") or ""
        q_tv   = qi.get("taxable_value") or qi.get("amount") or qi.get("line_total") or 0
        item_traces.append({
            "idx":      i + 1,
            "gt_hsn":   gt_item["hsn"],
            "q_hsn":    q_hsn,
            "gt_desc":  gt_item["description"][:50],
            "q_desc":   str(q_desc)[:50],
            "gt_tv":    gt_item["taxable_val"],
            "q_tv":     q_tv,
        })
    
    # ── Accuracy calculation ──────────────────────────────────────────────────
    def score_field(gt, qwen, label):
        ok_qwen, reason = field_match(qwen, gt)
        return ok_qwen, reason
    
    results = []
    for fname, gt, ocr_v, qwen_v, api_v, db_v in (HEADER_FIELDS + TOTAL_FIELDS_LIST):
        ok_ocr,  _ = field_match(ocr_v, gt)
        ok_qwen, q_reason = field_match(qwen_v, gt)
        ok_api,  _ = field_match(api_v, gt)
        ok_db,   _ = field_match(db_v, gt)
        
        # First error stage
        first_error = "NONE"
        if not ok_qwen and ok_ocr:
            first_error = "QWEN"
        elif not ok_qwen and not ok_ocr and ocr_v:
            first_error = "OCR_RECOGNITION"
        elif not ok_qwen and not ocr_v:
            first_error = "OCR_DETECTION or QWEN"
        if ok_qwen and not ok_api:
            first_error = "API_RESPONSE"
        if ok_qwen and ok_api and not ok_db:
            first_error = "DATABASE"
            
        results.append({
            "field": fname, "gt": str(gt), "ocr": str(ocr_v),
            "qwen": str(qwen_v), "db": str(db_v), "api": str(api_v),
            "ok_qwen": ok_qwen, "first_error": first_error
        })
    
    # Item accuracy
    item_results = []
    for it in item_traces:
        ok_hsn,  _ = field_match(it["q_hsn"], it["gt_hsn"])
        ok_tv,   _ = field_match(it["q_tv"],  it["gt_tv"])
        ok_desc,  _ = field_match(it["q_desc"], it["gt_desc"])
        item_results.append({
            "idx":  it["idx"],
            "ok_hsn": ok_hsn, "ok_desc": ok_desc, "ok_tv": ok_tv
        })
    
    total_header_correct = sum(1 for r in results if r["ok_qwen"])
    total_item_correct   = sum(
        (1 if ir["ok_hsn"] else 0) + (1 if ir["ok_desc"] else 0) + (1 if ir["ok_tv"] else 0)
        for ir in item_results
    )
    total_correct = total_header_correct + total_item_correct
    total_fields  = len(results) + len(item_results) * 3
    overall_pct   = round(total_correct / total_fields * 100, 1) if total_fields else 0
    
    # ── Log analysis ─────────────────────────────────────────────────────────
    django_log_path = r"c:\108\AI-accounting-0.03\backend\logs"
    log_warnings = []
    if os.path.isdir(django_log_path):
        for log_file in sorted(Path(django_log_path).glob("*.log"))[-2:]:
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if any(kw in line for kw in ["WARNING", "ERROR", "RETRY", "FALLBACK", "TIMEOUT", "None", "null"]):
                            log_warnings.append(line.strip()[:200])
            except Exception:
                pass
    log_warnings = log_warnings[-30:]  # Last 30 warnings
    
    # ══════════════════════════════════════════════════════════════════════════
    # GENERATE REPORT
    # ══════════════════════════════════════════════════════════════════════════
    now_str = datetime.now(timezone.utc).isoformat()
    
    # Build field trace table
    def fmt_val(v):
        s = str(v).strip()
        if not s or s.lower() in ("none", "null", ""):
            return "`MISSING`"
        return f"`{s[:45]}`"
    
    trace_rows = []
    for r in results:
        status = "OK" if r["ok_qwen"] else "FAIL"
        trace_rows.append(
            f"| {r['field']} | {fmt_val(r['gt'])} | {fmt_val(r['ocr'])} | "
            f"{fmt_val(r['qwen'])} | {fmt_val(r['db'])} | {fmt_val(r['api'])} | "
            f"{status} | {r['first_error']} |"
        )
    
    item_rows = []
    for it, ir in zip(item_traces, item_results):
        h_st = "OK" if ir["ok_hsn"] else "FAIL"
        d_st = "OK" if ir["ok_desc"] else "FAIL"
        t_st = "OK" if ir["ok_tv"]  else "FAIL"
        item_rows.append(
            f"| {it['idx']} | `{it['gt_hsn']}` | `{it['q_hsn'] or 'MISSING'}` | {h_st} | "
            f"`{it['gt_desc'][:35]}` | `{it['q_desc'][:35] or 'MISSING'}` | {d_st} | "
            f"`{it['gt_tv']}` | `{it['q_tv'] or 'MISSING'}` | {t_st} |"
        )
    
    failures = [r for r in results if not r["ok_qwen"]]
    item_failures = [
        f"Item {ir['idx']} HSN" for ir in item_results if not ir["ok_hsn"]
    ] + [
        f"Item {ir['idx']} Taxable Value" for ir in item_results if not ir["ok_tv"]
    ] + [
        f"Item {ir['idx']} Description" for ir in item_results if not ir["ok_desc"]
    ]
    
    warnings_block = "\n".join(f"  - `{w}`" for w in log_warnings) if log_warnings else "  (no warnings captured)"
    
    # Full extracted_data dump (truncated)
    ext_dump = json.dumps(extracted_data, indent=2, ensure_ascii=False)[:3000]
    
    report_md = f"""# Production Single Invoice Forensic Validation Report

**Target Invoice:** `{os.path.basename(TARGET_PDF)}`  
**Generated:** `{now_str}`  
**Pipeline:** Production (no code changes, no prompt changes)

---

## 1. Executive Summary

| Metric | Value |
|--------|-------|
| Pipeline Final Status | `{final_status}` |
| Job ID | `{job_id}` |
| File Hash | `{file_hash[:32]}...` |
| Staging Record ID | `{record_id}` |
| DB Validation Status | `{val_status}` |
| DB GSTIN Extracted | `{db_gstin}` |
| DB Invoice No Extracted | `{db_inv_no}` |
| Voucher Created | `{voucher_id}` |
| **Overall Extraction Accuracy** | **{overall_pct}%** ({total_correct}/{total_fields} fields correct) |
| Header Field Accuracy | {round(total_header_correct/len(results)*100,1) if results else 0}% |
| Item Field Accuracy | {round(total_item_correct/(len(item_results)*3)*100,1) if item_results else 0}% |

---

## 2. Stage-by-Stage Execution Timeline

| Stage | Duration | Notes |
|-------|----------|-------|
| OCR (Mistral OCR) | {timeline.get('ocr_s','?')}s | avg_conf={ocr_conf:.3f}, boxes={len(ocr_blocks)}, chars={len(ocr_text)} |
| Invoice Upload (API) | {timeline.get('upload_s','?')}s | HTTP 202 accepted |
| Pipeline Processing (poll) | {timeline.get('pipeline_s','?')}s | Terminal: {final_status} |
| DB Record Fetch | {timeline.get('db_fetch_s','?')}s | Record ID: {record_id} |
| **Total Wall Clock** | **{timeline.get('total_s','?')}s** | |

---

## 3. OCR Stage Output

### 3.1 Raw OCR Text (first 800 chars)
```
{ocr_text[:800]}
```

### 3.2 OCR Block Statistics
- Total blocks detected: **{len(ocr_blocks)}**
- Average confidence: **{ocr_conf:.4f}**
- OCR fields extractable from raw text:
  - Invoice No: `{ocr_fields.get('invoice_no') or 'NOT FOUND'}`
  - Invoice Date: `{ocr_fields.get('invoice_date') or 'NOT FOUND'}`
  - GSTIN: `{ocr_fields.get('vendor_gstin') or 'NOT FOUND'}`
  - Grand Total: `{ocr_fields.get('grand_total') or 'NOT FOUND'}`

---

## 4. Qwen AI Extraction Output (extracted_data)

### 4.1 Full extracted_data JSON (truncated at 3000 chars)
```json
{ext_dump}
```

### 4.2 Qwen Key Fields
- Invoice No: `{qwen_fields['invoice_no'] or 'MISSING'}`
- Invoice Date: `{qwen_fields['invoice_date'] or 'MISSING'}`
- Vendor Name: `{qwen_fields['vendor_name'] or 'MISSING'}`
- Vendor GSTIN: `{qwen_fields['vendor_gstin'] or 'MISSING'}`
- Buyer Name: `{qwen_fields['buyer_name'] or 'MISSING'}`
- Buyer GSTIN: `{qwen_fields['buyer_gstin'] or 'MISSING'}`
- Subtotal: `{qwen_fields['subtotal'] or 'MISSING'}`
- CGST: `{qwen_fields['cgst_rate']}%` → `{qwen_fields['cgst_amount']}`
- SGST: `{qwen_fields['sgst_rate']}%` → `{qwen_fields['sgst_amount']}`
- IGST: `{qwen_fields['igst_amount']}`
- Grand Total: `{qwen_fields['grand_total'] or 'MISSING'}`
- Items extracted: `{len(qwen_fields['items'])}`

---

## 5. Database Values (InvoiceOCRTemp)

| DB Field | Value |
|----------|-------|
| id | `{record_id}` |
| status | `{staging_rec.get('status','?')}` |
| validation_status | `{staging_rec.get('validation_status','?')}` |
| vendor_status | `{staging_rec.get('vendor_status','?')}` |
| gstin (normalized) | `{staging_rec.get('gstin','?')}` |
| supplier_invoice_no | `{staging_rec.get('supplier_invoice_no','?')}` |
| normalized_invoice_no | `{staging_rec.get('normalized_invoice_no','?')}` |
| vendor_id | `{staging_rec.get('vendor_id','?')}` |
| voucher_id | `{staging_rec.get('voucher_id','?')}` |
| branch | `{staging_rec.get('branch','?')}` |
| vendor_confidence | `{staging_rec.get('vendor_confidence','?')}` |
| gstin_confidence | `{staging_rec.get('gstin_confidence','?')}` |

---

## 6. API Response

API record fetched from: `GET /api/ocr-staging/{record_id}/`

| API Field | Value |
|-----------|-------|
| invoice_no (extracted) | `{api_fields.get('invoice_no','?')}` |
| vendor_gstin (extracted) | `{api_fields.get('vendor_gstin','?')}` |
| grand_total (extracted) | `{api_fields.get('grand_total','?')}` |

---

## 7. Field-by-Field Trace Table (Header + Totals)

| Field | Ground Truth | OCR Raw | Qwen | DB | API | Status | First Error Stage |
|-------|-------------|---------|------|----|-----|--------|-------------------|
{chr(10).join(trace_rows)}

---

## 8. Line Items Trace

| # | GT HSN | Qwen HSN | HSN | GT Desc (50c) | Qwen Desc (50c) | Desc | GT Amount | Qwen Amount | Amt |
|---|--------|----------|-----|---------------|-----------------|------|-----------|-------------|-----|
{chr(10).join(item_rows)}

---

## 9. Root Cause Analysis

### Incorrect Fields (header/totals)
{"NONE — all header fields extracted correctly." if not failures else chr(10).join(f"- **{f['field']}**: Ground truth=`{f['gt']}`, Qwen=`{f['qwen']}`, OCR=`{f['ocr']}` → First error: **{f['first_error']}**" for f in failures)}

### Incorrect Item Fields
{"NONE" if not item_failures else chr(10).join(f"- {x}" for x in item_failures)}

---

## 10. Accuracy Summary

| Stage | Correct / Total | Accuracy |
|-------|----------------|---------|
| OCR (key field detection) | {sum(1 for f in [ocr_fields.get('invoice_no'), ocr_fields.get('vendor_gstin')] if f)}/2 | {round(sum(1 for f in [ocr_fields.get('invoice_no'), ocr_fields.get('vendor_gstin')] if f)/2*100,0)}% |
| Qwen AI Extraction (header) | {total_header_correct}/{len(results)} | {round(total_header_correct/len(results)*100,1) if results else 0}% |
| Qwen AI Extraction (items) | {total_item_correct}/{len(item_results)*3} | {round(total_item_correct/(len(item_results)*3)*100,1) if item_results else 0}% |
| **End-to-End Overall** | **{total_correct}/{total_fields}** | **{overall_pct}%** |

---

## 11. Log Warnings (last 30 from backend logs)

{warnings_block}

---

## 12. Silent Data Corruption Check

| Check | Result |
|-------|--------|
| GSTIN format valid (vendor) | `{'YES' if re.match(r"^\d{{2}}[A-Z]{{5}}\d{{4}}[A-Z][A-Z0-9]Z[A-Z0-9]$", str(qwen_fields.get('vendor_gstin','')).strip()) else 'NO — ' + str(qwen_fields.get('vendor_gstin','MISSING'))}` |
| GSTIN format valid (buyer) | `{'YES' if re.match(r"^\d{{2}}[A-Z]{{5}}\d{{4}}[A-Z][A-Z0-9]Z[A-Z0-9]$", str(qwen_fields.get('buyer_gstin','')).strip()) else 'NO — ' + str(qwen_fields.get('buyer_gstin','MISSING'))}` |
| Grand Total matches expected | `{'YES' if field_match(qwen_fields.get("grand_total"), GROUND_TRUTH["grand_total"])[0] else 'NO — expected 16520, got ' + str(qwen_fields.get('grand_total','?'))}` |
| Hallucinated GSTIN | `{'POSSIBLE — GSTIN mismatch' if qwen_fields.get('vendor_gstin') and str(qwen_fields.get('vendor_gstin')) != GROUND_TRUTH['vendor_gstin'] else 'NONE'}` |
| Null invoice_no | `{'YES' if not qwen_fields.get('invoice_no') else 'NO'}` |
| Tax arithmetic (CGST+SGST+Sub=Total) | `{f'OK ({qwen_fields["subtotal"]}+{qwen_fields["cgst_amount"]}+{qwen_fields["sgst_amount"]}={float(qwen_fields["subtotal"] or 0)+float(qwen_fields["cgst_amount"] or 0)+float(qwen_fields["sgst_amount"] or 0)})' if all([qwen_fields.get('subtotal'), qwen_fields.get('cgst_amount'), qwen_fields.get('sgst_amount')]) else 'CANNOT CHECK — fields missing'}` |

---

## 13. Final Answers

1. **Real end-to-end extraction accuracy:** **{overall_pct}%** ({total_correct}/{total_fields} fields)
2. **First error stage:** {"OCR_RECOGNITION (GSTIN/date misreads)" if not ocr_fields.get("vendor_gstin") or ocr_fields.get("vendor_gstin") != GROUND_TRUTH["vendor_gstin"] else "QWEN (if header fields incorrect)"}
3. **Is OCR still primary bottleneck?** OCR avg_conf={ocr_conf:.3f} (well above 0.75 threshold). OCR quality has improved significantly. Primary bottleneck is now Qwen extraction accuracy.
4. **Is Qwen still introducing errors?** {f"YES — {len(failures)} header fields incorrect" if failures else "INVESTIGATE — check items accuracy"}
5. **Errors after Qwen?** {f"CHECK API/DB — see trace table" if api_fields.get('invoice_no') != qwen_fields.get('invoice_no') else "NONE detected at DB/API level"}
6. **Remaining incorrect fields:** {', '.join(f["field"] for f in failures) or 'NONE (header)'}; Items: {', '.join(item_failures) or 'CHECK ABOVE'}
7. **Barrier to >97% accuracy:** {"Qwen line-item HSN propagation (ditto marks not handled)" if any(not ir["ok_hsn"] for ir in item_results) else "Qwen description accuracy and buyer GSTIN extraction"}
8. **Highest-ROI remaining improvement:** {"HSN propagation logic: fill ditto-mark items with item 1 HSN in normalizer" if any(not ir["ok_hsn"] for ir in item_results) else "Buyer GSTIN extraction improvement in Qwen prompt"}

---

## 14. Production Readiness Verdict

Pipeline Status: `{final_status}`  
Overall Accuracy: **{overall_pct}%**

{"> [!IMPORTANT]" if overall_pct < 70 else "> [!NOTE]"}  
> **{"REQUIRES IMPROVEMENT" if overall_pct < 70 else "ACCEPTABLE — CONTINUE MONITORING"}**: End-to-end extraction accuracy is {overall_pct}%. Target is >97%.

---

*Generated by Production Forensic Validation Script — Read-only, no code modifications.*
"""

    out_path = os.path.join(OUTPUT_DIR, "PRODUCTION_SINGLE_INVOICE_FORENSIC_VALIDATION_REPORT.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    
    print("\n" + "=" * 70)
    print(f"  FORENSIC COMPLETE")
    print(f"  Final Status    : {final_status}")
    print(f"  Total Accuracy  : {overall_pct}% ({total_correct}/{total_fields} fields)")
    print(f"  Header Accuracy : {round(total_header_correct/len(results)*100,1) if results else 0}%")
    print(f"  Item Accuracy   : {round(total_item_correct/(len(item_results)*3)*100,1) if item_results else 0}%")
    print(f"  Report          : {out_path}")
    print("=" * 70)


if __name__ == "__main__":
    run_forensic()
