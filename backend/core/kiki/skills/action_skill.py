from typing import Dict, Any, Optional
from .base import BaseSkill
from ..engines.action_engine import ActionEngine


class ActionSkill(BaseSkill):
    name = "ActionSkill"
    description = "Executes transactional write actions (create, approve, delete)."

    def execute(
        self,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return ActionEngine.execute(task_description, context=context_dict)
