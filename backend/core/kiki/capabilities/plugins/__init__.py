"""
KIKI Capability Plugins Package — Phase 15 V3
==============================================
Registers all capability plugins with the dynamic CapabilityRegistry.
"""
from ..registry import capability_registry
from .knowledge_plugin import KnowledgeRetrievalCapability
from .erp_plugin import ERPAnalyticsCapability
from .navigation_plugin import NavigationCapability
from .workflow_plugin import WorkflowAutomationCapability

# Instantiate and register capability plugins automatically
knowledge_plugin = KnowledgeRetrievalCapability()
erp_plugin = ERPAnalyticsCapability()
navigation_plugin = NavigationCapability()
workflow_plugin = WorkflowAutomationCapability()

capability_registry.register(knowledge_plugin)
capability_registry.register(erp_plugin)
capability_registry.register(navigation_plugin)
capability_registry.register(workflow_plugin)

__all__ = [
    "knowledge_plugin",
    "erp_plugin",
    "navigation_plugin",
    "workflow_plugin"
]
