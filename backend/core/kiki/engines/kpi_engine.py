from typing import Dict, Any, Optional
from ..query.kpi_resolver import KPIResolver
from ..runtime.investigation_engine import InvestigationEngine
from ..utils.logger import kiki_logger


class KPIEngine:
    """
    Specialized Engine — KPI Engine
    Calculates instant dashboard analytics, metrics, aggregations, and trend figures.
    Guarantees an informational answer is returned FIRST, with optional navigation recommendations.
    """

    @classmethod
    def execute(cls, question: str, context_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        kiki_logger.info(f"[KPI ENGINE] Executing KPI calculation for question '{question}'")

        # 1. Try Fast-Path KPI Resolver
        kpi_res = KPIResolver.resolve(question)
        if kpi_res is not None:
            res_dict = kpi_res.to_dict()
            res_dict["reply"] = kpi_res.final_response
            res_dict["intent"] = "KPI_QUERY"
            
            # Optional contextual navigation suggestions (Answer first, navigation secondary)
            suggestions = [
                {"title": "Open Dashboard", "route": "/dashboard", "description": "View live interactive dashboard metrics"},
                {"title": "View Reports", "route": "/dashboard?page=reports", "description": "Open financial analytics & reports"}
            ]
            res_dict["navigation_suggestions"] = suggestions
            return res_dict

        # 2. Fallback to InvestigationEngine for complex multi-metric KPI questions
        engine = InvestigationEngine()
        result = engine.run_investigation(question, context=context_dict)
        response_payload = result.to_dict()
        response_payload["reply"] = result.final_response
        response_payload["intent"] = "KPI_QUERY"
        response_payload["navigation_suggestions"] = [
            {"title": "Open Dashboard", "route": "/dashboard", "description": "View live workspace metrics"}
        ]
        return response_payload
