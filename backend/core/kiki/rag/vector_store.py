"""
KIKI ChromaDB Vector Store & KnowledgeProvider Implementation — Phase 15 V3
===========================================================================
Manages ChromaDB collections, vector embeddings, metadata schemas, and strict multi-tenant isolation.
Implements the provider-agnostic KnowledgeProvider abstract interface.
"""
import os
import chromadb
from typing import Dict, Any, List, Optional
from .provider import KnowledgeProvider
from ..config import kiki_settings
from ..logging import get_kiki_logger

logger = get_kiki_logger("chroma_vector_store")


class ChromaVectorStore(KnowledgeProvider):
    """Enterprise ChromaDB Vector Store implementing KnowledgeProvider interface."""

    COLLECTION_NAME = "kiki_knowledge_documents"

    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or kiki_settings.CHROMADB_PERSIST_DIRECTORY
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "KIKI Air-Gapped Enterprise Knowledge Vector Store"}
        )

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]] = None) -> int:
        """
        Stores chunk text, metadata, and optional dense embeddings in ChromaDB.
        """
        if not chunks:
            return 0

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "document_id": c["document_id"],
                "filename": c["filename"],
                "document_name": c.get("filename", "Internal Knowledge Document"),
                "document_family": c.get("family", c["filename"].split(".")[0].split("_")[0]),
                "entity": c.get("entity", c.get("filename", "").replace(".md", "")),
                "page_number": int(c.get("page_number", 1)),
                "section_heading": str(c.get("section_heading", "General")),
                "tenant_id": str(c["tenant_id"]),
                "department": str(c.get("department", "General")),
                "security_level": str(c.get("security_level", "Internal"))
            }
            for c in chunks
        ]

        if embeddings and len(embeddings) == len(chunks):
            self.collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
        else:
            self.collection.add(ids=ids, documents=documents, metadatas=metadatas)

        logger.info(f"Successfully indexed {len(chunks)} chunks in ChromaDB vector store.")
        return len(chunks)

    def probe_vector(self, query_text: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Lightweight fast vector probe implementing KnowledgeProvider interface (< 5ms).
        """
        try:
            global_coll = self.client.get_or_create_collection("finpixe_global_knowledge")
            if global_coll.count() == 0:
                return {"is_candidate": False, "max_similarity": 0.0, "top_document": None, "top_family": None, "chunks_found": 0}

            from .providers.embedding_provider import bge_embedding_provider
            query_vec = bge_embedding_provider.embed_text(query_text)
            results = global_coll.query(query_embeddings=[query_vec], n_results=top_k)
            if results and results.get("distances") and results["distances"][0]:
                dists = results["distances"][0]
                metas = results["metadatas"][0]
                best_dist = dists[0]
                best_meta = metas[0] if metas else {}
                max_similarity = max(0.0, min(1.0, 1.0 - (best_dist / 2.0))) if best_dist else 0.90
                top_doc = best_meta.get("document_name", "Global Knowledge Document")
                top_family = best_meta.get("family", top_doc.split(".")[0].split("_")[0])

                # Dynamic routing threshold: 0.30 for vector candidates
                is_candidate = max_similarity >= 0.30 and top_doc is not None
                return {
                    "is_candidate": is_candidate,
                    "max_similarity": round(max_similarity, 4),
                    "top_document": top_doc,
                    "top_family": top_family,
                    "chunks_found": len(dists)
                }
        except Exception as e:
            logger.warning(f"Fast vector probe error: {str(e)}")

        return {"is_candidate": False, "max_similarity": 0.0, "top_document": None, "top_family": None, "chunks_found": 0}


    def probe_knowledge(self, query_text: str, top_k: int = 3) -> Dict[str, Any]:
        """Backward-compatible alias for probe_vector."""
        return self.probe_vector(query_text, top_k=top_k)

    def query_global(self, query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Queries the developer-managed global knowledge collection 'finpixe_global_knowledge'."""
        try:
            global_coll = self.client.get_or_create_collection("finpixe_global_knowledge")
            results = global_coll.query(query_texts=[query_text], n_results=top_k)
            output = []
            if results and results.get("ids") and results["ids"][0]:
                ids_list = results["ids"][0]
                docs_list = results["documents"][0]
                metas_list = results["metadatas"][0]
                dists_list = results["distances"][0] if results.get("distances") else [0.0] * len(ids_list)

                for cid, doc, meta, dist in zip(ids_list, docs_list, metas_list, dists_list):
                    confidence = max(0.0, min(1.0, 1.0 - (dist / 2.0))) if dist else 0.90
                    doc_name = meta.get("document_name", "Global Knowledge Document")
                    doc_family = meta.get("family", meta.get("document_family", doc_name.split(".")[0].split("_")[0]))
                    output.append({
                        "chunk_id": cid,
                        "text": doc,
                        "metadata": {
                            "filename": doc_name,
                            "document_name": doc_name,
                            "document_family": doc_family,
                            "entity": meta.get("entity", doc_name.replace(".md", "").replace("_", " ")),
                            "page_number": int(meta.get("page", meta.get("page_number", 1))),
                            "section_heading": meta.get("section", meta.get("section_heading", "General")),
                            "category": meta.get("category", "General"),
                            "department": meta.get("department", "General")
                        },
                        "distance": dist,
                        "confidence": round(confidence, 4)
                    })
            return output
        except Exception as e:
            logger.error(f"Error querying global knowledge collection: {str(e)}")
            return []

    def query_tenant(
        self,
        query_text: str,
        tenant_id: str,
        top_k: int = 10,
        department: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Queries tenant isolated knowledge collection."""
        where_filter = {"tenant_id": str(tenant_id)}
        if department:
            where_filter["department"] = str(department)

        results = self.collection.query(query_texts=[query_text], n_results=top_k, where=where_filter)
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

    def query(self, query_text: str, tenant_id: str, top_k: int = 10, department: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
        return self.query_tenant(query_text, tenant_id, top_k=top_k, department=department)


chroma_store = ChromaVectorStore()
