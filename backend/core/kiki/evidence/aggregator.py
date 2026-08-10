"""
KIKI Evidence Aggregator — Phase 16.1 Pure Presentation Engine
===============================================================
Receives ExecutionPolicy and List[Evidence].
Performs strictly presentation responsibilities: ranking evidence by confidence,
deduplicating citations, formatting text, and preserving source provenance.
Contains ZERO business override rules.
"""
from typing import Dict, Any, List
from .model import Evidence, Citation
from ..capabilities.base import ExecutionPolicy
from ..logging import get_kiki_logger

logger = get_kiki_logger("evidence_aggregator")


class EvidenceAggregator:
    """Enterprise Evidence Presentation Engine for Single & Multi-Capability Plans."""

    def aggregate(self, execution_policy: ExecutionPolicy, evidence_list: List[Evidence]) -> Dict[str, Any]:
        """
        Ranks, deduplicates, formats, and aggregates Evidence objects based on ExecutionPolicy.
        Contains ZERO business decision or override logic.
        """
        if not evidence_list:
            return {
                "reply": "No evidence was returned for the query.",
                "evidence_package": {"summary": "No data retrieved.", "citations": [], "provenance": []},
                "citations": [],
                "action_cards": []
            }

        # Rank evidence strictly by evidence confidence score descending
        ranked_evidence = sorted(evidence_list, key=lambda e: e.confidence, reverse=True)

        primary_ev = ranked_evidence[0]
        full_reply = primary_ev.payload.get("synthesis_text") or primary_ev.summary

        # Format secondary evidence text ONLY for HYBRID execution policy
        if execution_policy == ExecutionPolicy.HYBRID and len(ranked_evidence) > 1:
            reply_parts = [full_reply]
            for sec_ev in ranked_evidence[1:]:
                sec_text = sec_ev.payload.get("synthesis_text") or sec_ev.summary
                if sec_text and sec_text not in reply_parts:
                    reply_parts.append(sec_text)
            full_reply = "\n\n".join(reply_parts)

        # Merge citations & preserve provenance
        merged_citations: List[Dict[str, Any]] = []
        seen_citations = set()
        merged_action_cards: List[Dict[str, Any]] = []
        provenance: List[str] = []

        for ev in ranked_evidence:
            provenance.append(ev.source)
            for cite in ev.citations:
                key = f"{cite.document_name}|{cite.section_heading}"
                if key not in seen_citations:
                    seen_citations.add(key)
                    merged_citations.append({
                        "document_name": cite.document_name,
                        "page_number": cite.page_number,
                        "section_heading": cite.section_heading,
                        "document_family": cite.document_family
                    })
            if "action_cards" in ev.payload:
                merged_action_cards.extend(ev.payload["action_cards"])

        composite_summary = " | ".join([f"[{ev.type} from {ev.source}]: {ev.summary}" for ev in ranked_evidence])

        logger.info(
            f"[AGGREGATOR 16.1] Policy: {execution_policy.value} | "
            f"Evidence Count: {len(ranked_evidence)} | Citations: {len(merged_citations)}"
        )

        return {
            "reply": full_reply,
            "evidence_package": {
                "summary": composite_summary,
                "citations": merged_citations,
                "provenance": provenance,
                "raw_evidence_count": len(ranked_evidence)
            },
            "citations": merged_citations,
            "action_cards": merged_action_cards
        }


evidence_aggregator = EvidenceAggregator()
