"""
KIKI BM25 Sparse Search Engine — Phase 17.4 Hardened & Collection-Scoped
========================================================================
Concrete implementation of BaseSparseRetriever for lexical search.

Phase 17.4 changes:
  - Collection-scoped BM25 indexes: finpixe_global_knowledge vs kiki_knowledge_documents
  - get_bm25_engine(collection_name) singleton registry function
  - Added corpus_manifest: Dict[str, str] → {chunk_id: content_hash} to every save
  - Added corpus_version, index_version, created_at to pickle schema
  - Added get_corpus_manifest() for external sync validation
  - Added validate_corpus_sync(chroma_chunk_ids) returning detailed sync report
"""
import os
import json
import pickle
import math
import re
import time
import hashlib
from typing import Dict, Any, List, Optional, Set
from ..interfaces.sparse import BaseSparseRetriever
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("sparse_bm25_engine")


class BM25SparseEngine(BaseSparseRetriever):
    """BM25 Lexical Inverted Index & Search Engine — Phase 17.4 Multi-Corpus."""

    def __init__(self, storage_dir: str = None, collection_name: str = "finpixe_global_knowledge"):
        self.collection_name = collection_name
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            )
            self.storage_dir = os.path.join(base_dir, "data", "bm25")

        os.makedirs(self.storage_dir, exist_ok=True)
        # Dedicated pickle file per collection (backwards compatible for legacy single file)
        self.index_file = os.path.join(self.storage_dir, f"bm25_{self.collection_name}.pkl")
        self.legacy_index_file = os.path.join(self.storage_dir, "bm25_index.pkl")

        # BM25 state
        self.chunks: List[Dict[str, Any]] = []
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.total_docs: int = 0

        # Phase 17.4: corpus provenance fields
        self.corpus_manifest: Dict[str, str] = {}   # chunk_id → content_hash
        self.corpus_version: str = ""
        self.index_version: str = ""
        self.created_at: str = ""

        # BM25 algorithm constants (standard Okapi BM25)
        self.k1: float = 1.5
        self.b: float = 0.75

        self._load_index()

    # ── Public accessors ──────────────────────────────────────────────────────

    def count(self) -> int:
        """Returns total indexed chunk count."""
        return len(self.chunks)

    def get_all_chunks(self) -> List[Dict[str, Any]]:
        """Returns all indexed chunks."""
        return self.chunks

    def get_corpus_manifest(self) -> Dict[str, str]:
        """Returns {chunk_id: content_hash} for all indexed chunks."""
        return dict(self.corpus_manifest)

    def get_provenance(self) -> Dict[str, Any]:
        """Returns BM25 index provenance metadata."""
        return {
            "collection_name": self.collection_name,
            "chunk_count": self.total_docs,
            "corpus_version": self.corpus_version,
            "index_version": self.index_version,
            "created_at": self.created_at,
            "corpus_manifest_size": len(self.corpus_manifest),
        }

    # ── Phase 17.4: Corpus Sync Validation ───────────────────────────────────

    def validate_corpus_sync(
        self, chroma_chunk_ids: Set[str]
    ) -> Dict[str, Any]:
        """
        Compares BM25 indexed chunk IDs against the provided Chroma chunk ID set.
        """
        sparse_ids = set(self.corpus_manifest.keys())
        common = sparse_ids & chroma_chunk_ids
        missing_from_sparse = chroma_chunk_ids - sparse_ids
        missing_from_dense = sparse_ids - chroma_chunk_ids

        sync_status = (
            "SYNCHRONIZED"
            if (not missing_from_sparse and not missing_from_dense)
            else "INDEX_OUT_OF_SYNC"
        )

        report = {
            "collection_name": self.collection_name,
            "sparse_chunk_count": len(sparse_ids),
            "dense_chunk_count": len(chroma_chunk_ids),
            "common_chunk_count": len(common),
            "missing_from_sparse": len(missing_from_sparse),
            "missing_from_dense": len(missing_from_dense),
            "sparse_corpus_version": self.corpus_version,
            "sparse_index_version": self.index_version,
            "sync_status": sync_status,
        }

        if sync_status == "SYNCHRONIZED":
            logger.info(
                f"[BM25 ENGINE:{self.collection_name}] ✅ Corpus sync: SYNCHRONIZED "
                f"({len(common)} chunks match)"
            )
        else:
            logger.warning(
                f"[BM25 ENGINE:{self.collection_name}] ❌ Corpus sync: INDEX_OUT_OF_SYNC | "
                f"missing_from_sparse={len(missing_from_sparse)} | "
                f"missing_from_dense={len(missing_from_dense)}"
            )

        return report

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_chunks(
        self,
        chunks: List[Dict[str, Any]],
        corpus_version: str = "",
        index_version: str = "",
    ) -> int:
        """
        Indexes candidate chunks, persists BM25 structures + corpus manifest to disk.
        """
        if not chunks:
            return 0

        self.chunks = list(chunks)
        self.total_docs = len(self.chunks)
        self.doc_freqs = {}
        self.doc_lengths = []
        total_len = 0

        # Build corpus_manifest: chunk_id → sha256(text)[:16]
        self.corpus_manifest = {}
        for c in self.chunks:
            cid = c.get("chunk_id", "")
            text = c.get("text", "")
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            self.corpus_manifest[cid] = content_hash

        for c in self.chunks:
            tokens = self._tokenize(c.get("text", ""))
            self.doc_lengths.append(len(tokens))
            total_len += len(tokens)
            unique_tokens = set(tokens)
            for tok in unique_tokens:
                self.doc_freqs[tok] = self.doc_freqs.get(tok, 0) + 1

        self.avg_doc_len = (
            total_len / self.total_docs if self.total_docs > 0 else 0.0
        )

        # Provenance
        ts = int(time.time())
        self.corpus_version = corpus_version or f"corpus_{ts}"
        self.index_version = index_version or f"idx_{ts}"
        self.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

        self._save_index()
        logger.info(
            f"[BM25 ENGINE:{self.collection_name}] ✅ Indexed {self.total_docs} chunks | "
            f"corpus_version={self.corpus_version} | index_version={self.index_version}"
        )
        return self.total_docs

    # ── Search ────────────────────────────────────────────────────────────────

    def search_sparse(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Executes BM25 score calculation for query tokens across indexed chunks."""
        if not self.chunks or self.total_docs == 0:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = [0.0] * self.total_docs

        for token in query_tokens:
            df = self.doc_freqs.get(token, 0)
            if df == 0:
                continue
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            for idx, c in enumerate(self.chunks):
                doc_tokens = self._tokenize(c.get("text", ""))
                tf = doc_tokens.count(token)
                if tf == 0:
                    continue
                doc_len = self.doc_lengths[idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (
                    1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0))
                )
                scores[idx] += idf * (numerator / denominator)

        scored_results = []
        for idx, score in enumerate(scores):
            if score > 0.0:
                c_copy = dict(self.chunks[idx])
                if filter_metadata:
                    meta = c_copy.get("metadata", {})
                    if not all(meta.get(k) == v for k, v in filter_metadata.items()):
                        continue
                c_copy["bm25_score"] = round(score, 4)
                c_copy["confidence"] = min(1.0, round(score / 10.0, 4))
                c_copy["collection_name"] = self.collection_name
                scored_results.append(c_copy)

        scored_results.sort(key=lambda x: x["bm25_score"], reverse=True)
        logger.info(
            f"[BM25 ENGINE:{self.collection_name}] Searched '{query[:60]}': "
            f"found {len(scored_results)} matching chunks."
        )
        return scored_results[:top_k]

    # ── Persistence ───────────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[A-Za-z0-9\-_]{2,}\b', text.lower())

    def _save_index(self) -> None:
        try:
            with open(self.index_file, "wb") as f:
                pickle.dump(
                    {
                        "chunks": self.chunks,
                        "doc_freqs": self.doc_freqs,
                        "doc_lengths": self.doc_lengths,
                        "avg_doc_len": self.avg_doc_len,
                        "total_docs": self.total_docs,
                        "corpus_manifest": self.corpus_manifest,
                        "corpus_version": self.corpus_version,
                        "index_version": self.index_version,
                        "created_at": self.created_at,
                        "collection_name": self.collection_name,
                    },
                    f,
                )
            # Also update legacy file if this is global collection for backwards compatibility
            if self.collection_name == "finpixe_global_knowledge":
                with open(self.legacy_index_file, "wb") as f:
                    pickle.dump(
                        {
                            "chunks": self.chunks,
                            "doc_freqs": self.doc_freqs,
                            "doc_lengths": self.doc_lengths,
                            "avg_doc_len": self.avg_doc_len,
                            "total_docs": self.total_docs,
                            "corpus_manifest": self.corpus_manifest,
                            "corpus_version": self.corpus_version,
                            "index_version": self.index_version,
                            "created_at": self.created_at,
                            "collection_name": self.collection_name,
                        },
                        f,
                    )
        except Exception as e:
            logger.warning(f"[BM25 SAVE ERROR:{self.collection_name}] Failed to save index: {e}")

    def _load_index(self) -> None:
        file_to_load = self.index_file
        if not os.path.exists(file_to_load) and self.collection_name == "finpixe_global_knowledge" and os.path.exists(self.legacy_index_file):
            file_to_load = self.legacy_index_file

        if os.path.exists(file_to_load):
            try:
                with open(file_to_load, "rb") as f:
                    data = pickle.load(f)
                self.chunks = data.get("chunks", [])
                self.doc_freqs = data.get("doc_freqs", {})
                self.doc_lengths = data.get("doc_lengths", [])
                self.avg_doc_len = data.get("avg_doc_len", 0.0)
                self.total_docs = data.get("total_docs", 0)
                self.corpus_manifest = data.get("corpus_manifest", {})
                self.corpus_version = data.get("corpus_version", "LEGACY")
                self.index_version = data.get("index_version", "LEGACY")
                self.created_at = data.get("created_at", "UNKNOWN")
                logger.info(
                    f"[BM25 ENGINE:{self.collection_name}] Loaded {self.total_docs} chunks from disk | "
                    f"corpus_version={self.corpus_version} | "
                    f"manifest_size={len(self.corpus_manifest)}"
                )
            except Exception as e:
                logger.warning(f"[BM25 LOAD ERROR:{self.collection_name}] Failed to load disk index: {e}")


# ── Global BM25 Engine Registry ───────────────────────────────────────────────
_BM25_ENGINES: Dict[str, BM25SparseEngine] = {}


def get_bm25_engine(collection_name: str = "finpixe_global_knowledge") -> BM25SparseEngine:
    """Returns collection-scoped singleton BM25 engine instance."""
    if collection_name not in _BM25_ENGINES:
        _BM25_ENGINES[collection_name] = BM25SparseEngine(collection_name=collection_name)
    return _BM25_ENGINES[collection_name]


# Backwards compatibility export: default global engine
bm25_sparse_engine = get_bm25_engine("finpixe_global_knowledge")
