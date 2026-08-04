import threading
from typing import List, Dict, Any, Optional
from .providers.base_provider import BaseDiscoveryProvider, NavigationNode, ActionDefinition
from .providers.route_provider import RouteDiscoveryProvider
from ..utils.logger import kiki_logger

class ApplicationDiscoveryService:
    """
    Component 1 — Application Discovery Service
    Aggregates pluggable discovery providers to build and maintain the unified,
    in-memory Application Intelligence Graph.
    Implements single-source metadata ownership and thread-safe caching.
    Exposes public platform APIs for Navigation, Global Search, Command Palette, and AI Agents.
    """
    _providers: List[BaseDiscoveryProvider] = []
    _cached_nodes: Optional[List[NavigationNode]] = None
    _cached_map: Optional[Dict[str, NavigationNode]] = None
    _lock = threading.Lock()

    @classmethod
    def register_provider(cls, provider: BaseDiscoveryProvider):
        """Registers a new pluggable discovery provider."""
        with cls._lock:
            cls._providers.append(provider)
            cls.invalidate_cache()

    @classmethod
    def _initialize_providers(cls):
        """Initializes default discovery providers if list is empty."""
        if not cls._providers:
            cls._providers = [RouteDiscoveryProvider()]

    @classmethod
    def discover_nodes(cls, force_refresh: bool=False) -> List[NavigationNode]:
        """
        Public Platform API — Discovers and returns all navigable Application Intelligence Nodes.
        Uses thread-safe in-memory caching.
        """
        with cls._lock:
            if cls._cached_nodes is not None and (not force_refresh):
                return cls._cached_nodes
            cls._initialize_providers()
            discovered_nodes: List[NavigationNode] = []
            node_map: Dict[str, NavigationNode] = {}
            for provider in cls._providers:
                try:
                    nodes = provider.discover()
                    for node in nodes:
                        discovered_nodes.append(node)
                        node_map[node.id] = node
                except Exception as e:
                    kiki_logger.error(f'[APPLICATION DISCOVERY] Provider error: {e}')
            cls._cached_nodes = discovered_nodes
            cls._cached_map = node_map
            kiki_logger.info(f'[APPLICATION DISCOVERY] Graph built successfully with {len(discovered_nodes)} nodes.')
            return cls._cached_nodes
        'Thread-safe cache invalidation API.'
        with cls._lock:
            cls._cached_nodes = None
            cls._cached_map = None
            kiki_logger.info('[APPLICATION DISCOVERY] Metadata cache invalidated.')

    @classmethod
    def get_node_by_id(cls, node_id: str) -> Optional[NavigationNode]:
        """Public Platform API — Retrieves a single node by ID."""
        nodes = cls.discover_nodes()
        if cls._cached_map and node_id in cls._cached_map:
            return cls._cached_map[node_id]
        for node in nodes:
            if node.id == node_id:
                return node
        return None

    @classmethod
    def find_capabilities(cls, capability_query: str) -> List[NavigationNode]:
        """Public Platform API — Searches nodes matching a specific capability."""
        query_clean = capability_query.strip().lower()
        nodes = cls.discover_nodes()
        return [node for node in nodes if any((query_clean in cap.lower() for cap in node.capabilities))]

    @classmethod
    def find_actions(cls, action_query: str) -> List[ActionDefinition]:
        """Public Platform API — Searches actions matching an action query."""
        query_clean = action_query.strip().lower()
        nodes = cls.discover_nodes()
        action_matches = []
        for node in nodes:
            for action in node.actions:
                if query_clean in action.name.lower() or query_clean in action.description.lower():
                    action_matches.append(action)
        return action_matches