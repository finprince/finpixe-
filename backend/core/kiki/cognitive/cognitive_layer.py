from typing import Dict, Any, Optional, List
from ..models.dto import BusinessResponse
from ..skills.registry import SkillRegistry

# Cognitive Layer Components
from .context_manager import ContextManager
from .conversation_memory import ConversationMemory
from .planner import CognitivePlanner
from .knowledge_retrieval import KnowledgeRetrievalService
from .evidence_aggregator import EvidenceAggregator
from .business_reasoning import BusinessReasoningEngine
from .reflection_engine import ReflectionEngine
from .confidence_evaluator import ConfidenceEvaluator
from .persona_manager import PersonaManager
from .recommendation_engine import RecommendationEngine
from .business_composer import BusinessResponseComposer
from ..utils.logger import kiki_logger


class KikiCognitiveLayer:
    """
    Component — FINPIXE Kiki 2.0 Cognitive Intelligence Platform (AI Brain)

    Full End-to-End Pipeline:
    Context Manager -> Conversation Memory -> Cognitive Planner -> Knowledge Retrieval Layer ->
    Skill Registry (Worker Execution) -> Evidence Aggregator -> Business Reasoning Engine ->
    Reflection Engine -> Confidence Evaluator -> Persona Manager -> Business Response Composer ->
    Recommendation Engine -> Final Consultant Response
    """

    @classmethod
    def process_request(
        cls,
        question: str,
        context_dict: Optional[Dict[str, Any]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        user_permissions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        clean_q = question.strip()
        kiki_logger.info(f"[KIKI 2.0 COGNITIVE BRAIN] Processing query: '{clean_q}'")

        # 1. Context Manager
        context_state = ContextManager.build_context(
            question=clean_q,
            context_dict=context_dict,
            user_permissions=user_permissions
        )

        # 2. Conversation Memory (Multi-turn Constraint Accumulation)
        cumulative_constraints = ConversationMemory.resolve_conversation(
            current_question=clean_q,
            history=history,
            existing_constraints=context_state.cumulative_constraints
        )
        context_state.cumulative_constraints = cumulative_constraints

        # 3. Cognitive Planner
        execution_plan = CognitivePlanner.plan(
            question=clean_q,
            context_state=context_state,
            cumulative_constraints=cumulative_constraints
        )

        # Handle explicit clarification requirement upfront
        if execution_plan.needs_clarification:
            kiki_logger.info(f"[KIKI 2.0] Question requires clarification: '{clean_q}'")
            return {
                "title": "Clarification Required",
                "summary": execution_plan.clarification_prompt or "Could you please specify which metric or report you'd like to view?",
                "reply": execution_plan.clarification_prompt or "Could you please specify which metric or report you'd like to view?",
                "confidence": "LOW",
                "persona": context_state.persona,
                "recommendations": [
                    {"title": "View Executive Dashboard", "route": "/dashboard"},
                    {"title": "Export Accounting Summary", "route": "/reports"}
                ],
                "developer_details": {"planner_output": execution_plan.to_dict(), "confidence_score": 0.3}
            }

        # 4. Knowledge Retrieval Layer (Semantic Vector Search)
        retrieved_knowledge = KnowledgeRetrievalService.retrieve_knowledge(
            query=clean_q,
            top_k=3
        )

        # 5. Skill Registry Execution (Worker Engine Tools)
        skill_outputs: List[Dict[str, Any]] = []
        for skill_name in execution_plan.required_skills:
            evidence = SkillRegistry.execute_skill(
                skill_name=skill_name,
                task_description=clean_q,
                context_dict=context_dict,
                user_permissions=user_permissions
            )
            skill_outputs.append(evidence)

        # 6. Evidence Aggregator
        aggregated_evidence = EvidenceAggregator.aggregate_evidence(skill_outputs)

        # 7. Business Reasoning Engine
        reasoning_output = BusinessReasoningEngine.reason(
            question=clean_q,
            aggregated_evidence=aggregated_evidence,
            retrieved_knowledge=retrieved_knowledge,
            context_state=context_state
        )

        # 8. Reflection Engine
        reflection_summary = ReflectionEngine.reflect(
            question=clean_q,
            reasoning_output=reasoning_output,
            aggregated_evidence=aggregated_evidence,
            context_state=context_state
        )

        # 9. Confidence Evaluator
        confidence = ConfidenceEvaluator.evaluate(
            intent="BUSINESS_INVESTIGATION",
            question=clean_q,
            engine_output=reasoning_output,
            evidences=aggregated_evidence.get("evidences")
        )
        if not reflection_summary.confidence_justified:
            confidence = "MEDIUM"

        # 10. Persona Manager
        persona = PersonaManager.resolve_persona(user_permissions, context_dict)

        # 11. Recommendation Engine
        recommendations = RecommendationEngine.generate_recommendations(
            question=clean_q,
            intent="BUSINESS_INVESTIGATION",
            engine_output=reasoning_output,
            context_dict=context_dict
        )

        # 12. Business Response Composer
        business_response = BusinessResponseComposer.compose(
            question=clean_q,
            reasoning_output=reasoning_output,
            aggregated_evidence=aggregated_evidence,
            execution_plan=execution_plan,
            reflection=reflection_summary,
            retrieved_knowledge=retrieved_knowledge,
            persona=persona,
            confidence=confidence,
            recommendations=recommendations
        )

        kiki_logger.info(
            f"[KIKI 2.0 COGNITIVE BRAIN SUCCESS]\n"
            f"Query: '{clean_q}'\n"
            f"Title: '{business_response.title}'\n"
            f"Result: '{business_response.result}'\n"
            f"Skills Executed: {execution_plan.required_skills}\n"
            f"Knowledge Items Retrieved: {len(retrieved_knowledge)}\n"
            f"Confidence: {confidence}\n"
        )

        final_payload = business_response.to_dict()
        final_payload["intent"] = "BUSINESS_INVESTIGATION"
        return final_payload
