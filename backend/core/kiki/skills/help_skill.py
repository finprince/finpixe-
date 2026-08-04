from typing import Dict, Any, Optional
from .base import BaseSkill
from ..help.help_handler import HelpHandler


class HelpSkill(BaseSkill):
    name = "HelpSkill"
    description = "Provides ERP documentation and operational workflow guides."

    def execute(
        self,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return HelpHandler.handle_help(task_description)
