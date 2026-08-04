from typing import Dict, Any, Optional
from .base import BaseSkill
from ..runtime.investigation_engine import InvestigationEngine


class InvestigationSkill(BaseSkill):
    name = "InvestigationSkill"
    description = "Executes schema matching, SQL query generation, and database read operations."

    def execute(
        self,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        engine = InvestigationEngine()
        result = engine.run_investigation(
            question=task_description,
            context=context_dict
        )
        return result.to_dict()
