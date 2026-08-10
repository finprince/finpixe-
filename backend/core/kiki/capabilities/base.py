"""
KIKI Base Capability & Probe Result Interfaces — Phase 15 V3
================─────────────────────────────────────────────
Abstract interfaces for all pluggable Enterprise AI Capabilities.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from ..evidence.model import Evidence


from enum import Enum


class ExecutionPolicy(str, Enum):
    """Execution policy enum for capability planning."""
    EXCLUSIVE = "EXCLUSIVE"
    HYBRID = "HYBRID"
    MULTIPLE = "MULTIPLE"
    FALLBACK = "FALLBACK"
    REJECT = "REJECT"


@dataclass
class CapabilityProbeResult:
    """Detailed probe evaluation returned by BaseCapability.probe()."""
    capability_name: str
    is_match: bool
    confidence: float
    estimated_latency_ms: float
    estimated_cost: float = 0.0
    required_permissions: List[str] = field(default_factory=list)
    supported_operations: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    availability: bool = True
    priority: int = 100
    execution_params: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None



class BaseCapability(ABC):
    """Abstract Base Class for all KIKI AI Operating System Capability Plugins."""
    name: str
    description: str
    priority: int = 100

    @abstractmethod
    def probe(self, rewritten_question: str, context: Any) -> CapabilityProbeResult:
        """
        Evaluates query against capability state/indexes (< 5ms).
        Returns CapabilityProbeResult containing confidence, availability, and match status.
        """
        pass

    @abstractmethod
    def execute(
        self,
        rewritten_question: str,
        context: Any,
        probe_result: CapabilityProbeResult,
        tenant_id: str
    ) -> Evidence:
        """
        Executes capability deterministically and returns standardized Evidence object.
        """
        pass
