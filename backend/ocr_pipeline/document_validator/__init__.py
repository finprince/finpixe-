"""
Document Quality Validation Layer — Phase 3A
=============================================
Minimal, deterministic, production-safe validation that runs AFTER normalize.py
and BEFORE database persistence.

Exposes a single callable: run_document_validation(invoice, tenant_id, record_id)

Design constraints:
  - Never modifies extracted invoice values
  - Never calls AI, OCR, or any external service
  - Never blocks the pipeline (all exceptions are caught internally)
  - Reuses existing GSTIN helpers from normalize.py
  - Uses the same ₹1.00 tax tolerance already in run_gst_validation_engine()
"""

from .engine import run_document_validation, DocumentValidationReport, RuleResult

__all__ = ["run_document_validation", "DocumentValidationReport", "RuleResult"]
