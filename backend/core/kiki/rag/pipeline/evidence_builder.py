"""
KIKI Evidence & Grounded Prompt Builder — Phase 17
==================================================
Concrete implementation of BaseEvidenceBuilder. Converts candidate chunks into standardized Evidence DTOs
and builds strict grounded LLM reasoning prompts.
"""
from typing import Dict, Any, List, Optional
from ..interfaces.evidence import BaseEvidenceBuilder
from core.kiki.evidence.model import Evidence, Citation
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("evidence_builder")


class EvidenceBuilder(BaseEvidenceBuilder):
    """Structured Evidence Package and Grounded Prompt Builder."""

    def build_evidence(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        trace_data: Optional[Dict[str, Any]] = None
    ) -> Evidence:
        """Converts retrieved candidate chunks into standardized Evidence DTO."""
        if not chunks:
            return Evidence(
                type="KNOWLEDGE",
                source="finpixe_global_knowledge",
                payload={"chunks": [], "context_string": ""},
                summary="No relevant knowledge documents found above confidence threshold.",
                confidence=0.0,
                citations=[]
            )

        citations: List[Citation] = []
        seen = set()

        for c in chunks:
            meta = c.get("metadata", {})
            doc_name = meta.get("filename") or meta.get("document_name") or "Internal Document"
            family = meta.get("document_family", doc_name.rsplit(".", 1)[0].split("_")[0])
            page = int(meta.get("page_number") or meta.get("page", 1))
            section = meta.get("section_heading") or meta.get("section", "General")
            key = f"{doc_name}|{section}"

            if key not in seen:
                seen.add(key)
                citations.append(Citation(
                    document_name=doc_name,
                    page_number=page,
                    section_heading=section,
                    document_family=family,
                    confidence=c.get("confidence", 0.90)
                ))

        context_parts = []
        for idx, c in enumerate(chunks):
            meta = c.get("metadata", {})
            doc_name = (meta.get("filename") or meta.get("document_name") or "Doc").replace(".md", "").replace("_", " ")
            page = meta.get("page_number") or meta.get("page", 1)
            section = meta.get("section_heading") or meta.get("section", "General")
            context_parts.append(f"[Source {idx+1}: {doc_name} (Page {page}, Section: {section})]\n{c['text']}")

        context_string = "\n\n".join(context_parts)
        top_meta = chunks[0].get("metadata", {})
        top_doc = top_meta.get("filename") or top_meta.get("document_name") or "Document"
        top_family = top_meta.get("document_family", "General")

        payload = {
            "chunks": chunks,
            "context_string": context_string,
            "top_document": top_doc,
            "top_family": top_family
        }
        if trace_data:
            payload["trace"] = trace_data

        top_confidence = chunks[0].get("confidence", 0.90)

        return Evidence(
            type="KNOWLEDGE",
            source="finpixe_global_knowledge",
            payload=payload,
            summary=f"Retrieved {len(chunks)} relevant document chunks from Document Family '{top_family}'.",
            confidence=top_confidence,
            citations=citations,
            metadata={"top_document": top_doc, "top_family": top_family}
        )

    def build_grounded_prompt(self, query: str, context_string: str) -> str:
        """Builds strict grounded LLM reasoning prompt."""
        return (
            f"User Question: '{query}'\n\n"
            f"Retrieved Knowledge Context:\n{context_string}\n\n"
            f"Provide a clear, precise, professional answer based strictly on the context above."
        )


evidence_builder = EvidenceBuilder()
