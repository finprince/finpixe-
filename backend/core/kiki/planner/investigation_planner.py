from typing import Dict, Any, List
from ..models.dto import QuestionUnderstanding, InvestigationPlan, InvestigationStep
from ..utils.logger import kiki_logger


class InvestigationPlanner:
    """
    Component 2 — Investigation Planner
    Converts question understanding into a structured step-by-step reasoning plan.
    Strictly performs planning only. NO SQL generation, NO schema search, NO database access.
    """

    @classmethod
    def build_plan_from_llm_response(
        cls,
        question: str,
        understanding: QuestionUnderstanding,
        raw_plan_dict: Dict[str, Any]
    ) -> InvestigationPlan:
        """
        Parses LLM prompt response dictionary into an InvestigationPlan DTO.
        """
        goal = raw_plan_dict.get("goal") or f"Investigate cause of question: {question}"
        raw_steps = raw_plan_dict.get("steps", [])

        steps: List[InvestigationStep] = []
        if isinstance(raw_steps, list):
            for idx, s in enumerate(raw_steps, start=1):
                if isinstance(s, dict):
                    steps.append(InvestigationStep(
                        step_number=s.get("step_number", idx),
                        description=s.get("description", f"Investigation step {idx}"),
                        objective=s.get("objective", "")
                    ))
                elif isinstance(s, str):
                    steps.append(InvestigationStep(
                        step_number=idx,
                        description=s,
                        objective=""
                    ))

        if not steps:
            steps = cls._generate_default_steps(understanding)

        kiki_logger.info(f"InvestigationPlanner created plan with {len(steps)} steps.")
        return InvestigationPlan(goal=goal, steps=steps)

    @classmethod
    def _generate_default_steps(cls, understanding: QuestionUnderstanding) -> List[InvestigationStep]:
        """Fallback step generator for entity-based and metric investigations."""
        if understanding.entities:
            entity_str = ", ".join(understanding.entities)
            return [
                InvestigationStep(
                    step_number=1,
                    description=f"Resolve entity master details for {entity_str}",
                    objective="Locate party or vendor ID"
                ),
                InvestigationStep(
                    step_number=2,
                    description="Locate matching transaction records and invoices",
                    objective="Filter vouchers by party"
                ),
                InvestigationStep(
                    step_number=3,
                    description="Retrieve latest transaction sorted by valid date column",
                    objective="Extract newest transaction details"
                ),
                InvestigationStep(
                    step_number=4,
                    description="Synthesize evidence and form business explanation",
                    objective="Produce evidence-backed answer"
                )
            ]

        return [
            InvestigationStep(
                step_number=1,
                description="Locate metric records and basic details",
                objective="Retrieve transaction totals"
            ),
            InvestigationStep(
                step_number=2,
                description="Compare transaction totals across active periods",
                objective="Determine volume and revenue variance"
            ),
            InvestigationStep(
                step_number=3,
                description="Synthesize evidence and form business conclusion",
                objective="Produce evidence-backed answer"
            )
        ]

