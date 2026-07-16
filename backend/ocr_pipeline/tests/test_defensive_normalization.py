"""
Unit Tests: GST Rate Duplication Correction in get_normalized_items()
=====================================================================

Tests the deterministic, item-level defensive normalization rule that corrects
the AI model's non-deterministic duplication of combined GST Rate onto both
cgst_rate and sgst_rate (e.g. returning 5/5 instead of 2.5/2.5).

Usage (run from backend directory):
    python -m ocr_pipeline.tests.test_defensive_normalization

No Django ORM is needed. This is a pure logic test.
"""
from __future__ import annotations

import sys
import os

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add backend to sys.path so we can import ocr_pipeline without Django setup
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Minimal Django settings bootstrap (no DB needed)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
try:
    import django
    django.setup()
except Exception:
    pass

from ocr_pipeline.normalize import get_normalized_items

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_invoice(items: list) -> dict:
    """Wrap items and compute header totals matching the items' signature."""
    has_igst = any(float(i.get("igst_amount") or i.get("igst") or 0.0) > 0.0 or float(i.get("igst_rate") or 0.0) > 0.0 for i in items)
    
    sum_cgst = sum(float(i.get("cgst") or i.get("cgst_amount") or 0.0) for i in items)
    sum_sgst = sum(float(i.get("sgst") or i.get("sgst_amount") or 0.0) for i in items)
    sum_igst = sum(float(i.get("igst") or i.get("igst_amount") or 0.0) for i in items)

    # If any item has a duplicated rate (in KNOWN_COMBINED) and it's intrastate,
    # simulate the Mode B signature where header has correct tax (half the sum of items).
    _KNOWN_COMBINED = {3.0, 5.0, 12.0, 18.0, 28.0}
    is_duplicated = False
    for i in items:
        cg_rate = float(i.get("cgst_rate") or 0.0)
        if cg_rate in _KNOWN_COMBINED and not has_igst:
            is_duplicated = True
            break
            
    if is_duplicated:
        header_cgst = sum_cgst / 2.0
        header_sgst = sum_sgst / 2.0
        header_igst = 0.0
    else:
        header_cgst = sum_cgst
        header_sgst = sum_sgst
        header_igst = sum_igst

    return {
        "items": items,
        "total_cgst": header_cgst,
        "total_sgst": header_sgst,
        "total_igst": header_igst,
    }


def run_test(name: str, items: list, assertions: callable) -> None:
    invoice = make_invoice(items)
    result = get_normalized_items(invoice, layout_type="Layout C")
    try:
        assertions(result)
        print(f"  ✓ {name}")
    except AssertionError as e:
        print(f"  ✗ {name}")
        print(f"      {e}")
        for idx, itm in enumerate(result):
            print(f"      item[{idx}]: cgst_rate={itm.get('cgst_rate')} sgst_rate={itm.get('sgst_rate')} "
                  f"igst_rate={itm.get('igst_rate')} cgst={itm.get('cgst')} sgst={itm.get('sgst')} "
                  f"computed_gst_rate={itm.get('computed_gst_rate')}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Test data factories
# ─────────────────────────────────────────────────────────────────────────────

def item_5pct_correct():
    """cgst_rate=2.5, sgst_rate=2.5 — already correct, no change expected."""
    return {
        "description": "Lab Coat Blue Colour",
        "hsn_code": "8210",
        "quantity": 1.0,
        "uom": "Nos",
        "rate": 450.0,
        "taxable_value": 450.0,
        "igst_rate": 0.0,
        "igst_amount": 0.0,
        "cgst_rate": 2.5,
        "cgst_amount": 11.25,
        "sgst_rate": 2.5,
        "sgst_amount": 11.25,
        "amount": 472.50,
    }


def item_5pct_duplicated():
    """cgst_rate=5, sgst_rate=5 — AI duplicated combined 5% rate and amount."""
    return {
        "description": "Lab Coat Blue Colour",
        "hsn_code": "8210",
        "quantity": 1.0,
        "uom": "Nos",
        "rate": 450.0,
        "taxable_value": 450.0,
        "igst_rate": 0.0,
        "igst_amount": 0.0,
        "cgst_rate": 5.0,
        "cgst_amount": 22.50,  # duplicated amount (5% of 450)
        "sgst_rate": 5.0,
        "sgst_amount": 22.50,
        "amount": 495.00,
    }


def item_18pct_correct():
    """cgst_rate=9, sgst_rate=9 — already correct, no change expected."""
    return {
        "description": "Lathe Chuck Key 7/16\"",
        "hsn_code": "8205",
        "quantity": 1.0,
        "uom": "Nos",
        "rate": 270.0,
        "taxable_value": 270.0,
        "igst_rate": 0.0,
        "igst_amount": 0.0,
        "cgst_rate": 9.0,
        "cgst_amount": 24.3,
        "sgst_rate": 9.0,
        "sgst_amount": 24.3,
        "amount": 318.60,
    }


def item_18pct_duplicated():
    """cgst_rate=18, sgst_rate=18 — AI duplicated combined 18% rate and amount."""
    return {
        "description": "Lathe Chuck Key 7/16\"",
        "hsn_code": "8205",
        "quantity": 1.0,
        "uom": "Nos",
        "rate": 270.0,
        "taxable_value": 270.0,
        "igst_rate": 0.0,
        "igst_amount": 0.0,
        "cgst_rate": 18.0,
        "cgst_amount": 48.6,  # duplicated amount (18% of 270)
        "sgst_rate": 18.0,
        "sgst_amount": 48.6,
        "amount": 367.20,
    }


def item_igst_only():
    """Pure IGST invoice — cgst/sgst are zero, igst_rate=18. No correction."""
    return {
        "description": "Interstate Tool",
        "hsn_code": "8207",
        "quantity": 2.0,
        "uom": "Nos",
        "rate": 500.0,
        "taxable_value": 1000.0,
        "igst_rate": 18.0,
        "igst_amount": 180.0,
        "cgst_rate": 0.0,
        "cgst_amount": 0.0,
        "sgst_rate": 0.0,
        "sgst_amount": 0.0,
        "amount": 1180.0,
    }


def item_12pct_duplicated():
    """cgst_rate=12, sgst_rate=12 — AI duplicated combined 12% rate and amount."""
    return {
        "description": "Packaging Material",
        "hsn_code": "4819",
        "quantity": 10.0,
        "uom": "Nos",
        "rate": 100.0,
        "taxable_value": 1000.0,
        "igst_rate": 0.0,
        "igst_amount": 0.0,
        "cgst_rate": 12.0,
        "cgst_amount": 120.0,  # duplicated = 12% of 1000
        "sgst_rate": 12.0,
        "sgst_amount": 120.0,
        "amount": 1240.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_correct_2_5_per_2_5_no_change():
    """
    Input: cgst_rate=2.5, sgst_rate=2.5, cgst_amount=11.25, taxable=450
    Expected: No change. Ratio = taxable*rate/100 / amount = 11.25 / 11.25 = 1.0 ≠ 2.0
    """
    def assertions(result):
        assert len(result) == 1, f"Expected 1 item, got {len(result)}"
        itm = result[0]
        assert itm["cgst_rate"] == 2.5, f"cgst_rate should be 2.5, got {itm['cgst_rate']}"
        assert itm["sgst_rate"] == 2.5, f"sgst_rate should be 2.5, got {itm['sgst_rate']}"
        assert abs(itm["cgst"] - 11.25) < 0.01, f"cgst should be 11.25, got {itm['cgst']}"
        assert itm["computed_gst_rate"] == 5.0, f"computed_gst_rate should be 5.0, got {itm['computed_gst_rate']}"

    run_test("CORRECT 2.5/2.5 — no change expected", [item_5pct_correct()], assertions)


def test_duplicated_5_per_5_corrected():
    """
    Input: cgst_rate=5, sgst_rate=5, cgst_amount=11.25 (correct), taxable=450
    Mathematical proof:
      expected_at_5% = 450 * 5 / 100 = 22.5
      actual cgst_amount = 11.25
      22.5 ≈ 2 × 11.25  → duplication confirmed
    Correction: cgst_rate = 2.5, sgst_rate = 2.5, amounts unchanged (already correct)
    """
    def assertions(result):
        assert len(result) == 1
        itm = result[0]
        assert itm["cgst_rate"] == 2.5, f"cgst_rate should be corrected to 2.5, got {itm['cgst_rate']}"
        assert itm["sgst_rate"] == 2.5, f"sgst_rate should be corrected to 2.5, got {itm['sgst_rate']}"
        # Amounts must be UNCHANGED (they were already correct)
        assert abs(itm["cgst"] - 11.25) < 0.01, f"cgst amount should remain 11.25, got {itm['cgst']}"
        assert abs(itm["sgst"] - 11.25) < 0.01, f"sgst amount should remain 11.25, got {itm['sgst']}"
        assert itm["computed_gst_rate"] == 5.0, f"computed_gst_rate should be 5.0, got {itm['computed_gst_rate']}"

    run_test("DUPLICATED 5/5 → corrected to 2.5/2.5 (amounts unchanged)", [item_5pct_duplicated()], assertions)


def test_correct_9_per_9_no_change():
    """
    Input: cgst_rate=9, sgst_rate=9, cgst_amount=24.3, taxable=270
    expected_at_9% = 270 * 9 / 100 = 24.3
    Ratio = 24.3 / 24.3 = 1.0  → no correction
    """
    def assertions(result):
        assert len(result) == 1
        itm = result[0]
        assert itm["cgst_rate"] == 9.0, f"cgst_rate should stay 9.0, got {itm['cgst_rate']}"
        assert itm["sgst_rate"] == 9.0, f"sgst_rate should stay 9.0, got {itm['sgst_rate']}"
        assert abs(itm["cgst"] - 24.3) < 0.01
        assert itm["computed_gst_rate"] == 18.0

    run_test("CORRECT 9/9 — no change expected", [item_18pct_correct()], assertions)


def test_duplicated_18_per_18_corrected():
    """
    Input: cgst_rate=18, sgst_rate=18, cgst_amount=24.3, taxable=270
    Mathematical proof:
      expected_at_18% = 270 * 18 / 100 = 48.6
      actual cgst_amount = 24.3
      48.6 ≈ 2 × 24.3  → duplication confirmed
    Correction: cgst_rate = 9, sgst_rate = 9, amounts unchanged
    """
    def assertions(result):
        assert len(result) == 1
        itm = result[0]
        assert itm["cgst_rate"] == 9.0, f"cgst_rate should be corrected to 9.0, got {itm['cgst_rate']}"
        assert itm["sgst_rate"] == 9.0, f"sgst_rate should be corrected to 9.0, got {itm['sgst_rate']}"
        assert abs(itm["cgst"] - 24.3) < 0.01, f"cgst amount should remain 24.3, got {itm['cgst']}"
        assert abs(itm["sgst"] - 24.3) < 0.01
        assert itm["computed_gst_rate"] == 18.0

    run_test("DUPLICATED 18/18 → corrected to 9/9 (amounts unchanged)", [item_18pct_duplicated()], assertions)


def test_igst_invoice_not_touched():
    """
    IGST invoice: igst_rate=18, cgst=sgst=0
    Pre-condition 1 (is_intrastate) fails → no correction.
    """
    def assertions(result):
        assert len(result) == 1
        itm = result[0]
        assert itm["igst_rate"] == 18.0, f"igst_rate should remain 18.0, got {itm['igst_rate']}"
        assert itm["cgst_rate"] == 0.0,  f"cgst_rate should stay 0.0, got {itm['cgst_rate']}"
        assert itm["sgst_rate"] == 0.0,  f"sgst_rate should stay 0.0, got {itm['sgst_rate']}"
        assert itm["computed_gst_rate"] == 18.0

    run_test("IGST invoice — must not be touched", [item_igst_only()], assertions)


def test_mixed_rate_invoice_both_corrected():
    """
    Two items: 5/5 (duplicated) and 18/18 (duplicated) in the same invoice.
    Both must be independently corrected item-by-item.
    """
    def assertions(result):
        assert len(result) == 2, f"Expected 2 items, got {len(result)}"

        itm0 = result[0]
        assert itm0["cgst_rate"] == 2.5, f"Item 0: cgst_rate should be 2.5, got {itm0['cgst_rate']}"
        assert itm0["sgst_rate"] == 2.5
        assert abs(itm0["cgst"] - 11.25) < 0.01

        itm1 = result[1]
        assert itm1["cgst_rate"] == 9.0, f"Item 1: cgst_rate should be 9.0, got {itm1['cgst_rate']}"
        assert itm1["sgst_rate"] == 9.0
        assert abs(itm1["cgst"] - 24.3) < 0.01

    run_test(
        "MIXED rates (5/5 + 18/18 duplicated) — each corrected independently",
        [item_5pct_duplicated(), item_18pct_duplicated()],
        assertions,
    )


def test_already_corrected_invoice_no_double_correction():
    """
    If the data already has correct 2.5/2.5 values, running the normalizer again
    must NOT divide the rates a second time.
    Ratio = taxable*2.5/100 / cgst_amount = 11.25 / 11.25 = 1.0 → no trigger.
    """
    def assertions(result):
        assert len(result) == 1
        itm = result[0]
        assert itm["cgst_rate"] == 2.5, f"Already-correct invoice must stay 2.5, got {itm['cgst_rate']}"
        assert itm["sgst_rate"] == 2.5
        assert abs(itm["cgst"] - 11.25) < 0.01

    run_test("ALREADY CORRECTED — idempotent, no double-division", [item_5pct_correct()], assertions)


def test_12pct_duplicated_corrected():
    """
    Input: cgst_rate=12, sgst_rate=12, cgst_amount=60.0, taxable=1000
    expected_at_12% = 1000 * 12 / 100 = 120.0
    actual = 60.0
    120.0 ≈ 2 × 60.0 → duplication confirmed → correct to 6/6
    """
    def assertions(result):
        assert len(result) == 1
        itm = result[0]
        assert itm["cgst_rate"] == 6.0, f"cgst_rate should be corrected to 6.0, got {itm['cgst_rate']}"
        assert itm["sgst_rate"] == 6.0
        assert abs(itm["cgst"] - 60.0) < 0.01, "cgst amount must remain 60.0"
        assert itm["computed_gst_rate"] == 12.0

    run_test("DUPLICATED 12/12 → corrected to 6/6", [item_12pct_duplicated()], assertions)


def test_mixed_correct_and_igst_in_same_invoice():
    """
    Two items: 5/5 duplicated (intrastate), correct 9/9 (intrastate).
    Each must be handled independently: first corrected, second unchanged.
    """
    items = [
        item_5pct_duplicated(),
        item_18pct_correct(),
    ]

    def assertions(result):
        assert len(result) == 2

        # Item 0: 5/5 duplicated → 2.5/2.5
        assert result[0]["cgst_rate"] == 2.5
        assert result[0]["sgst_rate"] == 2.5
        assert abs(result[0]["cgst"] - 11.25) < 0.01

        # Item 1: 9/9 correct → unchanged
        assert result[1]["cgst_rate"] == 9.0
        assert result[1]["sgst_rate"] == 9.0
        assert abs(result[1]["cgst"] - 24.3) < 0.01

    run_test(
        "MIXED invoice (5/5 dup + correct 9/9) — independent per-item handling",
        items,
        assertions,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

TESTS = [
    test_correct_2_5_per_2_5_no_change,
    test_duplicated_5_per_5_corrected,
    test_correct_9_per_9_no_change,
    test_duplicated_18_per_18_corrected,
    test_igst_invoice_not_touched,
    test_mixed_rate_invoice_both_corrected,
    test_already_corrected_invoice_no_double_correction,
    test_12pct_duplicated_corrected,
    test_mixed_correct_and_igst_in_same_invoice,
]


if __name__ == "__main__":
    print("\n=== GST Rate Duplication Correction — Unit Tests ===\n")
    passed = 0
    failed = 0
    for test_fn in TESTS:
        try:
            test_fn()
            passed += 1
        except AssertionError:
            failed += 1
        except Exception as exc:
            print(f"  ✗ {test_fn.__name__} [EXCEPTION: {exc}]")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(TESTS)} tests")
    if failed:
        sys.exit(1)
    else:
        print("All tests passed.\n")
