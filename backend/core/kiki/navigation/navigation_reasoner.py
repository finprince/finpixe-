import json
from typing import List, Dict, Any, Optional, Tuple
from .providers.base_provider import NavigationNode
from ..runtime.ollama_runtime import OllamaRuntime
from ..utils.logger import kiki_logger


class NavigationReasoner:
    """
    Component 3 — Semantic Navigation Reasoner
    Performs LLM capability-based semantic reasoning over top 3-5 candidate nodes.
    Invoked ONLY when fast-path exact resolution cannot match deterministically.
    Presents options (NAVIGATION_OPTIONS) when queries are ambiguous.
    """

    def __init__(self, ollama_runtime: Optional[OllamaRuntime] = None):
        self.ollama = ollama_runtime or OllamaRuntime()

    def reason_navigation(
        self,
        question: str,
        candidates: List[NavigationNode]
    ) -> Tuple[str, Optional[NavigationNode], List[NavigationNode]]:
        """
        Reasons over candidate nodes for the question.
        Returns tuple: (intent_type, single_match_node_or_none, candidate_options_list)
        intent_type: "NAVIGATION" or "NAVIGATION_OPTIONS"
        """
        if not candidates:
            return "NAVIGATION_OPTIONS", None, []

        if len(candidates) == 1:
            return "NAVIGATION", candidates[0], []

        # Build compact candidate representation for Ollama (prompt size optimization)
        candidate_payloads = []
        for c in candidates:
            candidate_payloads.append({
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "capabilities": c.capabilities[:4],
                "business_domain": c.business_domain,
                "actions": [a.name for a in c.actions[:3]]
            })

        system_prompt = (
            "You are Kiki's AI Application Intelligence Navigation Reasoner.\n"
            "Analyze the user query and select the single best matching node ID from the provided candidates.\n"
            "If the query is ambiguous and could match multiple candidates, return 'AMBIGUOUS'.\n"
            "Respond ONLY with a valid JSON object matching this structure:\n"
            "{\"selected_id\": \"node_id_or_AMBIGUOUS\", \"confidence\": 0.95, \"reasoning\": \"explanation\"}"
        )

        user_prompt = (
            f"User Question: \"{question}\"\n\n"
            f"Candidate Application Nodes:\n{json.dumps(candidate_payloads, indent=2)}\n\n"
            "Which single node ID best fulfills this business capability request?"
        )

        try:
            llm_resp = self.ollama._call_ollama(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0
            )

            parsed = self.ollama._parse_json_response(llm_resp)
            selected_id = parsed.get("selected_id", "").strip()

            if selected_id and selected_id != "AMBIGUOUS":
                for c in candidates:
                    if c.id == selected_id:
                        kiki_logger.info(f"[NAVIGATION REASONER] LLM selected node '{c.title}' ({c.id}) for query '{question}'")
                        return "NAVIGATION", c, []

        except Exception as e:
            kiki_logger.warning(f"[NAVIGATION REASONER] LLM reasoning warning: {e}. Falling back to option list.")

        # If ambiguous or LLM parsing failed, return options list
        kiki_logger.info(f"[NAVIGATION REASONER] Query '{question}' returned multiple options ({len(candidates)} candidates)")
        return "NAVIGATION_OPTIONS", None, candidates
