from typing import Dict, Any, List, Optional
from .providers.base_provider import NavigationNode
from ..utils.logger import kiki_logger


class NavigationResponseBuilder:
    """
    Component 5 — Versioned Navigation Payload Contract Builder
    Generates versioned, confidence-scored JSON payloads for frontend execution.
    Guarantees schema versioning ("1.0") and confidence metrics.
    Navigation NEVER enters InvestigationEngine or executes SQL.
    """

    SCHEMA_VERSION = "1.0"

    @classmethod
    def build_single_response(
        cls,
        node: NavigationNode,
        confidence: float = 0.99,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Builds single target navigation response payload."""
        msg = f"Navigating to {node.title} ({node.route})."
        kiki_logger.info(f"[RESPONSE BUILDER] Single navigation payload for '{node.title}' (confidence={confidence})")
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "intent": "NAVIGATION",
            "module": node.title,
            "route": node.route,
            "action": "open",
            "confidence": confidence,
            "final_response": msg,
            "reply": msg,
            "investigation_steps": [],
            "evidences": []
        }

    @classmethod
    def build_options_response(
        cls,
        candidates: List[NavigationNode],
        confidence: float = 0.65,
        query: str = ""
    ) -> Dict[str, Any]:
        """Builds multi-option navigation response payload for ambiguous queries."""
        options = []
        for c in candidates:
            options.append({
                "id": c.id,
                "title": c.title,
                "route": c.route,
                "description": c.description,
                "category": c.category
            })

        msg = f"Found {len(options)} possible matching destinations for '{query}'."
        kiki_logger.info(f"[RESPONSE BUILDER] Options payload with {len(options)} candidates for query '{query}'")
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "intent": "NAVIGATION_OPTIONS",
            "query": query,
            "confidence": confidence,
            "options": options,
            "final_response": msg,
            "reply": msg,
            "investigation_steps": [],
            "evidences": []
        }

    @classmethod
    def build_no_match_response(cls, query: str = "") -> Dict[str, Any]:
        """Builds no match fallback payload."""
        msg = f"I could not find a matching ERP page for '{query}'."
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "intent": "NAVIGATION_NO_MATCH",
            "query": query,
            "confidence": 0.0,
            "final_response": msg,
            "reply": msg,
            "investigation_steps": [],
            "evidences": []
        }
