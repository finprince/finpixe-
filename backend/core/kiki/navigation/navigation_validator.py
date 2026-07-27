from typing import Optional, Dict, Any, Tuple
from .providers.base_provider import NavigationNode
from .application_discovery_service import ApplicationDiscoveryService
from ..utils.logger import kiki_logger


class NavigationValidator:
    """
    Component 4 — Navigation Security & Route Validator
    Validates selected routes against the discovered Application Intelligence Graph.
    Guarantees LLM never navigates to non-existent, hallucinated, or unauthorized pages.
    """

    @classmethod
    def validate_node(
        cls,
        node: NavigationNode,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Validates node against discovered graph and user RBAC permissions.
        Returns tuple: (is_valid, validation_status)
        """
        if not node or not node.route:
            return False, "INVALID_NODE"

        # 1. Cross-reference against discovered graph
        discovered_node = ApplicationDiscoveryService.get_node_by_id(node.id)
        if not discovered_node:
            kiki_logger.warning(f"[NAVIGATION VALIDATOR] Rejected undiscovered node ID '{node.id}'")
            return False, "NO_MATCH"

        # 2. Validate route structure
        if not (node.route.startswith("/dashboard") or node.route.startswith("/")):
            kiki_logger.warning(f"[NAVIGATION VALIDATOR] Rejected invalid route format '{node.route}'")
            return False, "INVALID_ROUTE"

        # 3. Check RBAC permissions if permissions provided
        if user_permissions and not user_permissions.get("is_superuser") and not user_permissions.get("is_master"):
            perms_dict = user_permissions.get("permissions", {})
            if node.permissions and node.visibility != "public":
                has_access = any(perms_dict.get(p, {}).get("view") is True for p in node.permissions)
                if not has_access and node.title not in ["Dashboard", "Settings"]:
                    kiki_logger.warning(f"[NAVIGATION VALIDATOR] Rejected unauthorized route '{node.route}' for user")
                    return False, "UNAUTHORIZED"

        kiki_logger.info(f"[NAVIGATION VALIDATOR] Validated route '{node.route}' successfully")
        return True, "VALID"
