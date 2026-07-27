from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ActionDefinition:
    """
    Metadata representation of a business action supported by a module.
    Prepares system for future AI Action execution without architectural changes.
    """
    id: str
    name: str
    description: str
    target_node_id: str
    permissions: List[str] = field(default_factory=list)
    action_type: str = "navigate"  # "navigate", "execute", "modal"
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NavigationNode:
    """
    Rich Metadata Model for ERP Application Components & Capabilities.
    Serves as the single unified representation for Navigation, Command Palette,
    Global Search, Contextual Help, and Autonomous AI Agents.
    """
    id: str
    title: str
    route: str
    parent: Optional[str] = None
    category: str = "Core Workspace"
    permissions: List[str] = field(default_factory=list)
    breadcrumbs: List[str] = field(default_factory=list)
    description: str = ""
    search_terms: List[str] = field(default_factory=list)
    feature_tags: List[str] = field(default_factory=list)
    visibility: str = "authenticated"
    actions: List[ActionDefinition] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    business_domain: str = "General"
    related_modules: List[str] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)
    workflow_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseDiscoveryProvider(ABC):
    """
    Abstract Discovery Provider Base Class.
    Follows Open/Closed Principle — new metadata sources register custom providers
    without modifying the core discovery engine.
    """

    @abstractmethod
    def discover(self) -> List[NavigationNode]:
        """
        Discovers and returns a list of NavigationNodes from the authoritative source.
        """
        pass
