"""
KIKI Corpus Synchronization Validator — Phase 17.4 New Module
=============================================================
Provides validate_rag_corpus_sync() to compare Chroma dense index vs BM25 sparse index.
Detects corpus divergence (e.g. BM25=109 chunks vs Chroma=564 chunks).

Should be called:
  1. After ingestion (index_knowledge command)
  2. After reindex (reindex_kiki_knowledge command)
  3. Before index promotion (reindex_manager.py)
  4. From rag_status management command
  5. During forensic diagnostics
"""
import hashlib
from typing import Dict, Any, Set, List
from .providers.chroma_provider import chroma_vector_store_provider
from .pipeline.sparse_engine import bm25_sparse_engine
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("corpus_sync_validator")


def _get_chroma_chunk_ids(collection_name: str = None) -> Set[str]:
    """Fetches all chunk IDs from the active Chroma collection."""
    try:
        from .providers.chroma_provider import ChromaVectorStoreProvider
        from core.kiki.config import kiki_settings

        coll_name = collection_name or getattr(
            kiki_settings, "PRIMARY_COLLECTION_NAME", "kiki_knowledge_documents"
        )
        provider = ChromaVectorStoreProvider(collection_name=coll_name)
        # Fetch all IDs using get() — ChromaDB supports this
        result = provider.collection.get(include=[])
        ids = set(result.get("ids", []))
        return ids
    except Exception as e:
        logger.error(f"[CORPUS SYNC] Failed to fetch Chroma chunk IDs: {e}")
        return set()


def _get_global_chroma_chunk_ids(collection_name: str = None) -> Set[str]:
    """Fetches all chunk IDs from the global knowledge Chroma collection."""
    try:
        from .providers.chroma_provider import ChromaVectorStoreProvider
        from core.kiki.config import kiki_settings

        coll_name = collection_name or getattr(
            kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge"
        )
        provider = ChromaVectorStoreProvider(collection_name=coll_name)
        result = provider.collection.get(include=[])
        ids = set(result.get("ids", []))
        return ids
    except Exception as e:
        logger.error(f"[CORPUS SYNC] Failed to fetch global Chroma chunk IDs: {e}")
        return set()


def validate_rag_corpus_sync(
    collection_name: str = None,
    include_global: bool = False
) -> Dict[str, Any]:
    """
    Validates that the BM25 sparse index and Chroma dense index represent the same corpus.
    """
    from .pipeline.sparse_engine import get_bm25_engine
    from core.kiki.config import kiki_settings

    logger.info("[CORPUS SYNC] Running corpus synchronization validation...")

    coll_name = collection_name or getattr(
        kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge"
    )
    
    # Fetch BM25 sparse engine for target collection
    bm25_engine = get_bm25_engine(coll_name)
    sparse_ids = set(bm25_engine.get_corpus_manifest().keys())
    sparse_count = len(sparse_ids)

    # Fetch Chroma dense IDs for target collection
    primary_ids = _get_chroma_chunk_ids(coll_name)
    primary_count = len(primary_ids)

    # Optional global collection union
    global_ids: Set[str] = set()
    if include_global and coll_name != getattr(kiki_settings, "GLOBAL_COLLECTION_NAME", "finpixe_global_knowledge"):
        global_ids = _get_global_chroma_chunk_ids()

    global_count = len(global_ids)
    all_dense_ids = primary_ids | global_ids
    dense_count = len(all_dense_ids)

    common = sparse_ids & all_dense_ids
    missing_from_sparse = all_dense_ids - sparse_ids
    missing_from_dense = sparse_ids - all_dense_ids

    sync_status = (
        "SYNCHRONIZED"
        if (not missing_from_sparse and not missing_from_dense)
        else "INDEX_OUT_OF_SYNC"
    )

    result = {
        "dense_chunk_count": dense_count,
        "sparse_chunk_count": sparse_count,
        "common_chunk_count": len(common),
        "missing_from_dense": len(missing_from_dense),
        "missing_from_sparse": len(missing_from_sparse),
        "primary_collection_count": primary_count,
        "global_collection_count": global_count,
        "bm25_corpus_version": bm25_engine.corpus_version,
        "bm25_index_version": bm25_engine.index_version,
        "bm25_created_at": bm25_engine.created_at,
        "sync_status": sync_status,
    }


    if sync_status == "SYNCHRONIZED":
        logger.info(
            f"[CORPUS SYNC] ✅ SYNCHRONIZED: {len(common)} common chunks | "
            f"dense={dense_count} | sparse={sparse_count}"
        )
    else:
        logger.warning(
            f"[CORPUS SYNC] ❌ INDEX_OUT_OF_SYNC: "
            f"missing_from_sparse={len(missing_from_sparse)} | "
            f"missing_from_dense={len(missing_from_dense)} | "
            f"dense={dense_count} | sparse={sparse_count}"
        )

    return result


def run_quick_sync_check() -> bool:
    """
    Fast sync check — returns True if synchronized, False if diverged.
    Suitable for health-check endpoints and pre-promotion gates.
    """
    result = validate_rag_corpus_sync()
    return result["sync_status"] == "SYNCHRONIZED"
