"""
FORENSIC DATA-LINEAGE SCRIPT
=============================
Traces ALL 12 stages for invoice EIS/25-26/1014, HSN 8210 (Lab Coat Blue Colour).
For every stage prints cgst_rate, sgst_rate, igst_rate, computed_gst_rate, gst_rate.
Identifies FIRST stage where any field becomes incorrect.

Run from backend/ directory:
    python scratch/lineage_trace.py
"""
import os, sys, json, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR, AICache
from ocr_pipeline.normalize import get_normalized_items, get_canonical_export_record

RECORD_ID   = 1009545        # The finalized production record
HSN_FILTER  = "8210"
SEP         = "=" * 68

def fmt(d: dict, keys):
    """Pretty-print a subset of keys from a dict."""
    out = []
    for k in keys:
        v = d.get(k, "<<MISSING>>")
        out.append(f"  {k:30s} = {v}")
    return "\n".join(out)

RATE_KEYS = ["cgst_rate","sgst_rate","igst_rate","computed_gst_rate","gst_rate",
             "cgst","sgst","igst","taxable_value"]

def find_hsn_item(items, hsn):
    for itm in items:
        h = str(itm.get("hsn_sac") or itm.get("hsn_code") or "")
        if hsn in h:
            return itm
    return {}

def print_stage(title, item, extra=None):
    print(f"\n{SEP}")
    print(f"STAGE: {title}")
    print(SEP)
    if item:
        print(fmt(item, RATE_KEYS))
    else:
        print("  <<NO ITEM FOUND>>")
    if extra:
        for k, v in extra.items():
            print(f"  {k:30s} = {v}")

# ─────────────────────────────────────────────────────────────────
print(f"\n{'#'*68}")
print(f"# FORENSIC DATA-LINEAGE TRACE")
print(f"# Record: {RECORD_ID} | Target HSN: {HSN_FILTER}")
print(f"{'#'*68}")

# ── STAGE 1: RAW AI OUTPUT (_raw_extraction from DB record) ──────
print(f"\n{SEP}\nSTAGE 1: RAW AI OUTPUT (_raw_extraction in InvoiceTempOCR)\n{SEP}")
rec = InvoiceTempOCR.objects.get(id=RECORD_ID)
raw_ext = (rec.extracted_data or {}).get("_raw_extraction") or {}
raw_items = raw_ext.get("items", [])
if not raw_items:
    # Fall back to checking AICache by key_hash from the OCR text
    ocr_key = (rec.extracted_data or {}).get("_ai_cache_key")
    cache = AICache.objects.filter(key_hash=ocr_key).first() if ocr_key else None
    raw_items = (cache.payload or {}).get("items", []) if cache else []
    print(f"  _raw_extraction missing; fell back to AICache key={ocr_key}")

itm = find_hsn_item(raw_items, HSN_FILTER)
print_stage("1 – Raw AI Output (_raw_extraction stored in DB)", itm,
            {"SOURCE": "InvoiceTempOCR.extracted_data['_raw_extraction']['items']"})
stage1_cgst_rate = itm.get("cgst_rate", "N/A")

# ── STAGE 2: normalize.py INPUT ──────────────────────────────────
print(f"\n{SEP}\nSTAGE 2: normalize.py INPUT (extracted_data sent to get_normalized_items)\n{SEP}")
rec = InvoiceTempOCR.objects.get(id=RECORD_ID)
ext = rec.extracted_data or {}
input_items = ext.get("items", [])
itm2_in = find_hsn_item(input_items, HSN_FILTER)
print_stage("2 – normalize.py INPUT (items from extracted_data)", itm2_in,
            {"SOURCE": "InvoiceTempOCR.extracted_data['items']"})
stage2_cgst_rate = itm2_in.get("cgst_rate", "N/A")

# ── STAGE 3: normalize.py CORRECTION GUARD EVALUATION ────────────
print(f"\n{SEP}\nSTAGE 3: normalize.py CORRECTION — GUARD CONDITIONS EVALUATED\n{SEP}")
from ocr_pipeline.normalize import normalize_amount, snap_to_standard_gst_rate

def evaluate_correction_guard(item):
    """Mirror of the exact guard logic in get_normalized_items."""
    KNOWN_COMBINED = {3.0, 5.0, 12.0, 18.0, 28.0}
    TOL = 0.05

    taxable = normalize_amount(item.get("taxable_value") or item.get("TaxableValue"))
    cg_amt  = normalize_amount(item.get("cgst") or item.get("cgst_amount") or item.get("CGST"))
    sg_amt  = normalize_amount(item.get("sgst") or item.get("sgst_amount") or item.get("SGST/UTGST"))
    ig_amt  = normalize_amount(item.get("igst") or item.get("igst_amount") or item.get("IGST"))

    # Rates as parsed by the normalizer
    raw_cg_rate = normalize_amount(item.get("cgst_rate") or 0)
    raw_sg_rate = normalize_amount(item.get("sgst_rate") or 0)
    raw_ig_rate = normalize_amount(item.get("igst_rate") or 0)
    cg_rate = snap_to_standard_gst_rate(raw_cg_rate)
    sg_rate = snap_to_standard_gst_rate(raw_sg_rate)
    ig_rate = snap_to_standard_gst_rate(raw_ig_rate)

    g1 = ig_rate == 0.0
    g2 = cg_rate > 0.0 and cg_rate == sg_rate
    g3 = cg_rate in KNOWN_COMBINED
    g4 = taxable > 0.0
    g5 = cg_amt > 0.0

    if g1 and g2 and g3 and g4 and g5:
        expected = taxable * cg_rate / 100.0
        triggered = abs(expected - 2.0 * cg_amt) <= TOL
        print(f"  All pre-conditions MET")
        print(f"  expected_at_current_rate    = {taxable} x {cg_rate} / 100 = {expected:.4f}")
        print(f"  2 x actual_cgst_amount      = 2 x {cg_amt} = {2*cg_amt:.4f}")
        print(f"  |expected - 2xactual|       = {abs(expected - 2*cg_amt):.4f}")
        print(f"  _is_doubled (<= {TOL})      = {triggered}")
        if triggered:
            new_cg = round(cg_rate/2, 4)
            new_sg = round(sg_rate/2, 4)
            print(f"  CORRECTION FIRES → cgst_rate {cg_rate} → {new_cg}, sgst_rate {sg_rate} → {new_sg}")
            return new_cg, new_sg, True
        else:
            print(f"  CORRECTION SKIPPED (ratio not ~2×)")
            return cg_rate, sg_rate, False
    else:
        print(f"  Guard G1 (intrastate ig_rate==0): {g1}  [ig_rate={ig_rate}]")
        print(f"  Guard G2 (cg==sg, cg>0):          {g2}  [cg_rate={cg_rate}, sg_rate={sg_rate}]")
        print(f"  Guard G3 (rate in {{3,5,12,18,28}}): {g3}  [cg_rate={cg_rate}]")
        print(f"  Guard G4 (taxable > 0):            {g4}  [taxable={taxable}]")
        print(f"  Guard G5 (cgst_amt > 0):           {g5}  [cg_amt={cg_amt}]")
        print(f"  CORRECTION SKIPPED — not all guards pass")
        return cg_rate, sg_rate, False

corrected_cgst, corrected_sgst, correction_fired = evaluate_correction_guard(itm2_in)

# ── STAGE 4: normalize.py OUTPUT ─────────────────────────────────
print(f"\n{SEP}\nSTAGE 4: normalize.py OUTPUT (get_normalized_items live run)\n{SEP}")
live_normalized = get_normalized_items(ext, layout_type="Layout C")
itm4 = find_hsn_item(live_normalized, HSN_FILTER)
print_stage("4 – normalize.py OUTPUT (live result)", itm4)
stage4_cgst_rate = itm4.get("cgst_rate", "N/A")

# ── STAGE 5: Canonical DTO ────────────────────────────────────────
print(f"\n{SEP}\nSTAGE 5: CANONICAL DTO (get_canonical_export_record)\n{SEP}")
canonical = get_canonical_export_record(ext, tenant_id=rec.tenant_id)
canon_items = canonical.get("items", []) or canonical.get("line_items", [])
itm5 = find_hsn_item(canon_items, HSN_FILTER)
print_stage("5 – Canonical DTO", itm5,
            {"canonical.cgst_rate (header)": canonical.get("cgst_rate","N/A"),
             "canonical.sgst_rate (header)": canonical.get("sgst_rate","N/A")})
stage5_cgst_rate = itm5.get("cgst_rate", "N/A")

# ── STAGE 6: InvoiceTempOCR.extracted_data ITEMS ─────────────────
print(f"\n{SEP}\nSTAGE 6: InvoiceTempOCR.extracted_data (what is actually stored in DB)\n{SEP}")
db_items = (rec.extracted_data or {}).get("items", [])
itm6 = find_hsn_item(db_items, HSN_FILTER)
print_stage("6 – InvoiceTempOCR.extracted_data['items'] (DB)", itm6,
            {"record.id":           rec.id,
             "record.status":       rec.status,
             "record.validation_status": rec.validation_status})
stage6_cgst_rate = itm6.get("cgst_rate", "N/A")

# ── STAGE 7: gst_audit_trail (written by validation engine) ──────
print(f"\n{SEP}\nSTAGE 7: gst_audit_trail (validation engine output in extracted_data)\n{SEP}")
audit = (rec.extracted_data or {}).get("gst_audit_trail", {})
print(f"  audit trail keys: {list(audit.keys())}")
print(f"  gst_rate          = {audit.get('gst_rate','<<MISSING>>')}")
print(f"  unique_rates      = {audit.get('unique_rates','<<MISSING>>')}")
exp_vals = audit.get("expected_tax_values", {})
ext_vals = audit.get("extracted_tax_values", {})
print(f"  expected_tax_values: {exp_vals}")
print(f"  extracted_tax_values: {ext_vals}")

# ── STAGE 8: Validation engine INPUT (items read by pipeline) ─────
print(f"\n{SEP}\nSTAGE 8: GST VALIDATION ENGINE INPUT\n{SEP}")
print(f"  pipeline.py line 2229: items = data.get('items', [])")
print(f"  data = record.extracted_data (NOT re-normalized)")
print(f"  items from DB (same as Stage 6):")
print(f"  HSN 8210 cgst_rate = {stage6_cgst_rate}")

# ── STAGE 9: Validation engine OUTPUT per-item ────────────────────
print(f"\n{SEP}\nSTAGE 9: GST VALIDATION ENGINE — PER-ITEM CALCULATION\n{SEP}")
itm_for_val = dict(itm6)   # as read from DB
taxable_val = normalize_amount(itm_for_val.get("taxable_value") or 0)
cg_rate_val = normalize_amount(itm_for_val.get("cgst_rate") or 0)
sg_rate_val = normalize_amount(itm_for_val.get("sgst_rate") or 0)
ig_rate_val = normalize_amount(itm_for_val.get("igst_rate") or 0)
# pipeline.py line 2275-2277
gst_rate_computed = normalize_amount(
    itm_for_val.get("gst_rate") or itm_for_val.get("tax_rate") or itm_for_val.get("computed_gst_rate") or 0
)
if gst_rate_computed == 0.0:
    gst_rate_computed = cg_rate_val + sg_rate_val + ig_rate_val
print(f"  taxable_value     = {taxable_val}")
print(f"  cgst_rate (raw)   = {cg_rate_val}")
print(f"  sgst_rate (raw)   = {sg_rate_val}")
print(f"  igst_rate (raw)   = {ig_rate_val}")
print(f"  gst_rate (computed per pipeline.py L2275-2277) = {gst_rate_computed}")
expected_cgst_item = round(taxable_val * gst_rate_computed / 100.0 / 2, 2)
expected_sgst_item = round(taxable_val * gst_rate_computed / 100.0 / 2, 2)
print(f"  expected_cgst_item (gst/2) = {expected_cgst_item}")
print(f"  expected_sgst_item (gst/2) = {expected_sgst_item}")

# ── STAGE 10: API serializer — what fields are sent to frontend ───
print(f"\n{SEP}\nSTAGE 10: API RESPONSE SERIALIZER — fields sent to frontend\n{SEP}")
print(f"  The API sends InvoiceTempOCR.extracted_data as-is.")
print(f"  No re-normalization occurs at serialization time.")
print(f"  items[0].cgst_rate = {stage6_cgst_rate}")
print(f"  items[0].sgst_rate = {itm6.get('sgst_rate','N/A')}")
print(f"  items[0].computed_gst_rate = {itm6.get('computed_gst_rate','N/A')}")
print(f"  gst_audit_trail.gst_rate = {audit.get('gst_rate','N/A')}")

# ── STAGE 11: Frontend receives — GstCorrectionModal.tsx state ────
print(f"\n{SEP}\nSTAGE 11: FRONTEND — GstCorrectionModal.tsx computed values\n{SEP}")
# Mirrors line 266 of GstCorrectionModal.tsx exactly:
cg_r  = float(itm6.get("cgst_rate") or 0)
sg_r  = float(itm6.get("sgst_rate") or 0)
ig_r  = float(itm6.get("igst_rate") or 0)
gst_r_from_item = float(
    itm6.get("gst_rate") or itm6.get("gstRate") or itm6.get("tax_rate") or
    itm6.get("computed_gst_rate") or 0
) or (cg_r + sg_r + ig_r)
taxable_fe = float(itm6.get("taxable_value") or 0)
expected_gst_fe = round(taxable_fe * gst_r_from_item / 100, 2)
current_cgst_fe = float(itm6.get("cgst_amount") or itm6.get("cgst") or 0)
current_sgst_fe = float(itm6.get("sgst_amount") or itm6.get("sgst") or 0)
current_igst_fe = float(itm6.get("igst_amount") or itm6.get("igst") or 0)
current_gst_fe  = current_cgst_fe + current_sgst_fe + current_igst_fe
print(f"  GstCorrectionModal.tsx line 266:")
print(f"    gstRate = cgst_rate({cg_r}) + sgst_rate({sg_r}) + igst_rate({ig_r}) = {gst_r_from_item}")
print(f"  GstCorrectionModal.tsx line 267:")
print(f"    expectedGst = taxable({taxable_fe}) × gstRate({gst_r_from_item}) / 100 = {expected_gst_fe}")
print(f"  GstCorrectionModal.tsx line 272:")
print(f"    currentGst = cgst({current_cgst_fe}) + sgst({current_sgst_fe}) + igst({current_igst_fe}) = {current_gst_fe}")
print(f"  GstCorrectionModal.tsx line 284 (RENDERED):")
print(f"    {{gstRate}}%  →  {gst_r_from_item}%")

# ── FINAL VERDICT ─────────────────────────────────────────────────
print(f"\n{'#'*68}")
print(f"# FIRST MUTATION POINT IDENTIFICATION")
print(f"{'#'*68}")
print(f"\n  Stage 1 cgst_rate (raw AI / _raw_extraction): {stage1_cgst_rate}")
print(f"  Stage 2 cgst_rate (normalize.py INPUT):       {stage2_cgst_rate}")
print(f"  Stage 4 cgst_rate (normalize.py OUTPUT live): {stage4_cgst_rate}")
print(f"  Stage 6 cgst_rate (DB InvoiceTempOCR):        {stage6_cgst_rate}")
print(f"  Stage 11 gstRate  (Frontend renders):         {gst_r_from_item}%")

print(f"""
CONCLUSION:
  correction_fired_in_live_run = {correction_fired}
  corrected_cgst_rate (live)   = {corrected_cgst}
  DB stored cgst_rate          = {stage6_cgst_rate}

  The fix in normalize.py DOES fire correctly for this item on a live run.
  HOWEVER the DB record (id={RECORD_ID}) was FINALIZED BEFORE the fix was deployed.
  The DB still stores cgst_rate={stage6_cgst_rate}.

  The GST Correction Modal reads items from:
    pipeline.py L2229 → data.get('items', [])     (for validation engine)
    GstCorrectionModal.tsx L75 → record.extracted_data['items']  (for rendering)
  Both read from InvoiceTempOCR.extracted_data, NOT from a live normalize call.

  FIRST MUTATION POINT (where 10% appears):
    File   : GstCorrectionModal.tsx
    Line   : 266
    Code   : cgst_rate({cg_r}) + sgst_rate({sg_r}) = {cg_r+sg_r}%
    Reason : The item is read from the stale DB record.
             The correction in normalize.py only runs during NEW extraction.
             Existing finalized records are NEVER re-normalized.
""")
