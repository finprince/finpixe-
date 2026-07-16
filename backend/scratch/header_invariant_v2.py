"""
FORENSIC INVESTIGATION v2: Header Invariant Analysis
=====================================================
Removes category filter. Analyzes ALL statuses.
Identifies Mode B (ratio~2.0) vs healthy (ratio~1.0) invoices.
Checks both FINALIZED and PROCESSING/VALID records.

Run from backend/ directory:
    python scratch/header_invariant_v2.py
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

SEP  = "-" * 72
BSEP = "=" * 72

def to_f(v):
    try:
        if v is None or str(v).strip() == "": return 0.0
        return float(str(v).replace(",","").replace("Rs","").replace("INR","").strip())
    except Exception:
        return 0.0

def analyze(rec):
    ext   = rec.extracted_data or {}
    items = ext.get("items", [])
    if not items:
        return None

    h_taxable = to_f(ext.get("total_taxable_value"))
    h_cgst    = to_f(ext.get("total_cgst"))
    h_sgst    = to_f(ext.get("total_sgst"))
    h_igst    = to_f(ext.get("total_igst"))

    if h_cgst == 0.0 and h_sgst == 0.0 and h_igst == 0.0:
        return None

    sum_cgst = sum(to_f(i.get("cgst") or i.get("cgst_amount")) for i in items)
    sum_sgst = sum(to_f(i.get("sgst") or i.get("sgst_amount")) for i in items)
    sum_igst = sum(to_f(i.get("igst") or i.get("igst_amount")) for i in items)
    sum_taxable = sum(to_f(i.get("taxable_value")) for i in items)

    cgst_ratio = round(sum_cgst / h_cgst, 4) if h_cgst > 0 else None
    sgst_ratio = round(sum_sgst / h_sgst, 4) if h_sgst > 0 else None
    igst_ratio = round(sum_igst / h_igst, 4) if h_igst > 0 else None

    rates = [(to_f(i.get("cgst_rate")), to_f(i.get("sgst_rate")),
              to_f(i.get("igst_rate")), to_f(i.get("taxable_value")),
              to_f(i.get("cgst") or i.get("cgst_amount")))
             for i in items]

    gst_res  = ext.get("gst_resolution")
    frozen   = ext.get("is_canonical_frozen", False)
    h_igst_f = h_igst > 0
    has_igst_item = any(ig > 0 for _, _, ig, _, _ in rates)

    if gst_res in ("CORRECTED", "SUPPLIER_VALUES_ACCEPTED"):
        cat = "CORRECTED"
    elif frozen:
        cat = "FROZEN"
    elif h_igst_f or has_igst_item:
        cat = "IGST"
    else:
        cat = "INTRASTATE"

    return dict(
        record_id    = rec.id,
        invoice_no   = rec.supplier_invoice_no or ext.get("invoice_no") or "?",
        status       = rec.status,
        cat          = cat,
        h_taxable    = h_taxable,
        h_cgst       = h_cgst,
        h_sgst       = h_sgst,
        h_igst       = h_igst,
        sum_cgst     = sum_cgst,
        sum_sgst     = sum_sgst,
        sum_igst     = sum_igst,
        sum_taxable  = sum_taxable,
        cgst_ratio   = cgst_ratio,
        sgst_ratio   = sgst_ratio,
        igst_ratio   = igst_ratio,
        rates        = rates,
        items_count  = len(items),
    )

print(f"\n{BSEP}")
print("FORENSIC HEADER INVARIANT ANALYSIS v2")
print(f"{BSEP}\n")

# Fetch broader set — all statuses, last 500
qs = (InvoiceTempOCR.objects
      .exclude(extracted_data__isnull=True)
      .order_by("-id")[:500])

results, skipped = [], 0
for rec in qs:
    r = analyze(rec)
    if r is None:
        skipped += 1
    else:
        results.append(r)

print(f"Analyzed: {len(results)}  Skipped: {skipped}\n")

# ── Status and category breakdown ─────────────────────────────────────────────

by_cat = {}
for r in results:
    by_cat.setdefault(r["cat"], []).append(r)

print("Category breakdown:")
for cat, recs in sorted(by_cat.items()):
    near2 = sum(1 for r in recs if r["cgst_ratio"] is not None and abs(r["cgst_ratio"]-2.0)<=0.05)
    near1 = sum(1 for r in recs if r["cgst_ratio"] is not None and abs(r["cgst_ratio"]-1.0)<=0.05)
    print(f"  {cat:14s}: {len(recs):3d} records | ratio~1.0: {near1:3d} | ratio~2.0: {near2:3d}")

# ── Detail for corrupted candidates (ratio ~2.0) ──────────────────────────────

print(f"\n{BSEP}")
print("ALL records with cgst_ratio ~2.0 (Mode B corruption candidates)")
print(f"{BSEP}")
print(f"{'RecordID':>9}  {'Invoice No':30}  {'Cat':12}  {'Status':12}  {'h_cgst':>8}  {'sum_cgst':>10}  {'ratio':>8}  Rates")
print(SEP)

mode_b_records = [r for r in results if r["cgst_ratio"] is not None and abs(r["cgst_ratio"]-2.0)<=0.05]
for r in mode_b_records:
    rate_str = ",".join(f"{cg}/{sg}" for cg,sg,_,_,_ in r["rates"])
    print(f"{r['record_id']:>9}  {r['invoice_no']:30}  {r['cat']:12}  {r['status']:12}  "
          f"{r['h_cgst']:>8.2f}  {r['sum_cgst']:>10.2f}  {r['cgst_ratio']:>8.4f}  {rate_str}")

# ── Detail for ratio != 1.0 (non-trivial deviations) ─────────────────────────

print(f"\n{BSEP}")
print("ALL records with cgst_ratio NOT ~1.0 (any anomaly)")
print(f"{BSEP}")
anomalies = [r for r in results
             if r["cgst_ratio"] is not None
             and abs(r["cgst_ratio"]-1.0)>0.06
             and r["h_cgst"] > 0]
anomalies.sort(key=lambda x: x["cgst_ratio"] or 0, reverse=True)
print(f"{'RecordID':>9}  {'Invoice No':30}  {'Cat':12}  {'h_cgst':>8}  {'sum_cgst':>10}  {'ratio':>8}  Rates")
print(SEP)
for r in anomalies[:40]:
    rate_str = ",".join(f"{cg}/{sg}" for cg,sg,_,_,_ in r["rates"])
    print(f"{r['record_id']:>9}  {r['invoice_no']:30}  {r['cat']:12}  "
          f"{r['h_cgst']:>8.2f}  {r['sum_cgst']:>10.2f}  {r['cgst_ratio']:>8.4f}  {rate_str}")

# ── Ratio distribution overall ────────────────────────────────────────────────

print(f"\n{BSEP}")
print("RATIO DISTRIBUTION (all intrastate/mixed records)")
print(f"{BSEP}")

intrastate = [r for r in results if r["cat"] in ("INTRASTATE","MIXED","FROZEN","CORRECTED")]
all_ratios = [r["cgst_ratio"] for r in intrastate if r["cgst_ratio"] is not None]

if all_ratios:
    buckets = {
        "ratio 0.0 (items have 0 cgst)": sum(1 for x in all_ratios if abs(x) < 0.05),
        "ratio 0.5":                      sum(1 for x in all_ratios if abs(x-0.5)<=0.05),
        "ratio 0.9-0.99":                 sum(1 for x in all_ratios if 0.9<=x<0.99),
        "ratio ~1.0 (correct)":           sum(1 for x in all_ratios if abs(x-1.0)<=0.05),
        "ratio 1.01-1.99 (other)":        sum(1 for x in all_ratios if 1.05<x<1.95),
        "ratio ~2.0 (Mode B)":            sum(1 for x in all_ratios if abs(x-2.0)<=0.05),
        "ratio >2.05 (extreme)":          sum(1 for x in all_ratios if x>2.05),
    }
    total = len(all_ratios)
    for label, cnt in buckets.items():
        bar = "#" * min(40, cnt)
        print(f"  {label:38s}: {cnt:4d}/{total}  {bar}")

# ── Per invoice EIS/25-26/1014 deep dive ──────────────────────────────────────

print(f"\n{BSEP}")
print("DEEP DIVE: All records for invoice EIS/25-26/1014")
print(f"{BSEP}")
eis_recs = [r for r in results if "1014" in str(r["invoice_no"])]
for r in eis_recs:
    print(f"\n  id={r['record_id']}  status={r['status']}  cat={r['cat']}")
    print(f"  header:     total_taxable={r['h_taxable']}  total_cgst={r['h_cgst']}  total_sgst={r['h_sgst']}")
    print(f"  item sums:  sum_cgst={r['sum_cgst']}  sum_sgst={r['sum_sgst']}")
    print(f"  ratio:      cgst_ratio={r['cgst_ratio']}  sgst_ratio={r['sgst_ratio']}")
    print(f"  items:")
    for cg, sg, ig, tx, cg_amt in r["rates"]:
        exp_at_half  = round(tx * (cg/2) / 100, 2)
        exp_at_full  = round(tx * cg / 100, 2)
        print(f"    cgst_rate={cg}  sgst_rate={sg}  taxable={tx}  cgst_amount={cg_amt}")
        print(f"      at_current_rate={exp_at_full}  at_half_rate={exp_at_half}  actual_cgst={cg_amt}")
        if abs(exp_at_full - cg_amt) < 0.05:
            print(f"      -> cgst_amount CONSISTENT with rate {cg}% (internal consistent corruption)")
        elif abs(exp_at_half - cg_amt) < 0.05:
            print(f"      -> cgst_amount CONSISTENT with half rate {cg/2}% (Mode A: rate wrong, amount correct)")

# ── Mathematical invariant proof ──────────────────────────────────────────────

print(f"\n{BSEP}")
print("INVARIANT PROOF: Can ratio == 2.0 deterministically identify Mode B?")
print(f"{BSEP}")
print()

all_non_igst = [r for r in results if r["cat"] in ("INTRASTATE","MIXED","FROZEN","CORRECTED")]
ratio2_count  = sum(1 for r in all_non_igst if r["cgst_ratio"] is not None and abs(r["cgst_ratio"]-2.0)<=0.05)
ratio1_count  = sum(1 for r in all_non_igst if r["cgst_ratio"] is not None and abs(r["cgst_ratio"]-1.0)<=0.05)
other_count   = len(all_non_igst) - ratio2_count - ratio1_count

print(f"  Non-IGST records analyzed:          {len(all_non_igst)}")
print(f"  cgst_ratio ~1.0 (normal):           {ratio1_count}")
print(f"  cgst_ratio ~2.0 (Mode B candidate): {ratio2_count}")
print(f"  cgst_ratio other:                   {other_count}")
print()

# For each ratio~2.0 record: is this definitely corrupted or a legitimate invoice?
if mode_b_records:
    print("  Examining ratio~2.0 records:")
    for r in mode_b_records:
        # Check if h_cgst is the ground-truth value (on invoice) and sum_cgst is doubled
        h = r["h_cgst"]
        s = r["sum_cgst"]
        # Implied: if h_cgst = correct CGST = taxable*cgst_rate/2/100
        # and sum_cgst = taxable*cgst_rate/100, then ratio = 2.0 always
        print(f"    id={r['record_id']}  inv={r['invoice_no']}")
        print(f"      h_cgst={h}  sum_cgst={s}  ratio={s/h:.4f}")
        print(f"      Interpretation: header stores CORRECT value ({h})")
        print(f"                      items store DOUBLED value ({s})")
        print(f"                      -> header is ground truth, items are corrupted")
        print(f"      Item rates: {','.join(f'cg={cg} sg={sg} tx={tx} amt={amt}' for cg,sg,_,tx,amt in r['rates'])}")

print(f"""
  CONCLUSION ON INVARIANT:
  
  IF header total_cgst represents the ACTUAL invoice amount (as printed),
  AND sum(item.cgst_amounts) represents what the AI stored,
  THEN ratio = sum_item_cgst / header_cgst = 2.0 is a DETERMINISTIC proof of
  Mode B corruption — because the AI computed item cgst_amounts using the
  doubled rate (e.g. 5% instead of 2.5%) applied to taxable_value.
  
  The only condition where ratio=2.0 can appear in a CORRECT invoice is if
  the header value is HALF the item total (i.e., the header itself is wrong).
  
  Since the header value comes from the invoice grand total line
  (a simple number printed on the invoice), it is the most reliable value.
  The line-item tax amounts are computed by the AI from the (possibly wrong) rate.
""")
