"""
Phase 0 — Data Lineage Investigation Script
============================================
Traces the failing invoice IMG_20260406_0003.pdf through every pipeline stage
and produces a comparison table of GST values at each stage.

FIELDS TRACED:
  - Taxable Value
  - CGST
  - SGST
  - IGST
  - CESS
  - Discount
  - Round Off
  - Subtotal
  - Grand Total / Invoice Total

STAGES:
  OCR Output -> AI Raw JSON -> Normalized DTO -> Canonical DTO ->
  invoice_temp_ocr DB record -> Validation DTO -> Finalize DTO ->
  Voucher DTO -> GST Validation Input -> Voucher Insert Payload

Usage:
  python manage.py shell < scratch/data_lineage_probe.py
  -- or --
  cd backend && python scratch/data_lineage_probe.py
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

import json
from decimal import Decimal

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
TARGET_PDF_NAME = "IMG_20260406_0003.pdf"
# The invoice number from the PDF — update if known
KNOWN_INVOICE_NO = None  # e.g. "4742/25-26" — leave None to auto-detect

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def to_float(val):
    if val is None:
        return 0.0
    try:
        clean = str(val).replace('₹', '').replace(',', '').replace(' ', '').strip()
        return float(clean) if clean else 0.0
    except Exception:
        return 0.0


def snapshot(label, data):
    """Print a structured snapshot row."""
    print(f"\n{'='*80}")
    print(f"STAGE: {label}")
    print(f"{'='*80}")
    fields = [
        ('taxable_value',   data.get('taxable_value')),
        ('cgst',            data.get('cgst')),
        ('sgst',            data.get('sgst')),
        ('igst',            data.get('igst')),
        ('cess',            data.get('cess')),
        ('discount',        data.get('discount')),
        ('round_off',       data.get('round_off')),
        ('subtotal',        data.get('subtotal')),
        ('invoice_total',   data.get('invoice_total')),
        ('grand_total',     data.get('grand_total')),
    ]
    for name, value in fields:
        print(f"  {name:<20}: {value!r}")
    raw = data.get('_raw')
    if raw:
        print(f"\n  [RAW SOURCE KEYS]: {list(raw.keys()) if isinstance(raw, dict) else type(raw)}")
    return {k: to_float(v) for k, v in fields}


def extract_supply_fields(supply_dict, record_data=None):
    """Extract supply-level totals from a supply_details dict or flat record data."""
    rd = record_data or {}
    s = supply_dict or {}
    return {
        'taxable_value': (
            to_float(s.get('total_taxable_value') or s.get('taxable_value')) or
            to_float(rd.get('total_taxable_value') or rd.get('taxable_value'))
        ),
        'cgst': (
            to_float(s.get('total_cgst') or s.get('cgst')) or
            to_float(rd.get('total_cgst') or rd.get('cgst'))
        ),
        'sgst': (
            to_float(s.get('total_sgst') or s.get('sgst')) or
            to_float(rd.get('total_sgst') or rd.get('sgst'))
        ),
        'igst': (
            to_float(s.get('total_igst') or s.get('igst')) or
            to_float(rd.get('total_igst') or rd.get('igst'))
        ),
        'cess': (
            to_float(s.get('total_cess') or s.get('cess')) or
            to_float(rd.get('total_cess') or rd.get('cess'))
        ),
        'discount': to_float(s.get('discount') or rd.get('discount')),
        'round_off': to_float(s.get('round_off') or rd.get('round_off')),
        'subtotal': to_float(s.get('subtotal') or rd.get('subtotal')),
        'invoice_total': (
            to_float(s.get('total_invoice_value') or s.get('invoice_total')) or
            to_float(rd.get('total_invoice_value') or rd.get('invoice_total') or rd.get('total_amount'))
        ),
        'grand_total': to_float(s.get('grand_total') or rd.get('grand_total')),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Find the most recent InvoiceTempOCR record for this PDF
# ─────────────────────────────────────────────────────────────────────────────
from ocr_pipeline.models import InvoiceTempOCR

print(f"\n{'#'*80}")
print(f"# Phase 0 — Data Lineage Investigation")
print(f"# Target: {TARGET_PDF_NAME}")
print(f"{'#'*80}")

# Search by file path pattern
qs = InvoiceTempOCR.objects.filter(
    file_path__icontains=TARGET_PDF_NAME
).order_by('-created_at')

if not qs.exists():
    # Try by invoice number if known
    if KNOWN_INVOICE_NO:
        qs = InvoiceTempOCR.objects.filter(
            supplier_invoice_no__iexact=KNOWN_INVOICE_NO
        ).order_by('-created_at')

if not qs.exists():
    print(f"\n[ERROR] No InvoiceTempOCR record found for {TARGET_PDF_NAME}")
    print("Available records (last 10):")
    for r in InvoiceTempOCR.objects.order_by('-created_at')[:10]:
        print(f"  id={r.id} inv={r.supplier_invoice_no} status={r.status} file={r.file_path}")
    sys.exit(1)

record = qs.first()
print(f"\n[FOUND] InvoiceTempOCR id={record.id}")
print(f"  supplier_invoice_no : {record.supplier_invoice_no}")
print(f"  gstin               : {record.gstin}")
print(f"  status              : {record.status}")
print(f"  validation_status   : {record.validation_status}")
print(f"  processed           : {record.processed}")
print(f"  tenant_id           : {record.tenant_id}")
print(f"  upload_session_id   : {record.upload_session_id}")
print(f"  file_path           : {record.file_path}")
print(f"  created_at          : {record.created_at}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Stage snapshots
# ─────────────────────────────────────────────────────────────────────────────
stages = {}
data = record.extracted_data or {}

# ── Stage: AI Raw JSON ──────────────────────────────────────────────────────
# The raw AI output is what was directly stored before normalization
# Look for the root-level values
ai_raw = {
    'taxable_value': data.get('total_taxable_value') or data.get('taxable_value'),
    'cgst':          data.get('total_cgst') or data.get('cgst'),
    'sgst':          data.get('total_sgst') or data.get('sgst'),
    'igst':          data.get('total_igst') or data.get('igst'),
    'cess':          data.get('total_cess') or data.get('cess'),
    'discount':      data.get('discount'),
    'round_off':     data.get('round_off'),
    'subtotal':      data.get('subtotal'),
    'invoice_total': data.get('invoice_total') or data.get('total_invoice_value') or data.get('total_amount'),
    'grand_total':   data.get('grand_total'),
    '_raw':          data,
}
stages['AI_RAW_JSON'] = snapshot("Stage 1 — AI Raw JSON (extracted_data root)", ai_raw)

# ── Stage: Sections (Normalized) ────────────────────────────────────────────
sections = data.get('sections') or {}
supply_details = sections.get('supply_details') or {}
supplier_details = sections.get('supplier_details') or {}

norm_fields = extract_supply_fields(supply_details, data)
norm_fields['_raw'] = supply_details
stages['NORMALIZED_DTO'] = snapshot("Stage 2 — Normalized DTO (sections.supply_details)", norm_fields)

# ── Stage: Assembled Exports (Canonical DTO) ─────────────────────────────────
assembled = data.get('assembled_exports') or data.get('_pages_assembled') or []
if assembled and isinstance(assembled, list) and assembled:
    ae = assembled[0]
    ae_supply = (ae.get('sections') or {}).get('supply_details') or {}
    ae_fields = extract_supply_fields(ae_supply, ae)
    ae_fields['_raw'] = ae
    stages['CANONICAL_DTO'] = snapshot("Stage 3 — Canonical DTO (assembled_exports[0])", ae_fields)
else:
    print("\nSTAGE: Stage 3 — Canonical DTO\n  [SKIP] No assembled_exports found")
    stages['CANONICAL_DTO'] = stages['NORMALIZED_DTO'].copy()

# ── Stage: DB Record (Flat Fields) ──────────────────────────────────────────
db_fields = {
    'taxable_value': getattr(record, 'total_taxable_value', None) or ai_raw.get('taxable_value'),
    'cgst':          ai_raw['cgst'],    # No flat CGST on model — use extracted_data
    'sgst':          ai_raw['sgst'],
    'igst':          ai_raw['igst'],
    'cess':          ai_raw['cess'],
    'discount':      ai_raw['discount'],
    'round_off':     ai_raw['round_off'],
    'subtotal':      ai_raw['subtotal'],
    'invoice_total': getattr(record, 'total_amount', None) or ai_raw['invoice_total'],
    'grand_total':   ai_raw['grand_total'],
}
stages['DATABASE'] = snapshot("Stage 4 — Database (InvoiceTempOCR flat fields)", db_fields)

# ── Stage: GST Audit Trail (if already validated) ───────────────────────────
gst_audit = data.get('gst_audit_trail') or {}
if gst_audit:
    expected = gst_audit.get('expected_tax_values') or {}
    extracted = gst_audit.get('extracted_tax_values') or {}
    print(f"\n{'='*80}")
    print("STAGE: Stage 5 — GST Audit Trail (already in DB)")
    print(f"{'='*80}")
    print(f"\n  GST Validation Status: {gst_audit.get('validation_status')}")
    print(f"  Taxable Value       : {gst_audit.get('taxable_value')}")
    print(f"  Difference Amount   : {gst_audit.get('difference_amount')}")
    print(f"  Resolution Choice   : {gst_audit.get('resolution_choice')}")
    print(f"  GST Rate            : {gst_audit.get('gst_rate')}")
    print(f"\n  EXPECTED (computed from items):")
    for k, v in expected.items():
        print(f"    {k:<20}: {v}")
    print(f"\n  EXTRACTED (from AI output):")
    for k, v in extracted.items():
        print(f"    {k:<20}: {v}")
    stages['GST_AUDIT_TRAIL'] = {
        'cgst': to_float(expected.get('cgst')),
        'sgst': to_float(expected.get('sgst')),
        'igst': to_float(expected.get('igst')),
        'cess': to_float(expected.get('cess')),
        'taxable_value': to_float(gst_audit.get('taxable_value')),
        'invoice_total': to_float(expected.get('total')),
    }
else:
    print("\nSTAGE: Stage 5 — GST Audit Trail\n  [SKIP] No gst_audit_trail in extracted_data")

# ── Stage: Per-Item Breakdown ────────────────────────────────────────────────
items = data.get('items') or []
if not items and assembled:
    items = (assembled[0] or {}).get('items') or []

if items:
    print(f"\n{'='*80}")
    print(f"STAGE: Item-Level Tax Breakdown ({len(items)} items)")
    print(f"{'='*80}")
    sum_taxable = 0.0
    sum_cgst = 0.0
    sum_sgst = 0.0
    sum_igst = 0.0
    sum_cess = 0.0
    for i, item in enumerate(items):
        tx = to_float(item.get('taxable_value') or item.get('taxable'))
        cg = to_float(item.get('cgst_amount') or item.get('cgst'))
        sg = to_float(item.get('sgst_amount') or item.get('sgst'))
        ig = to_float(item.get('igst_amount') or item.get('igst'))
        cs = to_float(item.get('cess_amount') or item.get('cess'))
        rate = to_float(item.get('gst_rate') or item.get('tax_rate'))
        desc = str(item.get('description') or item.get('item_name') or '')[:40]
        print(f"  Item {i+1:02d}: {desc!r:<42} | taxable={tx:8.2f} | gst_rate={rate}% | "
              f"cgst={cg:7.2f} | sgst={sg:7.2f} | igst={ig:7.2f} | cess={cs:5.2f}")
        sum_taxable += tx
        sum_cgst += cg
        sum_sgst += sg
        sum_igst += ig
        sum_cess += cs
    print(f"  {'ITEM SUM':<46} | taxable={sum_taxable:8.2f} | {'':9} | "
          f"cgst={sum_cgst:7.2f} | sgst={sum_sgst:7.2f} | igst={sum_igst:7.2f} | cess={sum_cess:5.2f}")
    stages['ITEM_SUMS'] = {
        'taxable_value': sum_taxable,
        'cgst': sum_cgst,
        'sgst': sum_sgst,
        'igst': sum_igst,
        'cess': sum_cess,
    }

# ── Stage: Voucher Record (if already created) ───────────────────────────────
if record.voucher_id:
    try:
        from accounting.models import Voucher, VoucherItem
        voucher = Voucher.objects.filter(id=record.voucher_id).first()
        if voucher:
            print(f"\n{'='*80}")
            print(f"STAGE: Stage 6 — Created Voucher (id={voucher.id})")
            print(f"{'='*80}")
            print(f"  voucher_number    : {getattr(voucher, 'voucher_number', 'N/A')}")
            print(f"  total_amount      : {getattr(voucher, 'total_amount', 'N/A')}")
            print(f"  narration         : {str(getattr(voucher, 'narration', ''))[:100]}")
    except Exception as e:
        print(f"\n  [VOUCHER LOOKUP ERROR] {e}")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Comparison Table
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n\n{'#'*80}")
print("# COMPARISON TABLE — GST Values at Each Stage")
print(f"{'#'*80}")
print(f"\n{'Stage':<22} {'Taxable':>10} {'CGST':>10} {'SGST':>10} {'IGST':>10} {'CESS':>8} {'InvTotal':>12}")
print(f"{'-'*84}")

stage_labels = {
    'AI_RAW_JSON':    'AI Raw JSON',
    'NORMALIZED_DTO': 'Normalized DTO',
    'CANONICAL_DTO':  'Canonical DTO',
    'DATABASE':       'DB Record',
    'ITEM_SUMS':      'Item Sums',
    'GST_AUDIT_TRAIL':'GST Audit Trail',
}

prev = None
first_diff_stage = None
first_diff_field = None

for key, label in stage_labels.items():
    if key not in stages:
        continue
    s = stages[key]
    tv  = s.get('taxable_value', 0.0)
    cg  = s.get('cgst', 0.0)
    sg  = s.get('sgst', 0.0)
    ig  = s.get('igst', 0.0)
    cs  = s.get('cess', 0.0)
    it  = s.get('invoice_total', 0.0)
    print(f"  {label:<20} {tv:>10.2f} {cg:>10.2f} {sg:>10.2f} {ig:>10.2f} {cs:>8.2f} {it:>12.2f}")

    if prev and not first_diff_stage:
        for field in ('taxable_value', 'cgst', 'sgst', 'igst', 'cess', 'invoice_total'):
            if abs(s.get(field, 0.0) - prev.get(field, 0.0)) > 0.01:
                first_diff_stage = label
                first_diff_field = field
                break
    prev = s

print(f"\n{'─'*84}")
if first_diff_stage:
    print(f"\n  ⚠️  FIRST VALUE CHANGE DETECTED AT STAGE: {first_diff_stage}")
    print(f"     FIELD THAT CHANGED: {first_diff_field}")
    print(f"\n  → CONCLUSION: Investigate the transformation AT OR BEFORE '{first_diff_stage}'.")
    print(f"    Do NOT modify the GST engine until this upstream change is diagnosed.\n")
else:
    print(f"\n  ✅ Values are consistent across all traced stages.")
    print(f"    If a mismatch occurs, it happens INSIDE the GST Validation Engine itself.\n")

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: calculate_item_taxable_value investigation
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'#'*80}")
print("# Item-Level calculate_item_taxable_value Trace")
print(f"{'#'*80}")
if items:
    from ocr_pipeline.normalize import calculate_item_taxable_value
    for i, item in enumerate(items[:5]):  # Limit to first 5 items
        tx_computed = calculate_item_taxable_value(item)
        tx_stored   = to_float(item.get('taxable_value') or item.get('taxable'))
        match = "✅ MATCH" if abs(tx_computed - tx_stored) < 0.01 else f"⚠️  DIFF stored={tx_stored:.2f} computed={tx_computed:.2f}"
        desc = str(item.get('description') or item.get('item_name') or '')[:40]
        print(f"  Item {i+1}: {desc!r:<42} | stored={tx_stored:8.2f} | computed={tx_computed:8.2f} | {match}")
else:
    print("  [SKIP] No items found in extracted_data")

print(f"\n\n{'#'*80}")
print("# END OF DATA LINEAGE INVESTIGATION")
print(f"{'#'*80}\n")
