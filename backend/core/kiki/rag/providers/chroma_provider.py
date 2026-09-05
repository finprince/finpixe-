"""
KIKI ChromaDB Vector Store Provider — Phase 17.1 Zero Hardcode Architecture
==============================================================================
Concrete implementation of BaseVectorStoreProvider for ChromaDB with ProviderCapabilities discovery.
Stores and validates index provenance metadata (embedding model, dimension, metric, normalization).
"""
import os
try:
    import chromadb
except ImportError:
    chromadb = None
from typing import Dict, Any, List, Optional
from ..interfaces.vector_store import BaseVectorStoreProvider
from ..interfaces.capabilities import ProviderCapabilities
from ..interfaces.embedding import BaseEmbeddingProvider
from .embedding_provider import bge_embedding_provider
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("chroma_provider")


class ChromaVectorStoreProvider(BaseVectorStoreProvider):
    """ChromaDB Vector Store Provider with Index Provenance Validation."""

    COLLECTION_NAME = "kiki_knowledge_documents"  # backwards-compat; runtime uses kiki_settings

    def __init__(
        self,
        persist_dir: str = None,
        embedding_provider: BaseEmbeddingProvider = None,
        collection_name: str = None
    ):
        self.persist_dir = persist_dir or kiki_settings.CHROMADB_PERSIST_DIRECTORY
        os.makedirs(self.persist_dir, exist_ok=True)
        self.embedding_provider = embedding_provider or bge_embedding_provider
        # Phase 17.4: prefer kiki_settings.PRIMARY_COLLECTION_NAME; fall back to class constant
        self.collection_name = (
            collection_name
            or getattr(kiki_settings, "PRIMARY_COLLECTION_NAME", self.COLLECTION_NAME)
        )
        if chromadb is None:
            self.client = None
            self.collection = None
            logger.warning("ChromaDB is not installed. ChromaVectorStoreProvider initialized in disabled mode.")
            return
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "KIKI Air-Gapped Knowledge Vector Store"}
        )

    def capabilities(self) -> ProviderCapabilities:
        embed_caps = self.embedding_provider.capabilities()
        return ProviderCapabilities(
            provider_name="chromadb",
            dimension=embed_caps.dimension,
            distance_metric=embed_caps.distance_metric,
            max_batch_size=100,
            supports_filtering=True,
            supports_quantization=False,
            model_id=embed_caps.model_id,
            normalized=embed_caps.normalized,
        )


    def get_provenance(self) -> Dict[str, Any]:
        """Returns dynamic metadata provenance from active ChromaDB collection."""
        try:
            coll_meta = self.collection.metadata or {}
            return {
                "embedding_model": coll_meta.get("embedding_model"),
                "embedding_dimension": coll_meta.get("embedding_dimension"),
                "distance_metric": coll_meta.get("distance_metric"),
                "normalized": coll_meta.get("normalized"),
                "corpus_version": coll_meta.get("corpus_version"),
                "index_version": coll_meta.get("index_version", self.collection_name),
                "created_at": coll_meta.get("created_at"),
                "document_count": coll_meta.get("document_count", 0),
                "chunk_count": self.count()
            }
        except Exception as e:
            logger.warning(f"[CHROMA PROVIDER] Error reading collection provenance: {e}")
            return {}

    def set_provenance(self, provenance_meta: Dict[str, Any]) -> None:
        """Sets provenance metadata on ChromaDB collection."""
        try:
            self.collection.modify(metadata=provenance_meta)
            logger.info(
                f"[CHROMA PROVIDER] Set provenance on '{self.collection_name}': "
                f"{provenance_meta}"
            )
        except Exception as e:
            logger.warning(f"[CHROMA PROVIDER] Failed to update collection provenance: {e}")

    def validate_provenance(self) -> tuple:
        """
        Validates active collection provenance against current runtime embedding provider.

        Phase 17.4 — corrected logic:
          EMPTY_COLLECTION:     count==0, any provenance state → OK (safe)
          COMPATIBLE:           provenance present and matches runtime
          PROVENANCE_MISSING:   count>0 but no embedding_model in metadata → NOT OK
          MIGRATION_REQUIRED:   count>0, provenance present but model/dim/metric mismatch

        INITIAL_INDEX is NO LONGER returned for non-empty collections.
        """
        count = self.count()
        caps = self.capabilities()
        prov = self.get_provenance()

        # Empty collection is always safe (no data, no risk)
        if count == 0:
            return True, "EMPTY_COLLECTION"

        # Non-empty but no provenance → legacy or corrupt index
        if not prov or not prov.get("embedding_model"):
            logger.warning(
                f"[CHROMA PROVIDER] ⚠️  Collection '{self.collection_name}' has {count} chunks "
                "but NO provenance metadata. State: PROVENANCE_MISSING."
            )
            return False, "PROVENANCE_MISSING"

        # Model mismatch check using canonical identity comparison
        from ..provenance import canonicalize_embedding_model_id
        index_model_canonical = canonicalize_embedding_model_id(prov.get("embedding_model"))
        runtime_model_canonical = canonicalize_embedding_model_id(caps.model_id)

        if index_model_canonical != runtime_model_canonical:
            return False, (
                f"MIGRATION_REQUIRED: model mismatch — "
                f"index={prov.get('embedding_model')} ({index_model_canonical}), "
                f"runtime={caps.model_id} ({runtime_model_canonical})"
            )


        # Dimension mismatch
        if prov.get("embedding_dimension") and prov.get("embedding_dimension") != caps.dimension:
            return False, (
                f"MIGRATION_REQUIRED: dimension mismatch — "
                f"index={prov.get('embedding_dimension')}, runtime={caps.dimension}"
            )

        # Metric mismatch
        if prov.get("distance_metric") and prov.get("distance_metric") != caps.distance_metric:
            return False, (
                f"MIGRATION_REQUIRED: metric mismatch — "
                f"index={prov.get('distance_metric')}, runtime={caps.distance_metric}"
            )

        return True, "COMPATIBLE"


    def add_vectors(
        self,
        vectors: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> int:
        if not documents:
            return 0
        generated_vectors = vectors if (vectors and len(vectors) == len(documents)) else self.embedding_provider.embed_documents(documents)

        try:
            self.collection.add(ids=ids, documents=documents, embeddings=generated_vectors, metadatas=metadatas)
        except Exception as e:
            if "dimension" in str(e).lower():
                logger.warning(f"[CHROMA PROVIDER] Collection '{self.collection_name}' dimension mismatch ({str(e)}). Recreating collection...")
                try:
                    self.client.delete_collection(self.collection_name)
                except Exception:
                    pass
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "KIKI Air-Gapped Knowledge Vector Store"}
                )
                self.collection.add(ids=ids, documents=documents, embeddings=generated_vectors, metadatas=metadatas)
            else:
                raise e

        logger.info(f"[CHROMA PROVIDER] Successfully indexed {len(documents)} document vectors into '{self.collection_name}'.")
        return len(documents)


    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        caps = self.capabilities()
        if len(query_vector) != caps.dimension and caps.dimension > 0:
            logger.error(
                f"[CHROMA PROVIDER] Dimension mismatch on query: "
                f"Query vector len={len(query_vector)}, Expected caps dim={caps.dimension}"
            )
            return []

        where_filter = filter_metadata if filter_metadata else None
        
        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where_filter
            )
        except Exception as e:
            logger.warning(f"[CHROMA PROVIDER] Query execution exception: {str(e)}")
            return []

        output = []
        if results and results.get("ids") and results["ids"][0]:
            ids_list = results["ids"][0]
            docs_list = results["documents"][0]
            metas_list = results["metadatas"][0]
            dists_list = results["distances"][0] if results.get("distances") else [0.0] * len(ids_list)

            for cid, doc, meta, dist in zip(ids_list, docs_list, metas_list, dists_list):
                confidence = max(0.0, min(1.0, 1.0 - (dist / 2.0))) if dist else 0.90
                output.append({
                    "chunk_id": cid,
                    "text": doc,
                    "metadata": meta,
                    "distance": dist,
                    "confidence": round(confidence, 4)
                })

        return output

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0


chroma_vector_store_provider = ChromaVectorStoreProvider()
