from typing import Dict, Any, Optional
from .base import BaseSkill
from ..engines.kpi_engine import KPIEngine


class KPISkill(BaseSkill):
    name = "KPISkill"
    description = "Calculates instant fast-path business metrics (Sales, Purchases, Receivables, Payables)."

    def execute(
        self,
        task_description: str,
        context_dict: Optional[Dict[str, Any]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return KPIEngine.execute(task_description)
