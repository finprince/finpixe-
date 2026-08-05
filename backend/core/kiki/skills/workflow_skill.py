from typing import Dict, Any, Optional
from .base import BaseSkill
from ..engines.workflow_engine import WorkflowEngine


class WorkflowSkill(BaseSkill):
    name = "WorkflowSkill"
    description = "Executes ERP workflow automation steps."

    def execute(
        self,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return WorkflowEngine.execute(task_description)
