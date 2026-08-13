"""
KIKI Developer Knowledge Indexer Module — Phase 17.4 Hardened
==============================================================
Recursively scans backend/core/kiki/knowledge/, parses, cleans, chunks, validates, embeds,
and indexes global knowledge into the GLOBAL ChromaDB collection AND BM25 sparse index.

Phase 17.4 changes:
  - Removed dual-write bug: knowledge indexer now writes ONLY to the global collection
    (finpixe_global_knowledge). It does NOT also write to kiki_knowledge_documents.
    kiki_knowledge_documents is reserved for user-uploaded documents (separate corpus).
  - All hardcoded strings replaced by kiki_settings constants.
  - page_number is None for DOCX/TXT (not fabricated as 1).
  - page_metadata_available propagated into stored chunk metadata.
  - version from kiki_settings.SCHEMA_VERSION.
  - After indexing: corpus provenance written to ChromaDB collection.
  - After indexing: BM25 indexes with corpus_version & index_version.
  - After indexing: validate_rag_corpus_sync() called and result logged.
"""
import os
import time
import hashlib
from typing import Dict, Any, List

from .loader import document_loader
from .ingestion.pipeline import ingestion_pipeline
from .pipeline.sparse_engine import bm25_sparse_engine
from .providers.chroma_provider import ChromaVectorStoreProvider
from .providers.embedding_provider import bge_embedding_provider
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("knowledge_indexer")


class KnowledgeIndexer:
    """Developer-Managed Global Knowledge Base Indexer — Phase 17.4 Hardened."""

    def __init__(self, knowledge_dir: str = None):
        if knowledge_dir:
            self.knowledge_dir = knowledge_dir
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.knowledge_dir = os.path.join(base_dir, "knowledge")

    def _get_global_collection_name(self) -> str:
        """Returns global collection name from settings (not hardcoded)."""
        return getattr(kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge")

    def _get_or_create_collection(self, rebuild: bool = False):
        """Gets or recreates global ChromaDB collection ensuring dimension compatibility."""
        global_coll_name = self._get_global_collection_name()

        # Phase 17.4: use ChromaVectorStoreProvider for the global collection
        # This is a SEPARATE instance from chroma_vector_store_provider (which serves
        # kiki_knowledge_documents / user-uploaded docs). DO NOT mix them.
        global_provider = ChromaVectorStoreProvider(collection_name=global_coll_name)
        client = global_provider.client

        if rebuild:
            try:
                client.delete_collection(global_coll_name)
                logger.info(f"[KNOWLEDGE INDEXER] Deleted '{global_coll_name}' for rebuild.")
            except Exception:
                pass

        try:
            coll = client.get_or_create_collection(
                name=global_coll_name,
                metadata={"description": "FINPIXE Developer-Managed Global Knowledge Library"}
            )
            return coll, client
        except Exception as e:
            logger.warning(f"[KNOWLEDGE INDEXER] Collection creation error: {e}")
            try:
                client.delete_collection(global_coll_name)
            except Exception:
                pass
            coll = client.get_or_create_collection(
                name=global_coll_name,
                metadata={"description": "FINPIXE Developer-Managed Global Knowledge Library"}
            )
            return coll, client

    def index_all(self, rebuild: bool = False) -> Dict[str, Any]:
        """
        Recursively scans knowledge_dir, parses documents through IngestionPipeline,
        embeds using active BGE provider, and stores into:
          1. ChromaDB global collection (finpixe_global_knowledge)
          2. BM25 sparse index

        Phase 17.4:
          - NO dual write to kiki_knowledge_documents (that collection is user-uploaded docs)
          - Provenance written to global collection after indexing
          - Corpus sync validated after indexing
        """
        logger.info(
            f"[KNOWLEDGE INDEXER] Starting global knowledge indexing from: {self.knowledge_dir}"
        )
        start_time = time.time()

        # Eagerly preload BGE embedding provider on CUDA before processing
        if not bge_embedding_provider.is_loaded():
            logger.info("[KNOWLEDGE INDEXER] Eagerly preloading BGE CUDA embedding provider...")
            bge_embedding_provider.preload()

        global_coll_name = self._get_global_collection_name()
        global_coll, _ = self._get_or_create_collection(rebuild=rebuild)

        # Settings — all from kiki_settings (no hardcodes)
        tenant_id = getattr(kiki_settings, "GLOBAL_KNOWLEDGE_TENANT_ID", "global")
        security_level = getattr(kiki_settings, "GLOBAL_KNOWLEDGE_SECURITY_LEVEL", "Public")
        schema_version = getattr(kiki_settings, "SCHEMA_VERSION", "2025.1")

        indexed_files = []
        total_pages_scanned = 0
        total_chunks_indexed = 0
        all_indexed_chunks: List[Dict[str, Any]] = []
        corpus_hash_input = []

        for root, dirs, files in os.walk(self.knowledge_dir):
            category = os.path.basename(root) if root != self.knowledge_dir else "General"

            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext not in document_loader.SUPPORTED_EXTENSIONS:
                    continue

                full_path = os.path.join(root, file)
                doc_id = f"gdoc_{file.replace('.', '_')}"

                try:
                    # Phase 1: Load document
                    doc_data = document_loader.load_document(full_path, filename=file)
                    pages = doc_data.get("total_pages", 1)
                    total_pages_scanned += pages

                    # Phase 2: Chunk with page_metadata_available propagated
                    from .chunker import semantic_chunker
                    raw_chunks = semantic_chunker.chunk_document(
                        doc_data=doc_data,
                        doc_id=doc_id,
                        tenant_id=tenant_id,
                        department=category,
                        security_level=security_level,
                    )

                    if not raw_chunks:
                        indexed_files.append({
                            "filename": file,
                            "category": category,
                            "pages": pages,
                            "chunks": 0,
                            "status": "EMPTY_DOCUMENT",
                        })
                        continue

                    # Phase 3: Build metadata per chunk — Phase 17.4 page correctness
                    ids = [c["chunk_id"] for c in raw_chunks]
                    documents = [c["text"] for c in raw_chunks]
                    page_meta_available = doc_data.get("page_metadata_available", False)

                    metadatas = []
                    for c in raw_chunks:
                        raw_page = c.get("page_number")  # None for DOCX
                        # ChromaDB MetadataValue cannot be None — use -1 as sentinel for "not available".
                        # citations.py checks page_metadata_available=False to avoid showing -1.
                        page_val = raw_page if (page_meta_available and raw_page is not None) else -1
                        metadatas.append({
                            "document_name": file,
                            "filename": file,
                            "category": category,
                            # Phase 17.4: -1 = page not physically available (DOCX/TXT sentinel)
                            "page": page_val,
                            "page_number": page_val,
                            # Phase 17.4: bool flag — True only for PDF with real pypdf pages
                            "page_metadata_available": page_meta_available,
                            "section": str(c.get("section_heading", "General")),
                            "section_heading": str(c.get("section_heading", "General")),
                            "chunk_id": c["chunk_id"],
                            # Phase 17.4: version from settings
                            "version": schema_version,
                            "tenant_id": tenant_id,
                            "security_level": security_level,
                            "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        })
                        corpus_hash_input.append(c["text"])

                    # Phase 4: Embed using active BGE provider
                    embeddings = bge_embedding_provider.embed_documents(documents)

                    # Phase 5: Write to GLOBAL collection ONLY (using upsert for idempotency)
                    try:
                        global_coll.upsert(
                            ids=ids,
                            documents=documents,
                            embeddings=embeddings,
                            metadatas=metadatas,
                        )
                    except Exception as add_e:
                        if "dimension" in str(add_e).lower():
                            logger.warning(
                                f"[KNOWLEDGE INDEXER] Dimension mismatch on "
                                f"'{global_coll_name}'. Rebuilding..."
                            )
                            global_coll, _ = self._get_or_create_collection(rebuild=True)
                            global_coll.upsert(
                                ids=ids,
                                documents=documents,
                                embeddings=embeddings,
                                metadatas=metadatas,
                            )
                        else:
                            raise add_e

                    total_chunks_indexed += len(raw_chunks)
                    all_indexed_chunks.extend(raw_chunks)

                    indexed_files.append({
                        "filename": file,
                        "category": category,
                        "pages": pages,
                        "chunks": len(raw_chunks),
                        "status": "SUCCESS",
                    })
                    logger.info(
                        f"[KNOWLEDGE INDEXER] Indexed '{file}' "
                        f"(Category: {category}, Chunks: {len(raw_chunks)}, "
                        f"PageMetaAvailable: {page_meta_available})"
                    )

                except Exception as e:
                    logger.error(f"[KNOWLEDGE INDEXER] Error indexing '{file}': {e}")
                    indexed_files.append({
                        "filename": file,
                        "category": category,
                        "pages": 0,
                        "chunks": 0,
                        "status": f"FAILED: {e}",
                    })

        execution_time = round(time.time() - start_time, 2)

        # Purge any stale chunk IDs from Chroma that are no longer part of the active corpus
        if all_indexed_chunks:
            current_ids = set(c["chunk_id"] for c in all_indexed_chunks)
            try:
                existing_res = global_coll.get(include=[])
                existing_ids = set(existing_res.get("ids", []))
                stale_ids = list(existing_ids - current_ids)
                if stale_ids:
                    global_coll.delete(ids=stale_ids)
                    logger.info(f"[KNOWLEDGE INDEXER] Purged {len(stale_ids)} stale chunk IDs from '{global_coll_name}'.")
            except Exception as purge_e:
                logger.warning(f"[KNOWLEDGE INDEXER] Stale chunk purge failed: {purge_e}")

        # Phase 5: Write full provenance to global collection
        if all_indexed_chunks:
            corpus_hash = hashlib.sha256(
                "\n".join(corpus_hash_input).encode("utf-8")
            ).hexdigest()[:16]
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            index_version = f"idx_{int(time.time())}"
            corpus_version = f"corpus_{corpus_hash}"

            provenance = {
                "embedding_model": bge_embedding_provider.model_name or "",
                "embedding_dimension": bge_embedding_provider._dim or 0,
                "distance_metric": getattr(kiki_settings, "EMBEDDING_DISTANCE_METRIC", "cosine"),
                "normalized": str(getattr(kiki_settings, "EMBEDDING_NORMALIZED", True)),
                "corpus_version": corpus_version,
                "corpus_hash": corpus_hash,
                "index_version": index_version,
                "schema_version": schema_version,
                "document_count": len(indexed_files),
                "chunk_count": total_chunks_indexed,
                "created_at": ts,
            }
            try:
                global_coll.modify(metadata=provenance)
                logger.info(
                    f"[KNOWLEDGE INDEXER] ✅ Provenance written to '{global_coll_name}': "
                    f"model={provenance['embedding_model']}, "
                    f"chunks={total_chunks_indexed}, corpus_version={corpus_version}"
                )
            except Exception as e:
                logger.warning(f"[KNOWLEDGE INDEXER] Failed to write provenance: {e}")

        # Phase 6: Index BM25 sparse index with corpus provenance
        if all_indexed_chunks:
            from .pipeline.sparse_engine import get_bm25_engine
            target_bm25 = get_bm25_engine(global_coll_name)
            target_bm25.index_chunks(
                chunks=all_indexed_chunks,
                corpus_version=corpus_version,
                index_version=index_version,
            )
            logger.info(
                f"[KNOWLEDGE INDEXER] ✅ BM25 indexed {len(all_indexed_chunks)} chunks for '{global_coll_name}' | "
                f"corpus_version={corpus_version}"
            )

        # Phase 7: Validate corpus sync — compare global knowledge BM25 against global Chroma only
        # NOTE: kiki_knowledge_documents (user-uploaded docs) is a SEPARATE corpus.
        # BM25 here represents global knowledge only, so we validate against global collection only.
        sync_status = "NOT_CHECKED"
        try:
            from .corpus_sync import validate_rag_corpus_sync
            sync_result = validate_rag_corpus_sync(
                collection_name=global_coll_name,
                include_global=False  # compare BM25 only against the global collection
            )
            sync_status = sync_result.get("sync_status", "UNKNOWN")
            if sync_status != "SYNCHRONIZED":
                logger.warning(
                    f"[KNOWLEDGE INDEXER] ⚠️  Corpus sync after indexing: {sync_status} | "
                    f"dense={sync_result.get('primary_collection_count')} | "
                    f"sparse={sync_result.get('sparse_chunk_count')}"
                )
        except Exception as sync_e:
            logger.warning(f"[KNOWLEDGE INDEXER] Corpus sync check failed: {sync_e}")


        logger.info(
            f"[KNOWLEDGE INDEXER] Completed in {execution_time}s | "
            f"Chunks: {total_chunks_indexed} | Corpus sync: {sync_status}"
        )

        return {
            "collection": global_coll_name,
            "total_documents": len(indexed_files),
            "total_pages": total_pages_scanned,
            "total_chunks": total_chunks_indexed,
            "execution_time_seconds": execution_time,
            "corpus_sync_status": sync_status,
            "file_details": indexed_files,
        }


knowledge_indexer = KnowledgeIndexer()
