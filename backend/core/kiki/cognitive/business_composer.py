import re
from typing import Dict, Any, List, Optional
from ..models.dto import (
    BusinessResponse,
    DeveloperDetails,
    RecommendationItem,
    QuickActionItem,
    CognitiveThinking,
    ExecutionPlan,
    ReflectionSummary,
    RetrievedKnowledgeItem
)
from .persona_manager import PersonaManager
from ..utils.logger import kiki_logger


class BusinessResponseComposer:
    """
    Component — Business Response Composer (Kiki 2.0)
    Formats cognitive intelligence output into structured ERP consultant responses:
    - Title
    - Result Metric
    - Summary
    - Insights
    - Recommendations & Quick Actions
    - Encapsulated DeveloperDetails (Planner, Vector Knowledge, Reflection Trace, SQL)
    """

    @classmethod
    def compose(
        cls,
        question: str,
        reasoning_output: Dict[str, Any],
        aggregated_evidence: Dict[str, Any],
        execution_plan: ExecutionPlan,
        reflection: ReflectionSummary,
        retrieved_knowledge: List[RetrievedKnowledgeItem],
        persona: str = "Accountant",
        confidence: str = "HIGH",
        recommendations: Optional[List[RecommendationItem]] = None
    ) -> BusinessResponse:

        clean_q = question.strip()
        lower_q = clean_q.lower()
        recs = recommendations or []

        # 1. Quick Actions
        quick_actions: List[QuickActionItem] = []
        for r in recs:
            if r.route:
                quick_actions.append(
                    QuickActionItem(
                        title=r.title,
                        action_type=r.action_type or "navigate",
                        route=r.route
                    )
                )

        # 2. Extract title & metric
        title = clean_q.title()
        if "sale" in lower_q:
            title = "Sales Report & Analysis"
        elif "purchase" in lower_q:
            title = "Purchase Voucher Summary"
        elif "gst" in lower_q:
            title = "GST Compliance & Tax Summary"

        result_val = reasoning_output.get("result_metric")
        summary = reasoning_output.get("summary") or f"Analysis completed for {title}."
        insights = reasoning_output.get("insights", [])

        # Apply Persona formatting
        summary = PersonaManager.format_summary_for_persona(persona, summary, result_val)

        # 3. Encapsulate Technical Details for Developer Mode
        dev_details = DeveloperDetails(
            sql_queries=aggregated_evidence.get("sql_queries", []),
            execution_steps=aggregated_evidence.get("execution_steps", []),
            evidences=aggregated_evidence.get("evidences", []),
            planner_output=execution_plan.to_dict(),
            retrieved_knowledge=[k.to_dict() for k in retrieved_knowledge],
            reflection_summary=reflection.to_dict(),
            confidence_score=1.0 if confidence == "HIGH" else (0.7 if confidence == "MEDIUM" else 0.4),
            selected_engine="KikiCognitiveOrchestrator",
            skills_executed=execution_plan.required_skills
        )

        formatted_reply = summary
        if result_val:
            formatted_reply = f"**{title}**: {result_val}\n\n{summary}"

        thinking = CognitiveThinking(
            user_objective=execution_plan.business_objective,
            business_task=execution_plan.goal,
            needs_data=True,
            reasoning_summary=reasoning_output.get("reasoning_notes", "")
        )

        return BusinessResponse(
            title=title,
            result=result_val,
            summary=summary,
            reply=formatted_reply,
            insights=insights,
            recommendations=recs,
            quick_actions=quick_actions,
            persona=persona,
            confidence=confidence,
            thinking=thinking,
            execution_plan=execution_plan,
            reflection=reflection,
            developer_details=dev_details
        )
