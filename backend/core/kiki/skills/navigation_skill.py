from typing import Dict, Any, Optional
from .base import BaseSkill
from ..navigation.navigation_engine import NavigationEngine


class NavigationSkill(BaseSkill):
    name = "NavigationSkill"
    description = "Navigates to specified ERP pages and workspaces."

    def execute(
        self,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        res = NavigationEngine.navigate(task_description, user_permissions=user_permissions)
        return res
