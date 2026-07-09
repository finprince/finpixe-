"""
Document Quality Validation Engine — Phase 3A
==============================================
Four deterministic modules that run after normalize.py, before DB persistence.

Module 1 — Mandatory Field Validation
Module 2 — Tax Arithmetic Validation
Module 3 — GSTIN Format Validation
Module 4 — Document Completeness

Rules:
  - PASS   : field/rule is valid
  - WARNING: field is present but suspect; human review recommended
  - ERROR  : field is missing or structurally invalid

No AI calls. No OCR calls. No value overwrites. No pipeline blocking.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Shared constants ───────────────────────────────────────────────────────

# Tax arithmetic tolerance — mirrors run_gst_validation_engine() which uses > 1.0
_TAX_TOLERANCE: float = 1.0

# Values that mean "no data" across the canonical schema
_EMPTY_SENTINELS = frozenset({
    "", "missing", "n/a", "—", "null", "none", "na", "0", "0.0", "0.00",
})

# Known OCR artefact HSN values flagged in the forensic trace
_SUSPICIOUS_HSN_ARTEFACTS = frozenset({"11", "tt", "9957", "1", "0"})


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class RuleResult:
    """Result of a single validation rule check."""
    module: str           # e.g. 'M01_MANDATORY'
    rule: str             # e.g. 'mandatory_invoice_no'
    status: str           # 'PASS' | 'WARNING' | 'ERROR'
    message: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentValidationReport:
    """Aggregated output of the full validation run."""
    invoice_no: str
    validated_at: str
    overall: str          # 'PASS' | 'PASS_WITH_WARNINGS' | 'FAIL'
    rules: List[RuleResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    elapsed_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invoice_no": self.invoice_no,
            "validated_at": self.validated_at,
            "overall": self.overall,
            "elapsed_ms": self.elapsed_ms,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "rules": [r.to_dict() for r in self.rules],
        }

    def summary_table(self) -> str:
        """Human-readable summary for logs."""
        lines = [
            "",
            f"  Invoice No : {self.invoice_no}",
            f"  Validated  : {self.validated_at}",
            f"  Overall    : {self.overall}",
            "",
            f"  {'Rule':<45} {'Status'}",
            f"  {'-'*45} {'-'*18}",
        ]
        for r in self.rules:
            lines.append(f"  {r.rule:<45} {r.status}")
        lines.append("")
        return "\n".join(lines)


# ── Utility helpers ────────────────────────────────────────────────────────

def _to_float(val: Any) -> float:
    """
    Safe float coercion matching the to_dec() pattern used across pipeline.py
    and run_gst_validation_engine().
    """
    try:
        if val is None:
            return 0.0
        s = str(val).replace("₹", "").replace(",", "").replace(" ", "").strip()
        return float(s) if s else 0.0
    except (ValueError, TypeError):
        return 0.0


def _is_empty(val: Any) -> bool:
    """Return True if val carries no meaningful content."""
    if val is None:
        return True
    s = str(val).strip().lower()
    return s in _EMPTY_SENTINELS


# ── MODULE 1: Mandatory Field Validation ──────────────────────────────────

def _run_mandatory_fields(invoice: Dict[str, Any]) -> List[RuleResult]:
    """
    Checks that all GST-compliance mandatory fields are present and non-empty.
    Does not modify any value.
    """
    results: List[RuleResult] = []

    # Resolve grand total from all canonical schema variants
    grand_total = _to_float(
        invoice.get("total_invoice_value")
        or invoice.get("invoice_total")
        or invoice.get("total_amount")
        or invoice.get("grand_total")
    )

    # Resolve vendor GSTIN from all canonical schema variants
    vendor_gstin = (
        invoice.get("vendor_gstin")
        or invoice.get("gstin")
        or invoice.get("canonical_gstin")
        or ""
    ).strip()

    scalar_checks = [
        ("invoice_no",   "Invoice Number", invoice.get("invoice_no")),
        ("invoice_date", "Invoice Date",   invoice.get("invoice_date")),
        ("vendor_name",  "Vendor Name",    invoice.get("vendor_name")),
        ("vendor_gstin", "Vendor GSTIN",   vendor_gstin),
        ("grand_total",  "Grand Total",    grand_total if grand_total > 0.0 else None),
    ]

    for key, label, value in scalar_checks:
        if _is_empty(value):
            results.append(RuleResult(
                module="M01_MANDATORY",
                rule=f"mandatory_{key}",
                status="ERROR",
                message=f"{label} is missing or empty",
                actual=value,
            ))
        else:
            results.append(RuleResult(
                module="M01_MANDATORY",
                rule=f"mandatory_{key}",
                status="PASS",
                message=f"{label} present",
                actual=str(value)[:80],
            ))

    # Line items — must have at least one
    items = invoice.get("items") or []
    if not isinstance(items, list) or len(items) == 0:
        results.append(RuleResult(
            module="M01_MANDATORY",
            rule="mandatory_line_items",
            status="ERROR",
            message="No line items found",
            actual=0,
        ))
    else:
        results.append(RuleResult(
            module="M01_MANDATORY",
            rule="mandatory_line_items",
            status="PASS",
            message=f"{len(items)} line item(s) present",
            actual=len(items),
        ))

    return results


# ── MODULE 2: Tax Arithmetic Validation ──────────────────────────────────

def _run_tax_arithmetic(invoice: Dict[str, Any]) -> List[RuleResult]:
    """
    Verifies: subtotal + CGST + SGST + IGST + cess + round_off ≈ grand_total.

    Tolerance: ₹1.00 — identical to the threshold used in
    run_gst_validation_engine() (pipeline.py line 2264: `difference_amount > 1.0`).

    This module is read-only — it NEVER overwrites any extracted value.
    It complements run_gst_validation_engine() which runs post-DB on user
    resolution choice. This module runs pre-DB and produces an audit record.
    """
    results: List[RuleResult] = []

    grand_total = _to_float(
        invoice.get("total_invoice_value")
        or invoice.get("invoice_total")
        or invoice.get("total_amount")
        or invoice.get("grand_total")
    )

    if grand_total == 0.0:
        results.append(RuleResult(
            module="M02_TAX",
            rule="tax_grand_total_nonzero",
            status="WARNING",
            message="Grand total is zero -- tax arithmetic skipped",
            actual=0.0,
        ))
        return results

    taxable   = _to_float(invoice.get("total_taxable_value") or invoice.get("subtotal"))
    cgst      = _to_float(invoice.get("total_cgst") or invoice.get("cgst"))
    sgst      = _to_float(invoice.get("total_sgst") or invoice.get("sgst"))
    igst      = _to_float(invoice.get("total_igst") or invoice.get("igst"))
    cess      = _to_float(invoice.get("total_cess") or invoice.get("cess") or 0.0)
    round_off = _to_float(invoice.get("round_off") or 0.0)

    computed = round(taxable + cgst + sgst + igst + cess + round_off, 2)
    diff = abs(computed - grand_total)

    if diff <= _TAX_TOLERANCE:
        results.append(RuleResult(
            module="M02_TAX",
            rule="tax_arithmetic",
            status="PASS",
            message=f"Tax arithmetic balances (diff=Rs.{diff:.2f}, tolerance=Rs.{_TAX_TOLERANCE:.2f})",
            expected=grand_total,
            actual=computed,
        ))
    else:
        results.append(RuleResult(
            module="M02_TAX",
            rule="tax_arithmetic",
            status="ERROR",
            message=(
                f"Tax arithmetic mismatch: "
                f"computed Rs.{computed:.2f} != extracted grand total Rs.{grand_total:.2f} "
                f"(diff=Rs.{diff:.2f})"
            ),
            expected=grand_total,
            actual=computed,
        ))

    return results


# ── MODULE 3: GSTIN Format Validation ────────────────────────────────────

def _check_one_gstin(raw: str, label: str) -> RuleResult:
    """
    Validates a single GSTIN string using the helpers already defined in
    normalize.py (GSTIN_PATTERN and validate_gstin_checksum).
    Never corrects the value.
    """
    # Late import to avoid circular imports at module load time.
    # These helpers are already thoroughly tested in the production pipeline.
    from ocr_pipeline.normalize import GSTIN_PATTERN, validate_gstin_checksum  # type: ignore[import]

    tag = label.lower().replace(" ", "_")
    val = str(raw).strip().upper() if raw else ""

    if not val or val.lower() in _EMPTY_SENTINELS:
        return RuleResult(
            module="M03_GSTIN",
            rule=f"gstin_present_{tag}",
            status="WARNING",
            message=f"{label}: GSTIN is empty — B2C invoice or OCR gap",
            actual=val,
        )

    if len(val) != 15:
        return RuleResult(
            module="M03_GSTIN",
            rule=f"gstin_length_{tag}",
            status="ERROR",
            message=f"{label}: GSTIN length is {len(val)}, expected 15",
            actual=val,
        )

    if not GSTIN_PATTERN.match(val):
        return RuleResult(
            module="M03_GSTIN",
            rule=f"gstin_format_{tag}",
            status="ERROR",
            message=f"{label}: GSTIN does not match required format",
            actual=val,
        )

    if not validate_gstin_checksum(val):
        return RuleResult(
            module="M03_GSTIN",
            rule=f"gstin_checksum_{tag}",
            status="WARNING",
            message=f"{label}: GSTIN checksum failed — possible OCR character error",
            actual=val,
        )

    return RuleResult(
        module="M03_GSTIN",
        rule=f"gstin_valid_{tag}",
        status="PASS",
        message=f"{label}: GSTIN is structurally valid",
        actual=val,
    )


def _run_gstin_format(invoice: Dict[str, Any]) -> List[RuleResult]:
    results: List[RuleResult] = []

    vendor_gstin = (
        invoice.get("vendor_gstin")
        or invoice.get("gstin")
        or invoice.get("canonical_gstin")
        or ""
    ).strip().upper()

    buyer_gstin = (
        invoice.get("buyer_gstin")
        or invoice.get("raw_buyer_gstin")
        or invoice.get("canonical_buyer_gstin")
        or ""
    ).strip().upper()

    results.append(_check_one_gstin(vendor_gstin, "Vendor GSTIN"))

    # Buyer GSTIN is optional on B2C invoices — WARNING not ERROR if absent
    results.append(_check_one_gstin(buyer_gstin, "Buyer GSTIN"))

    return results


# ── MODULE 4: Document Completeness ──────────────────────────────────────

def _run_document_completeness(invoice: Dict[str, Any]) -> List[RuleResult]:
    """
    Checks that the four expected document sections are present.
    Does not attempt to reconstruct missing sections.
    """
    results: List[RuleResult] = []

    # Header — must have invoice_no OR invoice_date
    has_header = not _is_empty(invoice.get("invoice_no")) or not _is_empty(invoice.get("invoice_date"))
    results.append(RuleResult(
        module="M04_COMPLETENESS",
        rule="section_header",
        status="PASS" if has_header else "ERROR",
        message="Header section present" if has_header else
                "Header section missing (no invoice_no or invoice_date)",
    ))

    # Vendor block — must have vendor_name OR (g)stin
    has_vendor = (
        not _is_empty(invoice.get("vendor_name"))
        or not _is_empty(invoice.get("vendor_gstin"))
        or not _is_empty(invoice.get("gstin"))
        or not _is_empty(invoice.get("bill_from"))
    )
    results.append(RuleResult(
        module="M04_COMPLETENESS",
        rule="section_vendor",
        status="PASS" if has_vendor else "ERROR",
        message="Vendor block present" if has_vendor else
                "Vendor block missing (no vendor_name, gstin, or bill_from)",
    ))

    # Buyer block — optional on B2C; WARNING not ERROR
    has_buyer = (
        not _is_empty(invoice.get("buyer_name"))
        or not _is_empty(invoice.get("buyer_gstin"))
        or not _is_empty(invoice.get("bill_to"))
    )
    results.append(RuleResult(
        module="M04_COMPLETENESS",
        rule="section_buyer",
        status="PASS" if has_buyer else "WARNING",
        message="Buyer block present" if has_buyer else
                "Buyer block empty — B2C invoice or OCR gap in buyer region",
    ))

    # Item table — must have at least one item
    items = invoice.get("items") or []
    has_items = isinstance(items, list) and len(items) > 0
    results.append(RuleResult(
        module="M04_COMPLETENESS",
        rule="section_items",
        status="PASS" if has_items else "ERROR",
        message=f"Item table has {len(items)} item(s)" if has_items else
                "Item table is empty",
        actual=len(items) if isinstance(items, list) else 0,
    ))

    # Totals — must be non-zero
    grand_total = _to_float(
        invoice.get("total_invoice_value")
        or invoice.get("invoice_total")
        or invoice.get("total_amount")
        or invoice.get("grand_total")
    )
    results.append(RuleResult(
        module="M04_COMPLETENESS",
        rule="section_totals",
        status="PASS" if grand_total > 0.0 else "WARNING",
        message=f"Totals present (grand total=Rs.{grand_total:.2f})" if grand_total > 0.0 else
                "Totals section missing or zero",
        actual=grand_total,
    ))

    return results


# ── ORCHESTRATOR ──────────────────────────────────────────────────────────

def run_document_validation(
    invoice: Dict[str, Any],
    tenant_id: str = "",
    record_id: str = "",
) -> DocumentValidationReport:
    """
    Main entry point for the Document Quality Validation Layer.

    Runs all four modules in sequence, collects results, and returns a
    DocumentValidationReport. This function NEVER raises — all exceptions
    are caught and converted to WARNING results so the pipeline always
    continues.

    Args:
        invoice:   The canonical invoice dict produced by get_ui_payload().
        tenant_id: Used only in log messages for traceability.
        record_id: Used only in log messages for traceability.

    Returns:
        DocumentValidationReport with overall status PASS | PASS_WITH_WARNINGS | FAIL.
    """
    from datetime import datetime, timezone as _tz

    t_start = time.monotonic()
    validated_at = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    invoice_no = str(
        invoice.get("invoice_no")
        or invoice.get("supplier_invoice_no")
        or ""
    ).strip()

    all_rules: List[RuleResult] = []

    # M01 — Mandatory Fields
    try:
        all_rules.extend(_run_mandatory_fields(invoice))
    except Exception as exc:
        logger.error(f"[DOC_VAL_M01_ERROR] record={record_id} inv={invoice_no} err={exc}")
        all_rules.append(RuleResult("M01_MANDATORY", "module_crash", "WARNING", f"Module crashed: {exc}"))

    # M02 — Tax Arithmetic
    try:
        all_rules.extend(_run_tax_arithmetic(invoice))
    except Exception as exc:
        logger.error(f"[DOC_VAL_M02_ERROR] record={record_id} inv={invoice_no} err={exc}")
        all_rules.append(RuleResult("M02_TAX", "module_crash", "WARNING", f"Module crashed: {exc}"))

    # M03 — GSTIN Format
    try:
        all_rules.extend(_run_gstin_format(invoice))
    except Exception as exc:
        logger.error(f"[DOC_VAL_M03_ERROR] record={record_id} inv={invoice_no} err={exc}")
        all_rules.append(RuleResult("M03_GSTIN", "module_crash", "WARNING", f"Module crashed: {exc}"))

    # M04 — Document Completeness
    try:
        all_rules.extend(_run_document_completeness(invoice))
    except Exception as exc:
        logger.error(f"[DOC_VAL_M04_ERROR] record={record_id} inv={invoice_no} err={exc}")
        all_rules.append(RuleResult("M04_COMPLETENESS", "module_crash", "WARNING", f"Module crashed: {exc}"))

    # Aggregate status
    errors   = [r.message for r in all_rules if r.status == "ERROR"]
    warnings = [r.message for r in all_rules if r.status == "WARNING"]

    if errors:
        overall = "FAIL"
    elif warnings:
        overall = "PASS_WITH_WARNINGS"
    else:
        overall = "PASS"

    elapsed_ms = int((time.monotonic() - t_start) * 1_000)

    report = DocumentValidationReport(
        invoice_no=invoice_no,
        validated_at=validated_at,
        overall=overall,
        rules=all_rules,
        errors=errors,
        warnings=warnings,
        elapsed_ms=elapsed_ms,
    )

    logger.info(
        f"[DOC_VAL_COMPLETE] record={record_id} tenant={tenant_id} "
        f"invoice_no='{invoice_no}' overall={overall} "
        f"errors={len(errors)} warnings={len(warnings)} elapsed_ms={elapsed_ms}ms"
    )
    if overall != "PASS":
        logger.info("[DOC_VAL_SUMMARY]%s", report.summary_table())

    return report
