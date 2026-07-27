"""
Navigation and Application Intelligence Layer package for Kiki AI ERP Agent.
"""
from .providers.base_provider import BaseDiscoveryProvider, NavigationNode, ActionDefinition
from .application_discovery_service import ApplicationDiscoveryService
from .candidate_resolver import NavigationCandidateResolver
from .navigation_reasoner import NavigationReasoner
from .navigation_validator import NavigationValidator
from .response_builder import NavigationResponseBuilder
from .navigation_engine import NavigationEngine

__all__ = [
    "BaseDiscoveryProvider",
    "NavigationNode",
    "ActionDefinition",
    "ApplicationDiscoveryService",
    "NavigationCandidateResolver",
    "NavigationReasoner",
    "NavigationValidator",
    "NavigationResponseBuilder",
    "NavigationEngine",
]
