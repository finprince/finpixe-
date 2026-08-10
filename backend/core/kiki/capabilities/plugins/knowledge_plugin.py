"""
KIKI Knowledge Retrieval Capability Plugin — Phase 15 V3
==========================================================
Plugin capability for unstructured statutory knowledge and document search.
Interacts strictly through the KnowledgeProvider abstract interface and returns a standardized Evidence object.
"""
from typing import Dict, Any, List, Optional
from ..base import BaseCapability, CapabilityProbeResult
from ...rag.provider import KnowledgeProvider
from ...rag.vector_store import chroma_store
from ...rag.retriever import knowledge_retriever
from ...rag.citations import citation_builder
from ...evidence.model import Evidence, Citation
from ...providers import ProviderFactory
from ...config import kiki_settings
from ...logging import get_kiki_logger

logger = get_kiki_logger("knowledge_plugin")


class KnowledgeRetrievalCapability(BaseCapability):
    """Knowledge Retrieval Capability Plugin for KIKI AI Operating System."""

    name = "KnowledgeRetrievalCapability"
    description = "Searches unstructured statutory knowledge base, manuals, policies, SOPs, and user guides."
    priority = 90

    def __init__(self, provider: KnowledgeProvider = None):
        self.provider = provider or chroma_store

    def probe(self, rewritten_question: str, context: Any) -> CapabilityProbeResult:
        """
        Probes KnowledgeProvider fast vector similarity (< 5ms).
        Returns CapabilityProbeResult.
        """
        probe_data = self.provider.probe_vector(query_text=rewritten_question, top_k=3)
        max_sim = probe_data.get("max_similarity", 0.0)
        is_candidate = probe_data.get("is_candidate", False)
        top_doc = probe_data.get("top_document")

        logger.info(
            f"[KNOWLEDGE PROBE] Question: '{rewritten_question}' | "
            f"Candidate: {is_candidate} | Similarity: {max_sim:.4f} | Document: {top_doc}"
        )

        return CapabilityProbeResult(
            capability_name=self.name,
            is_match=is_candidate,
            confidence=max_sim,
            estimated_latency_ms=4.5,
            supported_operations=["semantic_vector_search", "document_family_retrieval"],
            availability=True,
            priority=self.priority,
            execution_params={
                "top_document": top_doc,
                "top_family": probe_data.get("top_family"),
                "max_similarity": max_sim
            }
        )

    def execute(
        self,
        rewritten_question: str,
        context: Any,
        probe_result: CapabilityProbeResult,
        tenant_id: str
    ) -> Evidence:
        """
        Executes Knowledge Retrieval, calls local Ollama synthesis, and returns Evidence object.
        """
        logger.info(f"[KNOWLEDGE EXECUTE] Processing: '{rewritten_question}' | Tenant: '{tenant_id}'")

        # 1. Retrieve evidence package from KnowledgeRetriever
        evidence_obj = knowledge_retriever.retrieve_evidence(
            query=rewritten_question,
            tenant_id=tenant_id,
            top_k=6,
            min_confidence=0.30
        )

        if not evidence_obj.payload.get("chunks"):
            # Fallback for general statutory questions with no matching custom upload chunks
            try:
                llm_provider = ProviderFactory.get_llm_provider()
                prompt = f"User Question: '{rewritten_question}'\nProvide a clear, accurate, enterprise statutory knowledge answer."
                reply_text = llm_provider.generate(
                    model=kiki_settings.REASONING_MODEL,
                    prompt=prompt,
                    temperature=0.1
                )
            except Exception as e:
                logger.warning(f"Knowledge fallback synthesis error: {str(e)}")
                reply_text = "Knowledge lookup completed. Please refer to statutory guidelines or internal documentation."

            evidence_obj.payload["synthesis_text"] = reply_text
            evidence_obj.summary = reply_text
            return evidence_obj

        # 2. Assemble context & prompt local Ollama reasoning model
        context_str = evidence_obj.payload["context_string"]
        system_prompt = (
            "You are KIKI 2027, an enterprise AI assistant. "
            "Answer the user's question completely using all relevant supplied evidence. "
            "Combine complementary information from multiple retrieved chunks. "
            "Preserve technical details, numbers, procedures, constraints, and relationships. "
            "Do not discard unique factual details merely to make the answer shorter. "
            "Do not invent information that is not supported by the evidence. "
            "If the supplied evidence is insufficient, explicitly state that."
        )

        prompt = (
            f"User Question: '{rewritten_question}'\n\n"
            f"Supplied Enterprise Knowledge Context:\n{context_str}\n\n"
            f"Provide a complete, accurate, grounded response using all supplied evidence above."
        )


        try:
            llm_provider = ProviderFactory.get_llm_provider()
            answer_text = llm_provider.generate(
                model=kiki_settings.REASONING_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
        except Exception as e:
            logger.warning(f"LLM synthesis error: {str(e)}")
            first_cite = evidence_obj.citations[0] if evidence_obj.citations else None
            doc_label = first_cite.document_name if first_cite else "Document"
            answer_text = f"Based on document '{doc_label}':\n{evidence_obj.payload['chunks'][0]['text']}"

        # 3. Build clean markdown citations
        formatted_citations = []
        for cite in evidence_obj.citations:
            formatted_citations.append({
                "document_name": cite.document_name,
                "page_number": cite.page_number,
                "section_heading": cite.section_heading
            })

        sources_markdown = citation_builder.format_citation_markdown(formatted_citations)
        full_reply = answer_text + sources_markdown

        evidence_obj.payload["synthesis_text"] = full_reply
        evidence_obj.summary = full_reply
        return evidence_obj
