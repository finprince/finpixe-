"""
KIKI Evidence & Citation Data Models — Phase 15 V3
===================================================
Standardized Evidence data structures returned by all capability plugins.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class Citation:
    """Standardized citation metadata across all knowledge sources."""
    document_name: str
    page_number: int
    section_heading: str
    document_family: str
    confidence: float


@dataclass
class Evidence:
    """
    Standardized Evidence object returned by all Capability Plugins.
    Enables uniform aggregation across multi-capability hybrid execution plans.
    """
    type: str                                # "KNOWLEDGE" | "ERP_DATA" | "WORKFLOW" | "NAVIGATION" | "CLARIFICATION"
    source: str                              # e.g., "finpixe_global_knowledge" | "customer_master" | "ui_router"
    payload: Dict[str, Any]                  # Capability-specific structured output
    summary: str                             # Human-readable executive summary of payload
    confidence: float
    citations: List[Citation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
