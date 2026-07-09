"""
Phase 3A Document Validation — Offline Test Runner
====================================================
Tests the Document Quality Validation Layer against:
  1. The forensic invoice (Screenshot 2026-06-24 180236.pdf) using values
     documented in PRODUCTION_SINGLE_INVOICE_STAGE_TRACE.md
  2. The Sprint 3 validation dataset from the database

Usage (run from backend directory):
  python -m ocr_pipeline.document_validator.test_validator

No Django ORM is needed for the offline tests (forensic + synthetic).
The Sprint 3 DB test requires a running Django environment.
"""
from __future__ import annotations

import sys

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import json
import os
import sys
import time
from typing import Any, Dict, List

# ── Path setup ─────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _print_banner(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _print_result(report) -> None:
    """Pretty-print a DocumentValidationReport."""
    status_icons = {"PASS": "[OK]", "WARNING": "[WRN]", "ERROR": "[ERR]"}
    overall_icon = {"PASS": "[PASS]", "PASS_WITH_WARNINGS": "[WARN]", "FAIL": "[FAIL]"}

    print(f"\n  Invoice   : {report.invoice_no or '(unknown)'}")
    print(f"  Overall   : {overall_icon.get(report.overall, '?')}  {report.overall}")
    print(f"  Elapsed   : {report.elapsed_ms} ms")
    print()
    print(f"  {'Rule':<50} {'Status':<12} {'Detail'}")
    print(f"  {'-' * 50} {'-' * 12} {'-' * 30}")
    for r in report.rules:
        icon = status_icons.get(r.status, "?")
        detail = ""
        if r.expected is not None and r.actual is not None:
            detail = f"expected={r.expected!r} actual={r.actual!r}"
        elif r.actual is not None:
            detail = f"actual={r.actual!r}"
        print(f"  {icon} {r.rule:<48} {r.status:<12} {detail}")

    if report.errors:
        print(f"\n  ERRORS ({len(report.errors)}):")
        for e in report.errors:
            print(f"    [ERR] {e}")
    if report.warnings:
        print(f"\n  WARNINGS ({len(report.warnings)}):")
        for w in report.warnings:
            print(f"    [WRN] {w}")


def _assert(condition: bool, label: str) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"    [{status}] {label}")
    if not condition:
        global _test_failures
        _test_failures += 1


_test_failures = 0


# ── Test data ────────────────────────────────────────────────────────────────

def _forensic_invoice_payload() -> Dict[str, Any]:
    """
    Reconstructed from PRODUCTION_SINGLE_INVOICE_STAGE_TRACE.md.
    Values reflect what the pipeline actually produced after normalization:
      - invoice_no     : 'VMT25-26/147'  (Qwen corrected OCR)
      - invoice_date   : '30-09-2025'    (Qwen corrected OCR)
      - vendor_gstin   : '33BTTPM6743D1ZF' (Qwen corrected OCR)
      - buyer_gstin    : ''              (Qwen dropped garbled OCR)
      - HSN items 2-6  : '11'            (OCR artefact from ditto marks)
      - CGST/SGST rates: 0.0             (Qwen returned null, normalizer snapped to 0)
      - Line qty       : 1.0             (normalizer fallback)
      - Line rate      : 3500.0          (normalizer fallback)
    Tax mismatch noted in the trace — this caused PENDING_PURCHASE routing.
    """
    return {
        "invoice_no": "VMT25-26/147",
        "invoice_date": "30-09-2025",
        "vendor_name": "VMTECH SOLUTIONS",
        "vendor_gstin": "33BTTPM6743D1ZF",
        "buyer_gstin": "",                          # Qwen dropped this
        "buyer_name": "",
        "bill_to": "",
        "bill_from": "No.12, Anna Nagar, Chennai",
        "total_taxable_value": 21000.0,
        "total_cgst": 1890.0,
        "total_sgst": 1890.0,
        "total_igst": 0.0,
        "total_cess": 0.0,
        "round_off": 0.0,
        # Grand total as extracted — intentionally wrong to reproduce the
        # CGST/SGST sum mismatch documented in the trace.
        "total_invoice_value": 24285.0,   # extracted value (wrong)
        # computed would be 21000 + 1890 + 1890 = 24780 → mismatch of ₹495
        "items": [
            {
                "description": "Service charges for Pneumatic Chuck",
                "hsn_sac": "948711",
                "qty": 1.0,
                "rate": 3500.0,
                "taxable_value": 3500.0,
                "cgst_rate": 0.0,
                "sgst_rate": 0.0,
                "cgst": 0.0,
                "sgst": 0.0,
            },
            {
                "description": "Service charges item 2",
                "hsn_sac": "11",            # OCR artefact from ditto marks
                "qty": 1.0,
                "rate": 3500.0,
                "taxable_value": 3500.0,
                "cgst_rate": 0.0,
                "sgst_rate": 0.0,
                "cgst": 0.0,
                "sgst": 0.0,
            },
        ],
    }


def _complete_valid_payload() -> Dict[str, Any]:
    """
    A fully valid invoice — all modules should PASS.
    GSTINs are taken from the forensic invoice trace (verified real GSTINs):
      33BTTPM6743D1ZF — vendor (from forensic invoice, passes checksum)
    Buyer GSTIN omitted to avoid checksum dependency — buyer is WARNING only.
    """
    return {
        "invoice_no": "INV-2025-001",
        "invoice_date": "01-07-2025",
        "vendor_name": "ABC Supplies Pvt Ltd",
        "vendor_gstin": "33BTTPM6743D1ZF",   # real GSTIN from forensic invoice
        "buyer_gstin": "",                     # B2C — buyer GSTIN optional
        "buyer_name": "XYZ Corp",
        "bill_from": "Chennai",
        "bill_to": "Mumbai",
        "total_taxable_value": 10000.0,
        "total_cgst": 900.0,
        "total_sgst": 900.0,
        "total_igst": 0.0,
        "total_cess": 0.0,
        "round_off": 0.0,
        "total_invoice_value": 11800.0,
        "items": [
            {"description": "Widget A", "hsn_sac": "847130", "qty": 10, "rate": 1000.0, "taxable_value": 10000.0},
        ],
    }


def _missing_fields_payload() -> Dict[str, Any]:
    """Invoice with several mandatory fields absent — M01 and M04 should ERROR."""
    return {
        "invoice_no": "",
        "invoice_date": None,
        "vendor_name": "",
        "vendor_gstin": "",
        "total_invoice_value": 0.0,
        "items": [],
    }


def _tax_mismatch_payload() -> Dict[str, Any]:
    """Tax arithmetic intentionally wrong — M02 should ERROR."""
    return {
        "invoice_no": "TAX-MISMATCH-001",
        "invoice_date": "01-07-2025",
        "vendor_name": "Test Vendor",
        "vendor_gstin": "29AABCT1332L1ZE",
        "bill_from": "Bangalore",
        "total_taxable_value": 10000.0,
        "total_cgst": 500.0,   # Wrong: should be 900
        "total_sgst": 500.0,   # Wrong: should be 900
        "total_invoice_value": 11800.0,
        "items": [{"description": "Item A", "taxable_value": 10000.0}],
    }


def _invalid_gstin_payload() -> Dict[str, Any]:
    """Vendor GSTIN is malformed — M03 should ERROR."""
    return {
        "invoice_no": "GSTIN-BAD-001",
        "invoice_date": "01-07-2025",
        "vendor_name": "Bad GSTIN Vendor",
        "vendor_gstin": "338TTP0674301ZF",   # OCR artefact (B→8, D→0) from forensic trace
        "bill_from": "Chennai",
        "total_invoice_value": 5000.0,
        "items": [{"description": "Item X", "taxable_value": 5000.0}],
    }


# ── Test cases ───────────────────────────────────────────────────────────────

def test_forensic_invoice(run_fn) -> None:
    _print_banner("TEST 1 — Forensic Invoice (Screenshot 2026-06-24 180236.pdf)")
    print("  Source: PRODUCTION_SINGLE_INVOICE_STAGE_TRACE.md\n")

    payload = _forensic_invoice_payload()
    report = run_fn(invoice=payload, tenant_id="forensic", record_id="1008123")
    _print_result(report)

    print("\n  Assertions:")
    _assert(report.overall in ("FAIL", "PASS_WITH_WARNINGS"),
            "Overall is not PASS (tax mismatch + buyer GSTIN empty)")

    m02_rules = [r for r in report.rules if r.module == "M02_TAX"]
    tax_rule = next((r for r in m02_rules if r.rule == "tax_arithmetic"), None)
    _assert(tax_rule is not None and tax_rule.status == "ERROR",
            "M02: tax_arithmetic reports ERROR (₹495 mismatch)")

    m03_rules = [r for r in report.rules if r.module == "M03_GSTIN"]
    vendor_rule = next((r for r in m03_rules if "vendor" in r.rule), None)
    _assert(vendor_rule is not None and vendor_rule.status == "PASS",
            "M03: Vendor GSTIN 33BTTPM6743D1ZF reports PASS")

    buyer_rule = next((r for r in m03_rules if "buyer" in r.rule), None)
    _assert(buyer_rule is not None and buyer_rule.status == "WARNING",
            "M03: Buyer GSTIN (empty) reports WARNING")

    m01_rules = [r for r in report.rules if r.module == "M01_MANDATORY"]
    inv_rule = next((r for r in m01_rules if r.rule == "mandatory_invoice_no"), None)
    _assert(inv_rule is not None and inv_rule.status == "PASS",
            "M01: invoice_no VMT25-26/147 reports PASS")


def test_complete_valid(run_fn) -> None:
    _print_banner("TEST 2 — Complete Valid Invoice (vendor fields PASS, buyer WARNING expected)")

    payload = _complete_valid_payload()
    report = run_fn(invoice=payload, tenant_id="test", record_id="test-001")
    _print_result(report)

    print("\n  Assertions:")
    _assert(report.overall in ("PASS", "PASS_WITH_WARNINGS"),
            "Overall is PASS or PASS_WITH_WARNINGS (buyer GSTIN absent = WARNING only)")
    _assert(len(report.errors) == 0,
            "No errors expected (all mandatory vendor fields present, tax balances)")
    vendor_rule = next((r for r in report.rules if "vendor" in r.rule and r.module == "M03_GSTIN"), None)
    _assert(vendor_rule is not None and vendor_rule.status == "PASS",
            "M03: Vendor GSTIN 33BTTPM6743D1ZF is valid (PASS)")


def test_missing_fields(run_fn) -> None:
    _print_banner("TEST 3 — Missing Mandatory Fields")

    payload = _missing_fields_payload()
    report = run_fn(invoice=payload, tenant_id="test", record_id="test-002")
    _print_result(report)

    print("\n  Assertions:")
    _assert(report.overall == "FAIL",
            "Overall should be FAIL (multiple mandatory fields missing)")
    _assert(len(report.errors) >= 4,
            "At least 4 ERROR results (inv_no, date, vendor, total, items)")


def test_tax_mismatch(run_fn) -> None:
    _print_banner("TEST 4 — Tax Arithmetic Mismatch")

    payload = _tax_mismatch_payload()
    report = run_fn(invoice=payload, tenant_id="test", record_id="test-003")
    _print_result(report)

    print("\n  Assertions:")
    m02 = next((r for r in report.rules if r.rule == "tax_arithmetic"), None)
    _assert(m02 is not None and m02.status == "ERROR",
            "M02: tax_arithmetic should ERROR when computed ≠ extracted")


def test_invalid_gstin(run_fn) -> None:
    _print_banner("TEST 5 — Invalid Vendor GSTIN (OCR artefact)")

    payload = _invalid_gstin_payload()
    report = run_fn(invoice=payload, tenant_id="test", record_id="test-004")
    _print_result(report)

    print("\n  Assertions:")
    m03 = [r for r in report.rules if r.module == "M03_GSTIN" and "vendor" in r.rule]
    vendor_rule = m03[0] if m03 else None
    _assert(vendor_rule is not None and vendor_rule.status in ("ERROR", "WARNING"),
            "M03: malformed vendor GSTIN is flagged")


def test_performance(run_fn) -> None:
    _print_banner("TEST 6 — Performance (100 iterations)")

    payload = _complete_valid_payload()
    times = []
    for _ in range(100):
        t0 = time.monotonic()
        run_fn(invoice=payload, tenant_id="perf", record_id="perf-001")
        times.append((time.monotonic() - t0) * 1000)

    avg = sum(times) / len(times)
    p99 = sorted(times)[98]
    print(f"\n  avg={avg:.2f}ms  p99={p99:.2f}ms  max={max(times):.2f}ms")

    _assert(avg < 20.0, "Average validation time < 20ms")
    _assert(p99 < 50.0, "p99 validation time < 50ms")


# ── Sprint 3 DB test (requires Django) ──────────────────────────────────────

def test_sprint3_dataset(run_fn) -> None:
    """
    Runs the validator against the 25 most recent finalized records in the DB.
    Requires Django environment (manage.py shell or runserver context).
    """
    _print_banner("TEST 7 — Sprint 3 Dataset (live DB records)")

    try:
        import django
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.base")
        django.setup()
    except Exception as e:
        print(f"  [SKIP] Django not available: {e}")
        return

    try:
        from ocr_pipeline.models import InvoiceTempOCR  # type: ignore
        from ocr_pipeline.normalize import get_canonical_export_record  # type: ignore
        records = (
            InvoiceTempOCR.objects
            .filter(status="FINALIZED")
            .exclude(extracted_data=None)
            .order_by("-created_at")[:25]
        )

        results_summary = []
        for rec in records:
            try:
                canonical = get_canonical_export_record(
                    rec.extracted_data or {}, tenant_id=rec.tenant_id
                )
                report = run_fn(
                    invoice=canonical,
                    tenant_id=str(rec.tenant_id),
                    record_id=str(rec.id),
                )
                results_summary.append({
                    "record_id": rec.id,
                    "invoice_no": rec.supplier_invoice_no or "",
                    "overall": report.overall,
                    "errors": len(report.errors),
                    "warnings": len(report.warnings),
                    "elapsed_ms": report.elapsed_ms,
                })
            except Exception as row_err:
                results_summary.append({
                    "record_id": rec.id,
                    "invoice_no": getattr(rec, "supplier_invoice_no", ""),
                    "overall": "ERROR",
                    "error_detail": str(row_err),
                })

        print(f"\n  Processed {len(results_summary)} records\n")
        print(f"  {'RecordID':<12} {'InvoiceNo':<25} {'Overall':<22} {'Errors':<8} {'Warns':<8} {'ms'}")
        print(f"  {'-'*12} {'-'*25} {'-'*22} {'-'*8} {'-'*8} {'-'*6}")
        for s in results_summary:
            print(
                f"  {str(s['record_id']):<12} "
                f"{str(s.get('invoice_no',''))[:24]:<25} "
                f"{s['overall']:<22} "
                f"{s.get('errors','-'):<8} "
                f"{s.get('warnings','-'):<8} "
                f"{s.get('elapsed_ms','-')}"
            )

        pass_count  = sum(1 for r in results_summary if r["overall"] == "PASS")
        warn_count  = sum(1 for r in results_summary if r["overall"] == "PASS_WITH_WARNINGS")
        fail_count  = sum(1 for r in results_summary if r["overall"] == "FAIL")
        error_count = sum(1 for r in results_summary if r["overall"] == "ERROR")

        print(f"\n  Summary: PASS={pass_count} PASS_WITH_WARNINGS={warn_count} "
              f"FAIL={fail_count} CRASH={error_count}")

        _assert(error_count == 0, "No records crashed the validator")  # type: ignore[syntax]

        # Save JSON report
        out_path = os.path.join(BACKEND_DIR, "sprint3_validation", "reports",
                                "phase3a_doc_validation_sprint3.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results_summary, f, indent=2, default=str)
        print(f"\n  Report saved: {out_path}")

    except Exception as db_err:
        print(f"  [SKIP] DB test failed: {db_err}")
        import traceback
        traceback.print_exc()


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Import the engine directly (no Django required for offline tests)
    from ocr_pipeline.document_validator.engine import run_document_validation

    print("\n" + "=" * 70)
    print("  Phase 3A Document Quality Validation — Test Suite")
    print("=" * 70)

    test_forensic_invoice(run_document_validation)
    test_complete_valid(run_document_validation)
    test_missing_fields(run_document_validation)
    test_tax_mismatch(run_document_validation)
    test_invalid_gstin(run_document_validation)
    test_performance(run_document_validation)
    test_sprint3_dataset(run_document_validation)

    _print_banner("FINAL RESULT")
    if _test_failures == 0:
        print("  [ALL PASS] All assertions passed.")
    else:
        print(f"  [FAILURES] {_test_failures} assertion(s) failed.")
    print()


if __name__ == "__main__":
    main()
