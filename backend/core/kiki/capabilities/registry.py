"""
KIKI Dynamic Capability Registry & AI Orchestrator Planner — Phase 15 V3
==========================================================================
Discovers, probes, and executes enterprise AI capabilities dynamically.

V3 Architecture Contract:
The Core Planner operates STRICTLY through abstract interfaces (BaseCapability, CapabilityProbeResult, Evidence).
It contains ZERO hardcoded references to concrete plugins or storage backends.
Supports single and multi-capability hybrid execution plans.
"""
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseCapability, CapabilityProbeResult, ExecutionPolicy
from ..evidence.model import Evidence
from ..config import kiki_settings
from ..logging import get_kiki_logger

logger = get_kiki_logger("capability_registry")


class CapabilityRegistry:
    """Enterprise AI Capability Registry and Execution Planner."""

    def __init__(self):
        self._capabilities: Dict[str, BaseCapability] = {}

    def register(self, capability: BaseCapability) -> None:
        """Dynamically registers a Capability Plugin."""
        self._capabilities[capability.name] = capability
        logger.info(f"[CAPABILITY REGISTRY] Registered plugin: '{capability.name}' (Priority: {capability.priority})")

    def unregister(self, capability_name: str) -> None:
        """Unregisters a plugin by name."""
        if capability_name in self._capabilities:
            del self._capabilities[capability_name]

    def probe_all(self, rewritten_question: str, context: Any) -> List[CapabilityProbeResult]:
        """
        Probes ALL registered capability plugins concurrently or sequentially (< 5ms each).
        Returns list of CapabilityProbeResult sorted by confidence and priority.
        """
        results: List[CapabilityProbeResult] = []
        for name, plugin in self._capabilities.items():
            try:
                probe_res = plugin.probe(rewritten_question, context)
                results.append(probe_res)
                logger.info(
                    f"[PROBE LOG] Plugin: '{name}' | Match: {probe_res.is_match} | "
                    f"Confidence: {probe_res.confidence:.4f} | Latency: {probe_res.estimated_latency_ms:.2f}ms"
                )
            except Exception as e:
                logger.warning(f"[PROBE ERROR] Plugin '{name}' probe failed: {str(e)}")

        # Sort probe results: matched first, then descending confidence, then priority
        results.sort(key=lambda p: (p.is_match, p.confidence, -p.priority), reverse=True)
        return results

    def plan_execution(self, probe_results: List[CapabilityProbeResult]) -> Tuple[ExecutionPolicy, List[CapabilityProbeResult]]:
        """
        Determines formal ExecutionPolicy and candidate execution plan.
        Uses centralized configuration thresholds from kiki_settings.
        """
        match_thresh = getattr(kiki_settings, "PROBE_MATCH_THRESHOLD", 0.35)
        gap_thresh = getattr(kiki_settings, "PLANNER_RELATIVE_GAP_THRESHOLD", 0.15)
        hybrid_thresh = getattr(kiki_settings, "PLANNER_HYBRID_CONFIDENCE_THRESHOLD", 0.60)

        matched = [
            p for p in probe_results
            if p.is_match and p.availability and p.confidence >= match_thresh
        ]

        if not matched:
            return ExecutionPolicy.REJECT, []

        matched.sort(key=lambda p: (p.confidence, -p.priority), reverse=True)

        if len(matched) == 1:
            return ExecutionPolicy.EXCLUSIVE, [matched[0]]

        top_1 = matched[0]
        top_2 = matched[1]
        gap = top_1.confidence - top_2.confidence

        # Relative Confidence Gap Rule: Dominant candidate gets EXCLUSIVE policy
        if gap >= gap_thresh:
            logger.info(
                f"[PLANNER 16.1] Dominant capability selected (EXCLUSIVE): '{top_1.capability_name}' "
                f"(Confidence: {top_1.confidence:.2f}, Gap: {gap:.2f})"
            )
            return ExecutionPolicy.EXCLUSIVE, [top_1]

        # Hybrid Policy Rule: Selected when both top candidates match with high native evidence confidence
        if top_1.confidence >= hybrid_thresh and top_2.confidence >= hybrid_thresh:
            logger.info(
                f"[PLANNER 16.1] HYBRID execution selected: "
                f"'{top_1.capability_name}' + '{top_2.capability_name}'"
            )
            return ExecutionPolicy.HYBRID, [top_1, top_2]

        return ExecutionPolicy.EXCLUSIVE, [top_1]

    def execute_plan(
        self,
        execution_plan: List[CapabilityProbeResult],
        rewritten_question: str,
        context: Any,
        tenant_id: str
    ) -> List[Evidence]:
        """
        Executes selected capability plugins and gathers standardized Evidence objects.
        """
        evidence_list: List[Evidence] = []
        for probe_res in execution_plan:
            plugin = self._capabilities.get(probe_res.capability_name)
            if not plugin:
                continue
            try:
                logger.info(f"[EXECUTE LOG] Running plugin: '{plugin.name}'")
                ev = plugin.execute(
                    rewritten_question=rewritten_question,
                    context=context,
                    probe_result=probe_res,
                    tenant_id=tenant_id
                )
                evidence_list.append(ev)
            except Exception as e:
                logger.error(f"[EXECUTE ERROR] Plugin '{plugin.name}' failed: {str(e)}")

        return evidence_list


# Singleton registry instance
capability_registry = CapabilityRegistry()
