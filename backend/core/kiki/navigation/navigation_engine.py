from typing import Dict, Any, Optional
from .application_discovery_service import ApplicationDiscoveryService
from .candidate_resolver import NavigationCandidateResolver
from .navigation_reasoner import NavigationReasoner
from .navigation_validator import NavigationValidator
from .response_builder import NavigationResponseBuilder
from ..utils.logger import kiki_logger


class NavigationEngine:
    """
    Orchestrator — Navigation Engine Platform Coordinator
    Coordinates the 5 decoupled Navigation & Application Intelligence components:
    1. ApplicationDiscoveryService
    2. NavigationCandidateResolver (Fast-Path < 1ms)
    3. NavigationReasoner (LLM Capability Reasoner)
    4. NavigationValidator (Security & Route Validation)
    5. NavigationResponseBuilder (Versioned Contract Payload)

    Guarantees Navigation NEVER enters InvestigationEngine or executes SQL queries.
    """

    @classmethod
    def navigate(
        cls,
        question: str,
        user_permissions: Optional[Dict[str, Any]] = None,
        reasoner: Optional[NavigationReasoner] = None
    ) -> Dict[str, Any]:
        kiki_logger.info(f"[NAVIGATION ENGINE] Resolving navigation request for query '{question}'")
        reasoner = reasoner or NavigationReasoner()


        # 1. Candidate Resolver: Fast-Path Exact Match (< 1ms execution, 0 LLM calls)
        is_exact, exact_node, candidates = NavigationCandidateResolver.resolve_candidates(
            question=question,
            user_permissions=user_permissions
        )

        if is_exact and exact_node:
            is_valid, _ = NavigationValidator.validate_node(exact_node, user_permissions)
            if is_valid:
                return NavigationResponseBuilder.build_single_response(
                    node=exact_node,
                    confidence=0.99,
                    question=question
                )

        # 2. Semantic Reasoner over Top Candidates
        intent_type, single_node, option_candidates = reasoner.reason_navigation(
            question=question,
            candidates=candidates
        )


        if intent_type == "NAVIGATION" and single_node:
            is_valid, _ = NavigationValidator.validate_node(single_node, user_permissions)
            if is_valid:
                return NavigationResponseBuilder.build_single_response(
                    node=single_node,
                    confidence=0.95,
                    question=question
                )

        if option_candidates:
            return NavigationResponseBuilder.build_options_response(
                candidates=option_candidates,
                confidence=0.65,
                query=question
            )

        return NavigationResponseBuilder.build_no_match_response(query=question)
