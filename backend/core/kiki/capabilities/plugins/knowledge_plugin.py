"""
KIKI Knowledge Retrieval Capability Plugin — Phase 18.5 Hardened
===================================================================
Plugin capability for unstructured statutory knowledge and document search.
Interacts strictly through the KnowledgeProvider abstract interface and returns a standardized Evidence object.

Phase 18.5 UX Corrections:
- Synthesis prompt enforces direct conversational response without "Source 1:" or "Based on sources" leakage.
- Returns clean synthesis_text without appending raw inline sources markdown.
- Structured citations array is passed as clean metadata for collapsed UI rendering.
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
                prompt = f"User Question: '{rewritten_question}'\nProvide a clear, direct, conversational AI assistant response."
                reply_text = llm_provider.generate(
                    model=kiki_settings.REASONING_MODEL,
                    prompt=prompt,
                    temperature=0.1
                )
            except Exception as e:
                logger.warning(f"Knowledge fallback synthesis error: {str(e)}")
                reply_text = "I don't have enough information in the available knowledge to answer that reliably."

            evidence_obj.payload["synthesis_text"] = reply_text
            evidence_obj.summary = reply_text
            return evidence_obj

        # 2. Assemble context & prompt local Ollama reasoning model
        context_str = evidence_obj.payload["context_string"]
        system_prompt = (
            "You are KIKI 2027, a helpful conversational AI assistant.\n"
            "Answer the user's question directly, clearly, and naturally.\n"
            "Use all relevant supplied context internally to form your answer.\n"
            "DO NOT say 'Based on the supplied sources', 'According to Source 1', or 'Source 1:'.\n"
            "DO NOT insert source lists, chunk IDs, vector scores, or RAG metadata into your response text.\n"
            "Combine complementary facts smoothly into a natural conversational response.\n"
            "If the supplied context does not contain enough information to answer the question, state:\n"
            "\"I don't have enough information in the available knowledge to answer that reliably.\""
        )

        prompt = (
            f"User Question: '{rewritten_question}'\n\n"
            f"Context:\n{context_str}\n\n"
            f"Provide a clean, direct, conversational response answering the user's question."
        )

        try:
            llm_provider = ProviderFactory.get_llm_provider()
            raw_answer = llm_provider.generate(
                model=kiki_settings.REASONING_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
        except Exception as e:
            logger.warning(f"LLM synthesis error: {str(e)}")
            raw_answer = "I don't have enough information in the available knowledge to answer that reliably."

        # Post-process answer text to strip any residual "Source 1:" or "Based on the provided sources" prefixes
        clean_answer = raw_answer.strip()
        lines = clean_answer.split('\n')
        filtered_lines = []
        for line in lines:
            lower_l = line.lower().strip()
            if lower_l.startswith(("source 1:", "source 2:", "source 3:", "source 4:", "source 5:")):
                continue
            if lower_l.startswith("based on the supplied sources") or lower_l.startswith("based on the provided sources"):
                line = line.split(":", 1)[-1].strip() if ":" in line else line
            filtered_lines.append(line)
        clean_answer = "\n".join(filtered_lines).strip()

        # 3. Store clean synthesis text without inline sources markdown
        evidence_obj.payload["synthesis_text"] = clean_answer
        evidence_obj.summary = clean_answer

        return evidence_obj
