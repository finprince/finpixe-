"""
KIKI Ingestion Pipeline — Phase 17.4 Production Hardened
=========================================================
Structured ingestion pipeline: Document -> Parser -> Cleaner -> Heading Extraction ->
Semantic Chunking -> Metadata -> Chunk Validation -> Store into Chroma + BM25 with Provenance & Sync Check.

Phase 17.4 (P0.2 Fix):
  - User-uploaded documents are indexed into BOTH Chroma (dense) and BM25 (sparse)
  - Provenance metadata written to Chroma DB collection
  - Corpus sync validated after every upload batch
"""
import time
import hashlib
from typing import Dict, Any, List
from ..loader import document_loader
from ..chunker import semantic_chunker
from .cleaner import text_cleaner
from .structure import structure_extractor
from .metadata import metadata_generator
from .validator import chunk_validator
from ..providers.chroma_provider import chroma_vector_store_provider
from ..providers.embedding_provider import bge_embedding_provider
from ..pipeline.sparse_engine import get_bm25_engine
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("ingestion_pipeline")


class IngestionPipeline:
    """Enterprise Structured Ingestion & Chunk Validation Pipeline — Phase 17.4 Hardened."""

    def process_file(
        self,
        file_path: str,
        filename: str,
        doc_id: str,
        category: str = "General",
        tenant_id: str = "global",
        security_level: str = "Public",
        collection_name: str = None
    ) -> Dict[str, Any]:
        """
        Runs document through clean structured ingestion pipeline.
        Indexes into Chroma (dense) + BM25 (sparse), attaches provenance, validates sync.
        """
        target_collection = collection_name or getattr(
            kiki_settings, "PRIMARY_COLLECTION_NAME", "kiki_knowledge_documents"
        )
        logger.info(
            f"[INGESTION PIPELINE] Ingesting document '{filename}' (ID: {doc_id}) "
            f"into collection '{target_collection}'..."
        )

        # 1. Document Parsing
        doc_data = document_loader.load_document(file_path, filename=filename)

        # 2. Text Cleaning
        cleaned_text = text_cleaner.clean_text(doc_data.get("full_text", ""))
        doc_data["full_text"] = cleaned_text

        # 3. Heading & Structural Heading Path Extraction
        heading_path = structure_extractor.extract_heading_path(cleaned_text)

        # 4. Semantic Chunking
        raw_chunks = semantic_chunker.chunk_document(
            doc_data=doc_data,
            doc_id=doc_id,
            tenant_id=tenant_id,
            department=category,
            security_level=security_level
        )

        if not raw_chunks:
            return {"status": "EMPTY", "chunks_indexed": 0}

        # 5. Metadata Enrichment & Heading Path Attachment
        enriched_chunks = []
        for c in raw_chunks:
            c["heading_path"] = heading_path
            meta = metadata_generator.generate_metadata(
                chunk=c,
                doc_id=doc_id,
                filename=filename,
                category=category,
                tenant_id=tenant_id,
                security_level=security_level
            )
            # Ensure page is -1 if unavailable (Chroma MetadataValue type constraint)
            if not c.get("page_metadata_available", False):
                meta["page"] = -1
                meta["page_number"] = -1
            c["metadata"] = meta
            enriched_chunks.append(c)

        # 6. Strict Chunk Validation Shield
        validated_chunks = chunk_validator.validate_chunks(enriched_chunks)

        if not validated_chunks:
            logger.warning(f"[INGESTION PIPELINE] All chunks rejected by validator for '{filename}'.")
            return {"status": "REJECTED", "chunks_indexed": 0}

        # 7. Add to Vector DB via ChromaVectorStoreProvider
        ids = [c["chunk_id"] for c in validated_chunks]
        documents = [c["text"] for c in validated_chunks]
        metadatas = [c["metadata"] for c in validated_chunks]

        # Use collection-scoped provider
        from ..providers.chroma_provider import ChromaVectorStoreProvider
        provider = ChromaVectorStoreProvider(collection_name=target_collection)

        # Idempotency check: clear previous chunks for this document_id if re-ingesting
        try:
            provider.collection.delete(where={"document_id": doc_id})
        except Exception:
            pass

        indexed_count = provider.add_vectors(
            vectors=None,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )


        # 8. Phase 17.4: Write Chroma Collection Provenance
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        prov_meta = {
            "embedding_model": bge_embedding_provider.model_name or "BAAI/bge-large-en-v1.5",
            "embedding_dimension": bge_embedding_provider._dim or 1024,
            "distance_metric": getattr(kiki_settings, "EMBEDDING_DISTANCE_METRIC", "cosine"),
            "normalized": str(getattr(kiki_settings, "EMBEDDING_NORMALIZED", True)),
            "corpus_version": f"user_corpus_{int(time.time())}",
            "index_version": target_collection,
            "schema_version": getattr(kiki_settings, "SCHEMA_VERSION", "2025.1"),
            "document_count": 1,
            "chunk_count": provider.count(),
            "created_at": ts,
        }
        provider.set_provenance(prov_meta)

        # 9. Phase 17.4 (P0.2 Fix): Index into collection-scoped BM25 sparse engine
        bm25_engine = get_bm25_engine(target_collection)
        # Combine existing BM25 chunks + new validated chunks
        existing_chunks = bm25_engine.get_all_chunks()
        # Remove any previous chunks for this document_id if re-ingesting
        filtered_existing = [c for c in existing_chunks if c.get("document_id") != doc_id]
        all_user_chunks = filtered_existing + validated_chunks
        bm25_engine.index_chunks(
            chunks=all_user_chunks,
            corpus_version=prov_meta["corpus_version"],
            index_version=target_collection
        )

        # 10. Phase 17.4: Validate Corpus Sync
        sync_status = "NOT_CHECKED"
        try:
            from ..corpus_sync import validate_rag_corpus_sync
            sync_result = validate_rag_corpus_sync(
                collection_name=target_collection,
                include_global=False
            )
            sync_status = sync_result.get("sync_status", "UNKNOWN")
            logger.info(
                f"[INGESTION PIPELINE] ✅ Ingested '{filename}': {indexed_count} chunks into '{target_collection}' | "
                f"Chroma={provider.count()}, BM25={bm25_engine.count()} | Corpus Sync: {sync_status}"
            )
        except Exception as sync_e:
            logger.warning(f"[INGESTION PIPELINE] Corpus sync check warning: {sync_e}")

        return {
            "document_id": doc_id,
            "filename": filename,
            "category": category,
            "total_pages": doc_data["total_pages"],
            "raw_chunks": len(raw_chunks),
            "chunks_indexed": indexed_count,
            "corpus_sync_status": sync_status,
            "status": "SUCCESS"
        }


ingestion_pipeline = IngestionPipeline()
