"""
KIKI Enterprise Local RAG Engine
=================================
Orchestrates unstructured document ingestion, semantic chunking, vector indexing,
retrieval, relevance filtering, ranked context assembly, LLM synthesis, and clean user citations.
"""
import uuid
from typing import Dict, Any, List, Optional
from .loader import document_loader
from .chunker import semantic_chunker
from .vector_store import chroma_store
from .retriever import knowledge_retriever
from .citations import citation_builder
from ..providers import ProviderFactory
from ..config import kiki_settings
from ..logging import get_kiki_logger

logger = get_kiki_logger("local_rag_engine")

class LocalRAGEngine:
    """Central Local RAG Engine for unstructured knowledge base."""

    def ingest_document(
        self,
        file_path: str,
        filename: str,
        tenant_id: str,
        department: str = "General",
        security_level: str = "Internal"
    ) -> Dict[str, Any]:
        """
        Executes complete ingestion pipeline: Parse -> Normalize -> Chunk -> Embed -> Store.
        """
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        logger.info(f"Starting ingestion pipeline for document '{filename}' (ID: {doc_id})")

        doc_data = document_loader.load_document(file_path, filename=filename)

        chunks = semantic_chunker.chunk_document(
            doc_data=doc_data,
            doc_id=doc_id,
            tenant_id=tenant_id,
            department=department,
            security_level=security_level
        )

        indexed_count = chroma_store.add_chunks(chunks)

        return {
            "document_id": doc_id,
            "filename": filename,
            "total_pages": doc_data["total_pages"],
            "total_chunks": indexed_count,
            "status": "READY",
            "tenant_id": tenant_id
        }

    def answer_question(
        self,
        question: str,
        tenant_id: str,
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes knowledge question answering pipeline:
        Retrieve -> Relevance Filter -> Rank -> Deduplicate -> Assemble Context -> LLM Synthesis -> Clean Citations.
        """
        logger.info(f"[RAG ENGINE] Processing: '{question}' | Tenant: '{tenant_id}'")

        # 1. Top-K Retrieval with Relevance Filtering & Ranking
        chunks = knowledge_retriever.retrieve(
            query=question,
            tenant_id=tenant_id,
            top_k=5,
            department=department,
            min_confidence=0.38
        )

        # 2. No relevant chunks found — fallback to LLM general knowledge
        if not chunks:
            logger.warning(f"[RAG ENGINE] No relevant chunks found for: '{question}'")
            try:
                llm_provider = ProviderFactory.get_llm_provider()
                prompt = f"User Question: '{question}'\nProvide a clear, accurate, enterprise statutory knowledge answer."
                reply_text = llm_provider.generate(
                    model=kiki_settings.REASONING_MODEL,
                    prompt=prompt,
                    temperature=0.1
                )
            except Exception as e:
                logger.warning(f"Knowledge answer fallback error: {str(e)}")
                reply_text = "Knowledge lookup completed. Please refer to statutory guidelines or internal documentation."

            return {
                "question": question,
                "reply": reply_text,
                "citations": [],
                "retrieved_chunks_count": 0,
                "confidence": 0.85
            }

        # 3. Build Deduplicated User-Facing Citations (clean, no chunk IDs / confidence %)
        citations = citation_builder.build_citations(chunks)

        # 4. Assemble Ranked Context — only the top relevant chunks
        context_parts = []
        for idx, c in enumerate(chunks):
            filename = c['metadata']['filename'].replace(".md", "").replace("_", " ")
            page = c['metadata']['page_number']
            section = c['metadata']['section_heading']
            context_parts.append(
                f"[Source {idx+1}: {filename} (Page {page}, Section: {section})]\n{c['text']}"
            )
        context_str = "\n\n".join(context_parts)

        logger.info(f"[RAG ENGINE] Sending {len(chunks)} ranked chunks to LLM | Top Document: {chunks[0]['metadata'].get('filename')}")

        # 5. LLM System Prompt & User Prompt
        system_prompt = (
            "You are KIKI 2027, an enterprise AI assistant for FINPIXE ERP. "
            "Answer the user's question based strictly on the provided document sources. "
            "Be clear, precise, and professional. Do not include internal IDs, confidence scores, or technical metadata in your answer."
        )

        prompt = (
            f"Question: '{question}'\n\n"
            f"Retrieved Document Knowledge Context:\n{context_str}\n\n"
            f"Provide a comprehensive answer based on the context above."
        )

        # 6. LLM Synthesis via Local Ollama
        try:
            llm_provider = ProviderFactory.get_llm_provider()
            answer_text = llm_provider.generate(
                model=kiki_settings.REASONING_MODEL,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
        except Exception as e:
            logger.warning(f"LLM natural language synthesis error: {str(e)}")
            first_cite = citations[0] if citations else {}
            answer_text = (
                f"Based on knowledge document '{first_cite.get('document_name', 'document')}' "
                f"(Section: {first_cite.get('section_heading', 'General')}):\n{chunks[0]['text']}"
            )

        # 7. Append Clean User-Facing 'Sources' Section (no chunk IDs, no confidence %)
        full_reply = answer_text + citation_builder.format_citation_markdown(citations)

        return {
            "question": question,
            "reply": full_reply,
            "citations": citations,
            "retrieved_chunks_count": len(chunks),
            "confidence": chunks[0].get("confidence", 0.90) if chunks else 0.90
        }

local_rag_engine = LocalRAGEngine()
