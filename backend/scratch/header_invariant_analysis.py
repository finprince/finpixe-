"""
FORENSIC INVESTIGATION: Header Invariant Analysis
==================================================
Determines whether header totals provide deterministic proof of Mode B GST
rate duplication (both rate AND amounts wrong) across a population of invoices.

For each InvoiceTempOCR record:
  - Reads header totals: total_taxable_value, total_cgst, total_sgst, total_igst
  - Sums line-item cgst/sgst amounts
  - Computes ratio: sum_item_cgst / header_total_cgst
  - Classifies the invoice and determines whether ratio is a reliable invariant.

Run from backend/ directory:
    python scratch/header_invariant_analysis.py
"""
import os, sys, json, django, math

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR

SEP   = "-" * 72
BSEP  = "=" * 72

# ── Helpers ───────────────────────────────────────────────────────────────────

def to_f(v):
    try:
        if v is None or str(v).strip() == "": return 0.0
        return float(str(v).replace(",", "").replace("Rs", "").replace("INR", "").strip())
    except Exception:
        return 0.0

def ratio_str(num, den):
    if den == 0.0:
        return "inf" if num != 0 else "n/a"
    r = num / den
    return f"{r:.4f}"

def classify_invoice(ext):
    """Determine invoice category from stored data."""
    gst_res  = ext.get("gst_resolution")
    frozen   = ext.get("is_canonical_frozen", False)
    has_igst = to_f(ext.get("total_igst")) > 0.0
    items    = ext.get("items", [])
    rates    = set()
    for itm in items:
        cg = to_f(itm.get("cgst_rate"))
        sg = to_f(itm.get("sgst_rate"))
        ig = to_f(itm.get("igst_rate"))
        if ig > 0:
            rates.add(("igst", round(ig, 2)))
        elif cg > 0 or sg > 0:
            rates.add(("cgst_sgst", round(cg, 2), round(sg, 2)))
    if gst_res in ("CORRECTED", "SUPPLIER_VALUES_ACCEPTED"):
        return "CORRECTED"
    if frozen:
        return "FROZEN"
    if has_igst or any(r[0] == "igst" for r in rates):
        return "IGST"
    if len(rates) > 1:
        return "MIXED"
    return "INTRASTATE"

def analyze_record(rec):
    """Return analysis dict for one record, or None if insufficient data."""
    ext   = rec.extracted_data or {}
    items = ext.get("items", [])
    if not items:
        return None

    h_taxable = to_f(ext.get("total_taxable_value"))
    h_cgst    = to_f(ext.get("total_cgst"))
    h_sgst    = to_f(ext.get("total_sgst"))
    h_igst    = to_f(ext.get("total_igst"))

    # Skip records with zero header totals (incomplete data)
    if h_cgst == 0.0 and h_sgst == 0.0 and h_igst == 0.0:
        return None

    sum_item_cgst = sum(to_f(i.get("cgst") or i.get("cgst_amount")) for i in items)
    sum_item_sgst = sum(to_f(i.get("sgst") or i.get("sgst_amount")) for i in items)
    sum_item_igst = sum(to_f(i.get("igst") or i.get("igst_amount")) for i in items)
    sum_item_taxable = sum(to_f(i.get("taxable_value")) for i in items)

    # Ratio: sum_item_cgst / header_total_cgst
    cgst_ratio = (sum_item_cgst / h_cgst) if h_cgst > 0 else None
    sgst_ratio = (sum_item_sgst / h_sgst) if h_sgst > 0 else None
    igst_ratio = (sum_item_igst / h_igst) if h_igst > 0 else None
    taxable_ratio = (sum_item_taxable / h_taxable) if h_taxable > 0 else None

    category = classify_invoice(ext)
    inv_no   = rec.supplier_invoice_no or ext.get("invoice_no") or ext.get("canonical_invoice_no") or "?"

    # Compute per-item cgst_rate profile
    item_rates = []
    for itm in items:
        cg = to_f(itm.get("cgst_rate"))
        sg = to_f(itm.get("sgst_rate"))
        cg_amt = to_f(itm.get("cgst") or itm.get("cgst_amount"))
        taxable = to_f(itm.get("taxable_value"))
        item_rates.append((cg, sg, cg_amt, taxable))

    return {
        "record_id":       rec.id,
        "invoice_no":      inv_no,
        "category":        category,
        "h_taxable":       h_taxable,
        "h_cgst":          h_cgst,
        "h_sgst":          h_sgst,
        "h_igst":          h_igst,
        "sum_item_cgst":   sum_item_cgst,
        "sum_item_sgst":   sum_item_sgst,
        "sum_item_igst":   sum_item_igst,
        "sum_item_taxable": sum_item_taxable,
        "cgst_ratio":      cgst_ratio,
        "sgst_ratio":      sgst_ratio,
        "igst_ratio":      igst_ratio,
        "taxable_ratio":   taxable_ratio,
        "item_rates":      item_rates,
        "items_count":     len(items),
    }

# ── Data fetch ────────────────────────────────────────────────────────────────

print(f"\n{BSEP}")
print("FORENSIC HEADER INVARIANT ANALYSIS")
print(f"{BSEP}\n")
print("Fetching records...")

# Fetch ~200 most recent FINALIZED records across all tenants
qs = (InvoiceTempOCR.objects
      .filter(status="FINALIZED")
      .exclude(extracted_data__isnull=True)
      .order_by("-id")[:200])

results = []
skipped = 0
for rec in qs:
    r = analyze_record(rec)
    if r is None:
        skipped += 1
        continue
    results.append(r)

print(f"Analyzed: {len(results)} records  |  Skipped (no data): {skipped}")

# ── Categorize ────────────────────────────────────────────────────────────────

by_cat = {}
for r in results:
    by_cat.setdefault(r["category"], []).append(r)

print(f"\nCategory breakdown:")
for cat, recs in sorted(by_cat.items()):
    print(f"  {cat:20s}: {len(recs)} records")

# ── Per-record detail table ───────────────────────────────────────────────────

print(f"\n{BSEP}")
print("DETAIL TABLE: cgst_ratio = sum(item.cgst) / header.total_cgst")
print(f"{BSEP}")
print(f"{'ID':>9}  {'Invoice No':25}  {'Cat':12}  {'h_cgst':>8}  {'sum_cgst':>10}  {'cgst_ratio':>12}  {'taxable_ratio':>14}  {'item_cgst_rates'}")
print(SEP)

for r in results:
    rate_str = ",".join(f"{cg}/{sg}" for cg, sg, _, _ in r["item_rates"])
    cgst_r_str = f"{r['cgst_ratio']:.4f}" if r["cgst_ratio"] is not None else "n/a"
    tax_r_str  = f"{r['taxable_ratio']:.4f}" if r["taxable_ratio"] is not None else "n/a"
    print(f"{r['record_id']:>9}  {r['invoice_no']:25}  {r['category']:12}  "
          f"{r['h_cgst']:>8.2f}  {r['sum_item_cgst']:>10.2f}  {cgst_r_str:>12}  {tax_r_str:>14}  {rate_str}")

# ── Ratio distribution per category ──────────────────────────────────────────

print(f"\n{BSEP}")
print("RATIO DISTRIBUTION: cgst_ratio per category")
print(f"{BSEP}")

for cat, recs in sorted(by_cat.items()):
    ratios = [r["cgst_ratio"] for r in recs if r["cgst_ratio"] is not None]
    if not ratios:
        continue
    near_1  = sum(1 for x in ratios if abs(x - 1.0) <= 0.05)
    near_2  = sum(1 for x in ratios if abs(x - 2.0) <= 0.05)
    near_05 = sum(1 for x in ratios if abs(x - 0.5) <= 0.05)
    other   = len(ratios) - near_1 - near_2 - near_05
    mn      = min(ratios)
    mx      = max(ratios)
    avg     = sum(ratios) / len(ratios)

    print(f"\n  Category: {cat} (n={len(recs)})")
    print(f"    min={mn:.4f}  max={mx:.4f}  avg={avg:.4f}")
    print(f"    ratio ~1.0 (correct):      {near_1:3d}  ({100*near_1/len(ratios):.1f}%)")
    print(f"    ratio ~2.0 (Mode B dup):   {near_2:3d}  ({100*near_2/len(ratios):.1f}%)")
    print(f"    ratio ~0.5 (halved):       {near_05:3d}  ({100*near_05/len(ratios):.1f}%)")
    print(f"    other ratio:               {other:3d}  ({100*other/len(ratios):.1f}%)")
    if other > 0:
        others = [x for x in ratios if abs(x - 1.0) > 0.05 and abs(x - 2.0) > 0.05 and abs(x - 0.5) > 0.05]
        print(f"    other values: {others[:10]}")

# ── Key invariant test ────────────────────────────────────────────────────────

print(f"\n{BSEP}")
print("INVARIANT TEST: Is cgst_ratio == 2.0 a reliable proof of Mode B?")
print(f"{BSEP}")

true_positives  = 0  # cgst_ratio ~2.0 AND category is INTRASTATE/MIXED (i.e., correct detect)
false_positives = 0  # cgst_ratio ~2.0 AND category is CORRECTED or FROZEN (i.e., wrong alarm)
true_negatives  = 0  # cgst_ratio ~1.0 AND category is CORRECTED/IGST (correct skip)
false_negatives = 0  # cgst_ratio ~1.0 AND category is INTRASTATE with known issue

details_2x = []

for r in results:
    rat = r["cgst_ratio"]
    if rat is None:
        continue
    is_2x = abs(rat - 2.0) <= 0.05
    is_1x = abs(rat - 1.0) <= 0.05
    cat   = r["category"]
    if is_2x:
        details_2x.append(r)
        if cat in ("CORRECTED", "IGST", "FROZEN"):
            false_positives += 1
        else:
            true_positives += 1
    if is_1x and cat in ("CORRECTED", "IGST", "FROZEN"):
        true_negatives += 1

print(f"\n  Records with cgst_ratio ~2.0 ({len(details_2x)} total):")
for r in details_2x:
    print(f"    id={r['record_id']:>8}  inv={r['invoice_no']:25}  cat={r['category']:12}  "
          f"h_cgst={r['h_cgst']:.2f}  sum_cgst={r['sum_item_cgst']:.2f}  "
          f"rates={','.join(f'{cg}/{sg}' for cg,sg,_,_ in r['item_rates'])}")

print(f"\n  Reliability:")
print(f"    True Positives  (ratio~2 AND corrupted):  {true_positives}")
print(f"    False Positives (ratio~2 AND legitimate):  {false_positives}")
print(f"    True Negatives  (ratio~1 AND correct):     {true_negatives}")

total_ratio_2x = len(details_2x)
precision = true_positives / total_ratio_2x if total_ratio_2x > 0 else 0.0
print(f"    Precision (TP/all_2x):                    {precision:.2%}")

# ── Also check per-item: derived_cgst_rate vs header_implied_rate ──────────────

print(f"\n{BSEP}")
print("SECONDARY TEST: item-level — derived_rate = (h_cgst / h_taxable) * 100")
print(f"{BSEP}")
print("Checks if the header-implied rate differs from the item cgst_rate.")
print()

for r in results:
    if r["h_taxable"] <= 0 or r["h_igst"] > 0:
        continue
    header_implied_cgst_rate = (r["h_cgst"] / r["h_taxable"]) * 100.0
    for cg, sg, cg_amt, taxable in r["item_rates"]:
        if cg == 0 and sg == 0:
            continue
        # Expected: item cgst_rate should equal (header_implied_cgst_rate),
        # OR header_implied_cgst_rate == item_cgst_rate/2 (Mode B marker)
        if abs(cg - header_implied_cgst_rate * 2) <= 0.3:
            print(f"  id={r['record_id']:>8}  inv={r['invoice_no']:25}  cat={r['category']:12}  "
                  f"item_cgst_rate={cg}  header_implied={header_implied_cgst_rate:.2f}  "
                  f"ratio=item/header={cg/header_implied_cgst_rate:.3f}  -> POSSIBLE MODE B")

# ── Final verdict ─────────────────────────────────────────────────────────────

print(f"\n{BSEP}")
print("CONCLUSION")
print(f"{BSEP}")

all_ratios_intrastate = [r["cgst_ratio"] for r in results
                         if r["category"] in ("INTRASTATE","MIXED") and r["cgst_ratio"] is not None]
all_ratios_correct    = [r["cgst_ratio"] for r in results
                         if r["category"] in ("CORRECTED","FROZEN","IGST") and r["cgst_ratio"] is not None]

near2_in_intrastate = sum(1 for x in all_ratios_intrastate if abs(x-2.0) <= 0.05)
near2_in_correct    = sum(1 for x in all_ratios_correct    if abs(x-2.0) <= 0.05)
near1_in_intrastate = sum(1 for x in all_ratios_intrastate if abs(x-1.0) <= 0.05)

print(f"""
  Total records analyzed:     {len(results)}
  Intrastate/Mixed invoices:  {len(all_ratios_intrastate)}
    of which cgst_ratio ~2.0: {near2_in_intrastate}
    of which cgst_ratio ~1.0: {near1_in_intrastate}
  Correct/IGST/Frozen:        {len(all_ratios_correct)}
    of which cgst_ratio ~2.0: {near2_in_correct}  (false positive rate)

  INVARIANT EXISTS? cgst_ratio == 2.0 identifies Mode B with precision {precision:.2%}
""")
