from typing import List, Dict, Any, Optional, Tuple
from .providers.base_provider import NavigationNode
from .application_discovery_service import ApplicationDiscoveryService
from ..utils.logger import kiki_logger

class NavigationCandidateResolver:
    """
    Component 2 — Navigation Candidate Resolver
    Performs deterministic fast-path exact match lookup (< 1ms execution, 0 LLM calls)
    and retrieves top 3-5 capability-scored candidate nodes for semantic LLM reasoning.
    """
    EXACT_VERBS = ['go to', 'open', 'navigate', 'take me to', 'show page', 'show', 'launch', 'switch to', 'move to', 'view page', 'view', 'create']

    @classmethod
    def resolve_candidates(cls, question: str, user_permissions: Optional[Dict[str, Any]]=None) -> Tuple[bool, Optional[NavigationNode], List[NavigationNode]]:
        """
        Resolves query to either:
        - (True, exact_node, []) -> Fast-Path Exact Match (< 1ms, 0 LLM calls)
        - (False, None, [top_candidates]) -> Candidate list for semantic LLM reasoning
        """
        if not question or not isinstance(question, str):
            return (False, None, [])
        clean_q = question.strip().lower()
        all_nodes = ApplicationDiscoveryService.discover_nodes()
        accessible_nodes = cls._filter_by_permissions(all_nodes, user_permissions)
        for node in accessible_nodes:
            node_title = node.title.lower()
            node_id = node.id.lower()
            if clean_q == node_title or clean_q == f'open {node_title}' or clean_q == f'go to {node_title}' or (clean_q == f'go to the {node_title}'):
                kiki_logger.info(f"[CANDIDATE RESOLVER] Fast-Path exact match: '{question}' -> Node '{node.title}' ({node.route})")
                return (True, node, [])
            for term in node.search_terms:
                term_clean = term.lower()
                for verb in cls.EXACT_VERBS:
                    if clean_q == f'{verb} {term_clean}' or clean_q == f'{verb} the {term_clean}':
                        kiki_logger.info(f"[CANDIDATE RESOLVER] Fast-Path alias match: '{question}' -> Node '{node.title}' ({node.route})")
                        return (True, node, [])
        scored_candidates: List[Tuple[float, NavigationNode]] = []
        tokens = [t for t in clean_q.split() if len(t) > 2]
        for node in accessible_nodes:
            score = 0.0
            node_title = node.title.lower()
            node_desc = node.description.lower()
            for token in tokens:
                if token in node_title:
                    score += 10.0
                if token in node_desc:
                    score += 3.0
                for cap in node.capabilities:
                    if token in cap.lower():
                        score += 5.0
                for st in node.search_terms:
                    if token in st.lower():
                        score += 4.0
                for act in node.actions:
                    if token in act.name.lower() or token in act.description.lower():
                        score += 4.0
            if score > 0.0:
                scored_candidates.append((score, node))
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c[1] for c in scored_candidates[:4]]
        if not top_candidates:
            top_candidates = accessible_nodes[:4]
        kiki_logger.info(f"[CANDIDATE RESOLVER] Retrieved {len(top_candidates)} candidate nodes for query '{question}'")
        return (False, None, top_candidates)

    @classmethod
    def _filter_by_permissions(cls, nodes: List[NavigationNode], user_permissions: Optional[Dict[str, Any]]) -> List[NavigationNode]:
        if not user_permissions:
            return nodes
        if user_permissions.get('is_superuser') or user_permissions.get('is_master'):
            return nodes
        filtered = []
        for node in nodes:
            if node.visibility == 'public' or not node.permissions:
                filtered.append(node)
                continue
            perms_dict = user_permissions.get('permissions', {})
            has_access = any((perms_dict.get(p, {}).get('view') is True for p in node.permissions))
            if has_access or node.title in {'Dashboard', 'Settings'}:
                filtered.append(node)
        return filtered if filtered else nodes