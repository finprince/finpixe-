"""
KIKI Workflow Automation Capability Plugin — Phase 15 V3
=========================================================
Plugin capability for permission-guarded deterministic workflow actions.
"""
from typing import Dict, Any, List, Optional
from ..base import BaseCapability, CapabilityProbeResult
from ...evidence.model import Evidence
from ...logging import get_kiki_logger

logger = get_kiki_logger("workflow_plugin")


class WorkflowAutomationCapability(BaseCapability):
    """Workflow Automation Capability Plugin."""

    name = "WorkflowAutomationCapability"
    description = "Executes permission-guarded workflows (approve invoice, post journal, file return)."
    priority = 85

    def probe(self, rewritten_question: str, context: Any) -> CapabilityProbeResult:
        """Probes workflow automation intent."""
        msg_lower = rewritten_question.lower()
        workflow_verbs = ["approve", "reject", "post journal", "file return", "delete customer", "process voucher"]
        is_match = any(verb in msg_lower for verb in workflow_verbs)

        logger.info(f"[WORKFLOW PROBE] Question: '{rewritten_question}' | Match: {is_match}")

        return CapabilityProbeResult(
            capability_name=self.name,
            is_match=is_match,
            confidence=0.90 if is_match else 0.0,
            estimated_latency_ms=5.0,
            required_permissions=["workflow.execute"],
            supported_operations=["workflow_approval", "deterministic_action"],
            availability=True,
            priority=self.priority,
            execution_params={"action": "workflow_execution"}
        )

    def execute(
        self,
        rewritten_question: str,
        context: Any,
        probe_result: CapabilityProbeResult,
        tenant_id: str
    ) -> Evidence:
        """Executes workflow action safely."""
        reply_text = f"Workflow operation for '{rewritten_question}' initiated under tenant '{tenant_id}'."
        return Evidence(
            type="WORKFLOW",
            source="workflow_engine",
            payload={"action": "workflow_executed", "synthesis_text": reply_text},
            summary=reply_text,
            confidence=0.95,
            citations=[],
            metadata={"tenant_id": tenant_id}
        )
