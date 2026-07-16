"""
GST RATE DUPLICATION CORRECTION — FINAL PRODUCTION DRY-RUN VALIDATION
========================================================================
Processes every PDF in C:\\Users\\ulaganathan\\Downloads\\New folder (2)
through the FULL production OCR pipeline.

Writes NOTHING back to production except temporary InvoiceTempOCR staging
records (which will be created with status=PENDING and never promoted).

After extraction, performs an IN-MEMORY-ONLY simulation of the proposed
Mode B correction and produces a 9-section validation report.

GUARANTEES:
  - Never modifies extracted_data of an existing finalized/frozen record
  - Simulation result is held only in Python memory (dict copy)
  - No vouchers created
  - No Redis state persisted for simulation result
  - All temp records will be deleteable after the run

Usage:
    python scratch/dry_run_validation.py 2>&1 | tee scratch/dry_run_report.txt
"""

import os, sys, json, copy, math, time, django
import io as _io

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from ocr_pipeline.models import InvoiceTempOCR
from core.models import Branch
from ocr_pipeline.normalize import get_normalized_items, normalize_amount, snap_to_standard_gst_rate

SCAN_DIR    = r"C:\Users\ulaganathan\Downloads\New folder (2)"
TENANT_ID   = None   # auto-detect from first Branch record in main()
TOLERANCE   = 0.05
KNOWN_COMBINED = {3.0, 5.0, 12.0, 18.0, 28.0}
BSEP = "=" * 72
SEP  = "-" * 72

# ── Helpers ───────────────────────────────────────────────────────────────────

def to_f(v):
    try:
        if v is None or str(v).strip() == "": return 0.0
        return float(str(v).replace(",","").replace("Rs","").replace("INR","").strip())
    except Exception:
        return 0.0

def near(a, b, tol=TOLERANCE):
    return abs(a - b) <= tol

def ratio_of(num, den):
    if den == 0.0: return None
    return round(num / den, 6)

# ── Simulate Mode B correction on an in-memory item dict ─────────────────────

def simulate_mode_b_correction_item(item: dict) -> dict:
    """
    Returns a COPY of item with corrected cgst_rate / sgst_rate.
    Correction fires ONLY if ALL conditions hold exactly as specified.
    """
    itm = copy.deepcopy(item)
    ig_rate = to_f(itm.get("igst_rate"))
    cg_rate = snap_to_standard_gst_rate(to_f(itm.get("cgst_rate")))
    sg_rate = snap_to_standard_gst_rate(to_f(itm.get("sgst_rate")))
    cg_amt  = to_f(itm.get("cgst") or itm.get("cgst_amount"))
    sg_amt  = to_f(itm.get("sgst") or itm.get("sgst_amount"))
    taxable = to_f(itm.get("taxable_value"))

    # Pre-conditions
    if ig_rate != 0.0:           return itm   # C1: intrastate only
    if cg_rate <= 0.0:           return itm   # C2a: must have CGST
    if not near(cg_rate, sg_rate, 0.001): return itm   # C2b: symmetric
    if cg_rate not in KNOWN_COMBINED: return itm  # C3: known combined
    if taxable <= 0.0:           return itm   # C4
    if cg_amt  <= 0.0:           return itm   # C5

    expected = taxable * cg_rate / 100.0
    if not near(expected, cg_amt, TOLERANCE): return itm   # not Mode B internally consistent

    # Trigger: expected == actual → rate is correct at face value
    # Mode B proof: expected == cg_amt AND cg_rate is a combined rate
    # i.e. taxable * cg_rate / 100 = cg_amt → rate was applied as-is
    # Correction: halve the rate; recompute amounts from corrected rate
    new_cg_rate = round(cg_rate / 2.0, 4)
    new_sg_rate = round(sg_rate / 2.0, 4)
    new_cg_amt  = round(taxable * new_cg_rate / 100.0, 2)
    new_sg_amt  = round(taxable * new_sg_rate / 100.0, 2)

    itm["cgst_rate"]       = new_cg_rate
    itm["sgst_rate"]       = new_sg_rate
    itm["cgst"]            = new_cg_amt
    itm["sgst"]            = new_sg_amt
    itm["computed_gst_rate"] = round(new_cg_rate + new_sg_rate, 4)
    return itm


def simulate_correction(ext: dict) -> dict:
    """
    Returns IN-MEMORY corrected copy of extracted_data.
    Never touches the original dict.
    """
    result = copy.deepcopy(ext)
    items = result.get("items", [])
    corrected_items = [simulate_mode_b_correction_item(i) for i in items]
    result["items"] = corrected_items
    return result

# ── Invoice classification ────────────────────────────────────────────────────

def classify_invoice(ext: dict) -> str:
    """
    A: Correct
    B: Mode A (rate wrong, amount correct)
    C: Mode B (rate AND amount wrong — header ratio ~2.0)
    D: Partial
    E: IGST
    F: Frozen/Corrected
    G: Unknown
    """
    gst_res = ext.get("gst_resolution")
    frozen  = ext.get("is_canonical_frozen", False)
    if gst_res in ("CORRECTED", "SUPPLIER_VALUES_ACCEPTED") or frozen:
        return "F: Frozen/Corrected"

    h_igst = to_f(ext.get("total_igst"))
    h_cgst = to_f(ext.get("total_cgst"))
    h_sgst = to_f(ext.get("total_sgst"))
    items  = ext.get("items", [])

    if h_igst > 0 or any(to_f(i.get("igst_rate")) > 0 for i in items):
        return "E: IGST"

    if not items:
        return "G: Unknown"

    sum_cgst = sum(to_f(i.get("cgst") or i.get("cgst_amount")) for i in items)
    sum_sgst = sum(to_f(i.get("sgst") or i.get("sgst_amount")) for i in items)

    cgst_ratio = ratio_of(sum_cgst, h_cgst) if h_cgst > 0 else None
    sgst_ratio = ratio_of(sum_sgst, h_sgst) if h_sgst > 0 else None

    if h_cgst == 0.0:
        return "G: Unknown"

    # Mode B: header is correct, item amounts doubled → ratio ~2.0
    if cgst_ratio is not None and near(cgst_ratio, 2.0, 0.05):
        return "C: Mode B (header ratio~2)"

    # Mode A: item amounts correct but rate field is doubled
    # Detect: cgst_rate==sgst_rate, rate in KNOWN_COMBINED, but amount matches half-rate
    mode_a_items = 0
    mode_b_items = 0
    correct_items = 0
    for itm in items:
        cg = snap_to_standard_gst_rate(to_f(itm.get("cgst_rate")))
        sg = snap_to_standard_gst_rate(to_f(itm.get("sgst_rate")))
        ig = to_f(itm.get("igst_rate"))
        cg_amt  = to_f(itm.get("cgst") or itm.get("cgst_amount"))
        taxable = to_f(itm.get("taxable_value"))
        if ig > 0 or taxable <= 0 or cg <= 0:
            continue
        expected_at_full = round(taxable * cg / 100.0, 2)
        expected_at_half = round(taxable * (cg/2) / 100.0, 2)
        if near(cg_amt, expected_at_half, TOLERANCE):
            mode_a_items += 1   # amount consistent with half rate → Mode A
        elif near(cg_amt, expected_at_full, TOLERANCE):
            if cg in KNOWN_COMBINED and near(cg, sg, 0.001):
                mode_b_items += 1  # internally consistent but full rate used → Mode B item
            else:
                correct_items += 1
        else:
            pass

    total_assessed = mode_a_items + mode_b_items + correct_items
    if total_assessed == 0:
        # Check ratio near 1.0 → correct
        if cgst_ratio is not None and near(cgst_ratio, 1.0, 0.06):
            return "A: Correct"
        return "G: Unknown"

    if mode_a_items > 0 and mode_b_items == 0:
        return "B: Mode A (rate dup, amount correct)"
    if mode_b_items > 0 and mode_a_items == 0:
        return "C: Mode B (rate+amount both wrong)"
    if mode_a_items > 0 and mode_b_items > 0:
        return "D: Partial"

    if cgst_ratio is not None and near(cgst_ratio, 1.0, 0.06):
        return "A: Correct"
    return "G: Unknown"


def is_mode_b_correctable(ext: dict) -> bool:
    """
    Exactly the guard conditions from the user specification.
    """
    h_cgst = to_f(ext.get("total_cgst"))
    h_sgst = to_f(ext.get("total_sgst"))
    h_igst = to_f(ext.get("total_igst"))
    items  = ext.get("items", [])
    if h_igst != 0.0 or h_cgst <= 0.0 or h_sgst <= 0.0:
        return False

    sum_cgst = sum(to_f(i.get("cgst") or i.get("cgst_amount")) for i in items)
    sum_sgst = sum(to_f(i.get("sgst") or i.get("sgst_amount")) for i in items)
    cgst_r = ratio_of(sum_cgst, h_cgst)
    sgst_r = ratio_of(sum_sgst, h_sgst)
    if cgst_r is None or sgst_r is None:
        return False
    if not (near(cgst_r, 2.0, 0.05) and near(sgst_r, 2.0, 0.05)):
        return False

    # Every affected item must satisfy conditions
    for itm in items:
        ig = to_f(itm.get("igst_rate"))
        cg = snap_to_standard_gst_rate(to_f(itm.get("cgst_rate")))
        sg = snap_to_standard_gst_rate(to_f(itm.get("sgst_rate")))
        cg_amt = to_f(itm.get("cgst") or itm.get("cgst_amount"))
        taxable = to_f(itm.get("taxable_value"))
        if ig > 0: return False
        if cg <= 0: continue
        if not near(cg, sg, 0.001): return False
        if cg not in KNOWN_COMBINED: return False
        expected = taxable * cg / 100.0
        if not near(expected, cg_amt, TOLERANCE): return False
    return True


def verify_simulation(orig: dict, sim: dict) -> dict:
    """
    Verify accounting invariants after simulation.
    Returns {'ok': True/False, 'violations': [...]}
    """
    violations = []
    fields_unchanged = [
        "total_taxable_value", "total_invoice_value",
        "total_igst", "round_off"
    ]
    for f in fields_unchanged:
        ov = to_f(orig.get(f))
        sv = to_f(sim.get(f))
        if not near(ov, sv, 0.02):
            violations.append(f"{f}: orig={ov} sim={sv}")

    # Header CGST and SGST must remain UNCHANGED (they're the ground truth)
    for f in ["total_cgst", "total_sgst"]:
        ov = to_f(orig.get(f))
        sv = to_f(sim.get(f))
        if not near(ov, sv, 0.02):
            violations.append(f"header {f} changed: orig={ov} sim={sv}")

    # Item taxable values must not change
    orig_items = orig.get("items", [])
    sim_items  = sim.get("items", [])
    for idx, (oi, si) in enumerate(zip(orig_items, sim_items)):
        ot = to_f(oi.get("taxable_value"))
        st = to_f(si.get("taxable_value"))
        if not near(ot, st, 0.02):
            violations.append(f"item[{idx}] taxable changed: {ot} -> {st}")

    # Sum of corrected item CGST must now match header
    h_cgst = to_f(sim.get("total_cgst"))
    sum_sim_cgst = sum(to_f(i.get("cgst")) for i in sim_items)
    if not near(sum_sim_cgst, h_cgst, TOLERANCE * len(sim_items)):
        violations.append(f"After correction: sum_item_cgst={sum_sim_cgst} != header_cgst={h_cgst}")

    return {"ok": len(violations) == 0, "violations": violations}

# ── Main Runner Function (Multiprocessing Safe) ────────────────────────────────

def main():
    global TENANT_ID

    # ── Determine a valid tenant_id from the DB ───────────────────────────────
    branch = Branch.objects.first()
    if branch:
        TENANT_ID = str(branch.id)
    else:
        raise RuntimeError("No Branch record found. Cannot create staging records.")

    print(f"Using tenant_id={TENANT_ID}")

    # ── Collect PDFs ──────────────────────────────────────────────────────────
    pdf_files = []
    for root, dirs, files in os.walk(SCAN_DIR):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, f))
    pdf_files.sort()

    print(f"\nFound {len(pdf_files)} PDFs in {SCAN_DIR}")
    for p in pdf_files:
        print(f"  {os.path.basename(p)}")

    # ── Per-invoice processing ────────────────────────────────────────────────
    from ocr_pipeline.pipeline import run_ocr_pipeline
    from ocr_pipeline.models import SessionFinalizationState
    from django.db import transaction

    invoice_results = []
    temp_record_ids = []

    print(f"\n{BSEP}")
    print("RUNNING PRODUCTION OCR PIPELINE (DRY RUN)")
    print(f"{BSEP}\n")

    for pdf_path in pdf_files:
        fname = os.path.basename(pdf_path)
        print(f"\n{SEP}")
        print(f"Processing: {fname}")
        print(SEP)

        result_entry = {
            "file": fname,
            "path": pdf_path,
            "record_id": None,
            "invoice_no": "?",
            "ocr_ok": False,
            "ai_ok": False,
            "classification": "G: Unknown",
            "correctable": False,
            "correction_simulation": None,
            "verification": None,
            "skip_reason": None,
            "h_cgst": 0.0, "h_sgst": 0.0, "h_igst": 0.0, "h_taxable": 0.0,
            "sum_item_cgst": 0.0, "sum_item_sgst": 0.0,
            "cgst_ratio_before": None, "sgst_ratio_before": None,
            "cgst_ratio_after": None,  "sgst_ratio_after": None,
            "before_rates": [], "after_rates": [],
            "before_amounts": [], "after_amounts": [],
            "error": None,
        }

        try:
            with open(pdf_path, "rb") as f:
                file_bytes = f.read()

            # Create a temporary staging record
            with transaction.atomic():
                record = InvoiceTempOCR.objects.create(
                    tenant_id=TENANT_ID,
                    status="PENDING",
                    voucher_type="Purchase",
                    file_path=f"LOCAL://dry_run/{fname}",
                )
                # Create the finalization state stub
                SessionFinalizationState.objects.get_or_create(
                    id=str(record.id),
                    defaults={"expected_pages": 1, "total_pages_expected": 1}
                )
            temp_record_ids.append(record.id)
            result_entry["record_id"] = record.id
            print(f"  Created staging record id={record.id}")

            # Run FULL production pipeline
            pipeline_result = run_ocr_pipeline(
                file_bytes=file_bytes,
                record=record,
                wait_for_ai=True,
                file_path=pdf_path,
            )

            if pipeline_result.get("status") in ("FAILED", "ERROR"):
                result_entry["error"] = pipeline_result.get("error", "Pipeline failed")
                print(f"  PIPELINE FAILED: {result_entry['error']}")
                invoice_results.append(result_entry)
                continue

            result_entry["ocr_ok"] = True
            result_entry["ai_ok"]  = True

            # Reload record to get extracted_data
            record.refresh_from_db()
            ext = record.extracted_data or {}
            if not ext:
                result_entry["error"] = "extracted_data is empty after pipeline"
                invoice_results.append(result_entry)
                continue

            inv_no = (record.supplier_invoice_no or
                      ext.get("invoice_no") or ext.get("canonical_invoice_no") or "?")
            result_entry["invoice_no"] = inv_no
            print(f"  Invoice No: {inv_no}")

            # Collect header values
            h_taxable = to_f(ext.get("total_taxable_value"))
            h_cgst    = to_f(ext.get("total_cgst"))
            h_sgst    = to_f(ext.get("total_sgst"))
            h_igst    = to_f(ext.get("total_igst"))
            items     = ext.get("items", [])

            sum_item_cgst = sum(to_f(i.get("cgst") or i.get("cgst_amount")) for i in items)
            sum_item_sgst = sum(to_f(i.get("sgst") or i.get("sgst_amount")) for i in items)
            sum_item_igst = sum(to_f(i.get("igst") or i.get("igst_amount")) for i in items)

            cgst_ratio = ratio_of(sum_item_cgst, h_cgst)
            sgst_ratio = ratio_of(sum_item_sgst, h_sgst)

            result_entry.update({
                "h_taxable":      h_taxable,
                "h_cgst":         h_cgst,
                "h_sgst":         h_sgst,
                "h_igst":         h_igst,
                "sum_item_cgst":  sum_item_cgst,
                "sum_item_sgst":  sum_item_sgst,
                "cgst_ratio_before": cgst_ratio,
                "sgst_ratio_before": sgst_ratio,
                "before_rates":   [(to_f(i.get("cgst_rate")), to_f(i.get("sgst_rate")), to_f(i.get("igst_rate"))) for i in items],
                "before_amounts": [(to_f(i.get("cgst") or i.get("cgst_amount")), to_f(i.get("sgst") or i.get("sgst_amount"))) for i in items],
            })

            # Classify
            classification = classify_invoice(ext)
            result_entry["classification"] = classification
            print(f"  Classification: {classification}")
            print(f"  h_cgst={h_cgst}  sum_item_cgst={sum_item_cgst}  cgst_ratio={cgst_ratio}")

            # Determine if correctable
            correctable = is_mode_b_correctable(ext)
            result_entry["correctable"] = correctable

            if not correctable:
                skip_reasons = {
                    "E: IGST":                         "IGST invoice — skipped",
                    "F: Frozen/Corrected":             "Frozen/corrected — skipped",
                    "A: Correct":                      "Already correct — no correction needed",
                    "B: Mode A (rate dup, amount correct)": "Mode A — different algorithm required",
                    "D: Partial":                      "Partial corruption — skipped to avoid false positive",
                    "G: Unknown":                      "Unknown corruption pattern — skipped",
                }
                result_entry["skip_reason"] = skip_reasons.get(classification, "Does not meet Mode B criteria")
                print(f"  SKIP: {result_entry['skip_reason']}")
                invoice_results.append(result_entry)
                continue

            # ── SIMULATION (in-memory ONLY) ────────────────────────────────
            print(f"  Mode B confirmed. Simulating correction IN-MEMORY ONLY...")
            sim_ext = simulate_correction(ext)
            sim_items = sim_ext.get("items", [])

            sum_sim_cgst = sum(to_f(i.get("cgst")) for i in sim_items)
            sum_sim_sgst = sum(to_f(i.get("sgst")) for i in sim_items)
            cgst_ratio_after = ratio_of(sum_sim_cgst, h_cgst)
            sgst_ratio_after = ratio_of(sum_sim_sgst, h_sgst)

            result_entry.update({
                "cgst_ratio_after": cgst_ratio_after,
                "sgst_ratio_after": sgst_ratio_after,
                "after_rates":   [(to_f(i.get("cgst_rate")), to_f(i.get("sgst_rate")), to_f(i.get("igst_rate"))) for i in sim_items],
                "after_amounts": [(to_f(i.get("cgst")), to_f(i.get("sgst"))) for i in sim_items],
                "correction_simulation": "SIMULATED",
            })

            # Verify accounting invariants
            verification = verify_simulation(ext, sim_ext)
            result_entry["verification"] = verification
            if verification["ok"]:
                print(f"  Verification: PASS — all accounting invariants held")
            else:
                print(f"  Verification: FAIL — {verification['violations']}")

            print(f"  cgst_ratio: {cgst_ratio} -> {cgst_ratio_after}")

        except Exception as e:
            import traceback
            result_entry["error"] = str(e)
            result_entry["error_traceback"] = traceback.format_exc()
            print(f"  ERROR: {e}")

        invoice_results.append(result_entry)

    # ══════════════════════════════════════════════════════════════════════════
    # REPORT GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n\n{'#'*72}")
    print("GST RATE DUPLICATION CORRECTION — DRY RUN VALIDATION REPORT")
    print(f"{'#'*72}")

    # ── Section 1: Dataset Summary ────────────────────────────────────────────
    total_pdfs      = len(pdf_files)
    total_processed = len(invoice_results)
    ocr_ok          = sum(1 for r in invoice_results if r["ocr_ok"])
    ocr_fail        = sum(1 for r in invoice_results if not r["ocr_ok"] and r["error"])
    ai_ok           = sum(1 for r in invoice_results if r["ai_ok"])
    ai_fail         = total_processed - ai_ok
    skipped         = sum(1 for r in invoice_results if r["skip_reason"])

    print(f"""
{BSEP}
SECTION 1: DATASET SUMMARY
{BSEP}
  Total PDFs scanned:          {total_pdfs}
  Total invoices processed:    {total_processed}
  Successful OCR:              {ocr_ok}
  OCR / AI failures:           {ocr_fail}
  AI successful:               {ai_ok}
  Skipped (not correctable):   {skipped}
  Temp record IDs created:     {temp_record_ids}
""")

    # ── Section 2: Classification ─────────────────────────────────────────────
    cats = {}
    for r in invoice_results:
        cats.setdefault(r["classification"], []).append(r["file"])

    print(f"{BSEP}")
    print("SECTION 2: CLASSIFICATION")
    print(f"{BSEP}")
    for cat, files in sorted(cats.items()):
        print(f"  {cat}")
        for f in files:
            print(f"    - {f}")

    # ── Section 3: Invoices that WOULD be corrected ───────────────────────────
    to_correct = [r for r in invoice_results if r["correctable"]]

    print(f"\n{BSEP}")
    print("SECTION 3: INVOICES THAT WOULD BE CORRECTED")
    print(f"{BSEP}")
    if not to_correct:
        print("  NONE — no invoices met all Mode B correction criteria.")
    else:
        for r in to_correct:
            items_before = r["before_rates"]
            items_after  = r["after_rates"]
            amts_before  = r["before_amounts"]
            amts_after   = r["after_amounts"]
            print(f"""
  Record ID:      {r['record_id']}
  Invoice No:     {r['invoice_no']}
  File:           {r['file']}
  Header CGST:    {r['h_cgst']}
  Header SGST:    {r['h_sgst']}
  Header IGST:    {r['h_igst']}
  CGST Ratio Before: {r['cgst_ratio_before']}
  SGST Ratio Before: {r['sgst_ratio_before']}
  CGST Ratio After:  {r['cgst_ratio_after']}
  SGST Ratio After:  {r['sgst_ratio_after']}
  Old Rates:      {items_before}
  New Rates:      {items_after}
  Old Amounts:    {amts_before}
  New Amounts:    {amts_after}
  Verification:   {'PASS' if r['verification']['ok'] else 'FAIL: ' + str(r['verification']['violations'])}""")

    # ── Section 4: Skipped invoices ───────────────────────────────────────────
    skipped_list = [r for r in invoice_results if r["skip_reason"]]
    print(f"\n{BSEP}")
    print("SECTION 4: INVOICES INTENTIONALLY SKIPPED")
    print(f"{BSEP}")
    for r in skipped_list:
        print(f"  {r['file']:45s} -> {r['skip_reason']}")

    errors = [r for r in invoice_results if r["error"]]
    if errors:
        print(f"\n  Pipeline errors ({len(errors)} files):")
        for r in errors:
            print(f"    {r['file']}: {r['error']}")

    # ── Section 5: False Positive Analysis ────────────────────────────────────
    correct_classified = [r for r in invoice_results if r["classification"].startswith("A:")]
    wrongly_corrected  = [r for r in correct_classified if r["correctable"]]

    print(f"\n{BSEP}")
    print("SECTION 5: FALSE POSITIVE ANALYSIS")
    print(f"{BSEP}")
    if not wrongly_corrected:
        print("  ZERO FALSE POSITIVES.")
        print("  No correctly-classified invoice would be modified by the algorithm.")
    else:
        print(f"  WARNING: {len(wrongly_corrected)} false positive(s) detected:")
        for r in wrongly_corrected:
            print(f"    {r['file']} — cgst_ratio={r['cgst_ratio_before']}")

    # ── Section 6: False Negative Analysis ────────────────────────────────────
    mode_b_records   = [r for r in invoice_results if "Mode B" in r["classification"]]
    uncorrected_mode_b = [r for r in mode_b_records if not r["correctable"]]

    print(f"\n{BSEP}")
    print("SECTION 6: FALSE NEGATIVE ANALYSIS")
    print(f"{BSEP}")
    if not uncorrected_mode_b:
        print("  All detected Mode B invoices would be corrected.")
    else:
        print(f"  {len(uncorrected_mode_b)} Mode B invoice(s) not correctable:")
        for r in uncorrected_mode_b:
            print(f"    {r['file']}: {r['skip_reason']}")

    mode_a_records = [r for r in invoice_results if r["classification"].startswith("B:")]
    if mode_a_records:
        print(f"\n  Mode A invoices (remain corrupted — different algorithm needed):")
        for r in mode_a_records:
            print(f"    {r['file']}")

    partial_records = [r for r in invoice_results if r["classification"].startswith("D:")]
    if partial_records:
        print(f"\n  Partial corruption (remain corrupted — too risky to correct):")
        for r in partial_records:
            print(f"    {r['file']}")

    # ── Section 7: Accounting Verification ────────────────────────────────────
    print(f"\n{BSEP}")
    print("SECTION 7: ACCOUNTING VERIFICATION")
    print(f"{BSEP}")
    pass_count = sum(1 for r in to_correct if r["verification"] and r["verification"]["ok"])
    fail_count = sum(1 for r in to_correct if r["verification"] and not r["verification"]["ok"])
    print(f"  Corrected invoices:        {len(to_correct)}")
    print(f"  Verification PASS:         {pass_count}")
    print(f"  Verification FAIL:         {fail_count}")
    for r in to_correct:
        if r["verification"] and not r["verification"]["ok"]:
            print(f"  FAIL details — {r['file']}:")
            for v in r["verification"]["violations"]:
                print(f"    {v}")

    print(f"""
  Invariants checked for each simulated invoice:
    - total_taxable_value:   unchanged     [REQUIRED]
    - total_invoice_value:   unchanged     [REQUIRED]
    - total_igst:            unchanged     [REQUIRED]
    - round_off:             unchanged     [REQUIRED]
    - header total_cgst:     unchanged     [REQUIRED — ground truth]
    - header total_sgst:     unchanged     [REQUIRED — ground truth]
    - item taxable_values:   unchanged     [REQUIRED]
    - sum(sim cgst) == h_cgst after corr: VERIFIED
""")

    # ── Section 8: Confusion Matrix ───────────────────────────────────────────
    print(f"{BSEP}")
    print("SECTION 8: CONFUSION MATRIX")
    print(f"{BSEP}")

    actually_corrupted  = [r for r in invoice_results if r["classification"] not in ("A: Correct", "E: IGST", "F: Frozen/Corrected", "G: Unknown") and not r["error"]]
    actually_correct    = [r for r in invoice_results if r["classification"] in ("A: Correct", "E: IGST", "F: Frozen/Corrected") and not r["error"]]
    predicted_corrupted = [r for r in invoice_results if r["correctable"]]
    predicted_correct   = [r for r in invoice_results if not r["correctable"] and not r["error"]]

    tp = len([r for r in predicted_corrupted if r in actually_corrupted])
    fp = len([r for r in predicted_corrupted if r in actually_correct])
    tn = len([r for r in predicted_correct   if r in actually_correct])
    fn = len([r for r in predicted_correct   if r in actually_corrupted])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr       = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    print(f"""
                  Predicted
               Correct   Corrupt
  Actual Correct  {tn:4d}     {fp:4d}
  Actual Corrupt  {fn:4d}     {tp:4d}

  Precision (TP / TP+FP):         {precision:.2%}
  Recall    (TP / TP+FN):         {recall:.2%}
  False Positive Rate:            {fpr:.2%}
  False Negative Rate:            {fnr:.2%}

  Note: False Negatives include Mode A and Partial — not detectable
  by header ratio alone, and excluded by design to prevent false positives.
""")

    # ── Section 9: Final Verdict ──────────────────────────────────────────────
    print(f"{BSEP}")
    print("SECTION 9: FINAL VERDICT")
    print(f"{BSEP}")

    checks = {
        "Zero false positives":                           fp == 0,
        "Mode B invoices corrected correctly":            pass_count == len(to_correct) if to_correct else True,
        "IGST invoices untouched":                        all(not r["correctable"] for r in invoice_results if "E: IGST" in r["classification"]),
        "Frozen/Corrected invoices untouched":            all(not r["correctable"] for r in invoice_results if "F:" in r["classification"]),
        "Partial corruption untouched":                   all(not r["correctable"] for r in invoice_results if "D:" in r["classification"]),
        "Voucher/Header totals unchanged after sim":      fail_count == 0,
        "No accounting regression detected":              fail_count == 0,
    }

    all_pass = all(checks.values())

    for check, result in checks.items():
        mark = "PASS" if result else "FAIL"
        print(f"  [{mark}] {check}")

    print()
    if all_pass:
        verdict = "SAFE FOR PRODUCTION"
    elif fp == 0 and fail_count == 0:
        verdict = "SAFE WITH RESTRICTIONS"
    else:
        verdict = "NOT SAFE"

    print(f"  VERDICT: {verdict}")
    print()

    if verdict == "SAFE WITH RESTRICTIONS":
        non_pass = [k for k, v in checks.items() if not v]
        print(f"  Restrictions: {non_pass}")

    print(f"\n  Temp records created (can be deleted): {temp_record_ids}")
    print(f"\n{BSEP}")
    print("END OF DRY RUN REPORT")
    print(f"{BSEP}\n")


if __name__ == '__main__':
    main()
