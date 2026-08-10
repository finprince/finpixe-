"""
KIKI Navigation Capability Plugin — Phase 15 V3
================================================
Plugin capability for UI route resolving and workspace navigation.
"""
from typing import Dict, Any, List, Optional
from ..base import BaseCapability, CapabilityProbeResult
from ...evidence.model import Evidence
from ...ontology import ontology_graph
from ...logging import get_kiki_logger

logger = get_kiki_logger("navigation_plugin")


class NavigationCapability(BaseCapability):
    """Navigation Capability Plugin for workspace routing."""

    name = "NavigationCapability"
    description = "Handles page navigation and workspace routing requests."
    priority = 70

    def probe(self, rewritten_question: str, context: Any) -> CapabilityProbeResult:
        """Probes navigation intent."""
        msg_lower = rewritten_question.lower()
        nav_verbs = ["open", "go to", "navigate to", "take me to", "show page", "open page", "open dashboard"]
        is_match = any(msg_lower.startswith(verb) or verb in msg_lower for verb in nav_verbs)
        domain = ontology_graph.resolve_domain_for_term(rewritten_question) or "General"

        logger.info(f"[NAV PROBE] Question: '{rewritten_question}' | Match: {is_match} | Domain: {domain}")

        return CapabilityProbeResult(
            capability_name=self.name,
            is_match=is_match,
            confidence=0.95 if is_match else 0.0,
            estimated_latency_ms=1.0,
            supported_operations=["ui_navigation"],
            availability=True,
            priority=self.priority,
            execution_params={"domain": domain}
        )

    def execute(
        self,
        rewritten_question: str,
        context: Any,
        probe_result: CapabilityProbeResult,
        tenant_id: str
    ) -> Evidence:
        """Executes navigation action and returns Evidence."""
        domain_name = probe_result.execution_params.get("domain") or "General"
        route = f"/{domain_name.lower().replace(' ', '-')}"

        reply_text = f"Navigating to {domain_name} workspace."
        action_card = {
            "title": f"Open {domain_name}",
            "action_type": "NAVIGATE",
            "route": route
        }

        return Evidence(
            type="NAVIGATION",
            source="ui_router",
            payload={
                "domain": domain_name,
                "route": route,
                "action_cards": [action_card],
                "synthesis_text": reply_text
            },
            summary=reply_text,
            confidence=0.99,
            citations=[],
            metadata={"route": route}
        )
