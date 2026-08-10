# KIKI 2027 — PHASE 17.3
# CODE PATH AUDIT REPORT
**Generated:** 2026-08-10  
**Auditor:** KIKI Phase 17.3 Forensic Engineering  
**Scope:** Complete KIKI backend code path from HTTP request to final answer

---

## 1. System Architecture Overview

```
HTTP Request (POST /api/v2/kiki/chat/)
    ↓
APIView (core/kiki/api/views.py)
    ↓
AIKernelOrchestrator.process_request()     [kernel/orchestrator.py]
    ↓
ConversationContextManager.process()       [context/context_manager.py]
    ↓
NLUAnalyzer.analyze()                      [context/nlu_analyzer.py] — Ollama llama3
    ↓
AIPlanner.plan()                           [planner/planner.py]
    ↓
KnowledgeRetrievalCapability.execute()     [capabilities/knowledge_retrieval.py]
    ↓
ExecutionPipeline.run()                    [rag/execution_pipeline.py]
    ↓
BGEEmbeddingProvider.embed_text()          [rag/providers/embedding_provider.py] — BAAI/bge-large-en-v1.5 1024-dim
    ↓
ChromaVectorStoreProvider.query_vectors()  [rag/providers/chroma_provider.py] — kiki_knowledge_documents
    ↓
BM25SparseEngine.search_sparse()           [rag/pipeline/sparse_engine.py]
    ↓
RRFFusionEngine.fuse_results()             [rag/pipeline/fusion_engine.py]
    ↓
LocalRerankerProvider.rerank()             [rag/providers/reranker_provider.py] — cross-encoder/ms-marco-MiniLM-L-6-v2
    ↓
EvidenceBuilder.build_evidence()           [rag/pipeline/evidence_builder.py]
    ↓
EvidenceAggregator.aggregate()             [evidence/aggregator.py]
    ↓
ContextCompressorEngine.compress()         [rag/pipeline/compressor_engine.py]
    ↓
OllamaClient.generate()                    [runtime/ollama_client.py] — llama3:latest
    ↓
CitationBuilder.build_citations()          [rag/citations.py]
    ↓
JSON Response to Frontend
```

---

## 2. Component-Level Audit Table

| Component | File | Class | Method | Config Source | Failure Handling | Logging |
|-----------|------|-------|--------|--------------|-----------------|---------|
| **API Entry Point** | `core/kiki/api/views.py` | `KikiChatAPIView` | `post()` | `urls.py` | HTTP 500 fallback | request/response logged |
| **Kernel Orchestrator** | `core/kiki/kernel/orchestrator.py` | `AIKernelOrchestrator` | `process_request()` | `kiki_settings` | Exception wrapper → fallback reply | trace_id, tenant_id |
| **NLU Analyzer** | `core/kiki/context/nlu_analyzer.py` | `NLUAnalyzer` | `analyze()` | Ollama ROUTER_MODEL=llama3:latest | Fallback to passthrough | [NLU ANALYZER] component |
| **AI Planner** | `core/kiki/planner/` | `AIPlanner` | `plan()` | Plugin priority registry | REJECT policy if no plugin | [AI PLANNER 16.1] component |
| **Capability Registry** | `core/kiki/capabilities/` | `CapabilityRegistry` | `register()` | Plugin priority (90/85/80/70) | Zero plugins → REJECT | [CAPABILITY REGISTRY] |
| **Knowledge Retrieval** | `core/kiki/capabilities/` | `KnowledgeRetrievalCapability` | `execute()` | Priority=90 | Probe threshold gate | capability logs |
| **Execution Pipeline** | `core/kiki/rag/execution_pipeline.py` | `ExecutionPipeline` | `run()` | Internal | Timeout → error evidence | [EXECUTION PIPELINE] |
| **Embedding Provider** | `core/kiki/rag/providers/embedding_provider.py` | `BGEEmbeddingProvider` | `embed_text()`, `embed_documents()` | `kiki_settings.EMBEDDING_MODEL=bge-large-en-v1.5` | Model load exception | [EMBEDDING PROVIDER] |
| **Vector Provider** | `core/kiki/rag/providers/chroma_provider.py` | `ChromaVectorStoreProvider` | `query_vectors()`, `add_vectors()` | `kiki_settings.CHROMADB_PERSIST_DIRECTORY` | Dimension mismatch → recreate | [CHROMA PROVIDER] |
| **BM25 Sparse Engine** | `core/kiki/rag/pipeline/sparse_engine.py` | `BM25SparseEngine` | `search_sparse()`, `index_chunks()` | `storage_dir=core/data/bm25` | Load failure → empty results | [BM25 ENGINE] |
| **RRF Fusion** | `core/kiki/rag/pipeline/fusion_engine.py` | `RRFFusionEngine` | `fuse_results()` | k=60 (standard RRF constant) | Graceful merge | [RRF] |
| **Reranker** | `core/kiki/rag/providers/reranker_provider.py` | `LocalRerankerProvider` | `rerank()` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Passthrough on error | [RERANKER PROVIDER] |
| **Evidence Builder** | `core/kiki/rag/pipeline/evidence_builder.py` | `EvidenceBuilder` | `build_evidence()` | Confidence threshold | Low confidence → empty evidence | [EVIDENCE BUILDER] |
| **Evidence Aggregator** | `core/kiki/evidence/aggregator.py` | `EvidenceAggregator` | `aggregate()` | ExecutionPolicy.EXCLUSIVE | No evidence → grounded refusal | [AGGREGATOR 16.1] |
| **Context Compressor** | `core/kiki/rag/pipeline/compressor_engine.py` | `ContextCompressorEngine` | `compress_chunks()` | Token budget=2584 | Bypass if under budget | [CONTEXT COMPRESSOR] |
| **Ollama Client** | `core/kiki/runtime/ollama_client.py` | `OllamaClient` | `generate()` | `OLLAMA_BASE_URL=http://localhost:11434` | Timeout exception | runtime logs |
| **Citation Builder** | `core/kiki/rag/citations.py` | `CitationBuilder` | `build_citations()` | Metadata from chunks | Fallback empty citations | citation logs |
| **Tenant Guard** | `core/kiki/security/tenant_guard.py` | `TenantGuard` | `extract_context()` | Django user object | Anon → default_tenant | security logs |
| **Vector Probe** | `core/kiki/rag/vector_store.py` | `ChromaVectorStore` | `probe_vector()` | BGE 1024-dim embed then query | Exception → is_candidate=False | [CHROMA] |
| **Document Loader** | `core/kiki/rag/loader.py` | `DocumentLoader` | `load_document()` | SUPPORTED_EXTENSIONS list | Unsupported → ValueError | loader logs |
| **Chunker** | `core/kiki/rag/chunker.py` | `SemanticChunker` | `chunk_document()` | Paragraph-based semantic split | Empty doc → empty chunks | chunker logs |
| **Knowledge Indexer** | `core/kiki/rag/knowledge_indexer.py` | `KnowledgeIndexer` | `index_all()` | `core/kiki/knowledge/` directory | Per-file exception isolation | [KNOWLEDGE INDEXER] |
| **Reindex Manager** | `core/kiki/rag/reindex_manager.py` | `RAGReindexManager` | `promote_index()` | RAGActiveIndex model (DB) | Rollback on failure | [REINDEX MANAGER] |

---

## 3. Ingestion Path

```
DocumentLoader.load_document()    [loader.py]
    ↓ raw text, page count
TextCleaner.clean_text()          [ingestion/cleaner.py]
    ↓ cleaned text
StructureExtractor.extract()      [ingestion/structure.py]
    ↓ sections, headings
SemanticChunker.chunk_document()  [chunker.py]
    ↓ raw_chunks (list of dicts)
MetadataGenerator.generate()      [ingestion/metadata.py]
    ↓ chunk + metadata
ChunkValidator.validate_chunks()  [ingestion/validator.py]
    ↓ validated_chunks (final)
BGEEmbeddingProvider.embed_documents()   → 1024-dim vectors
ChromaVectorStoreProvider.add_vectors()  → finpixe_global_knowledge + kiki_knowledge_documents
BM25SparseEngine.index_chunks()          → core/data/bm25/bm25_index.pkl
```

---

## 4. Configuration Summary

| Setting | Value | Source |
|---------|-------|--------|
| EMBEDDING_MODEL | `bge-large-en-v1.5` | kiki_settings |
| EMBEDDING_PROVIDER | `bge_local` | kiki_settings |
| EMBEDDING_DISTANCE_METRIC | `cosine` | kiki_settings |
| EMBEDDING_NORMALIZED | `True` | kiki_settings |
| VECTOR_PROVIDER | `chromadb` | kiki_settings |
| LLM_PROVIDER | `ollama` | kiki_settings |
| REASONING_MODEL | `llama3:latest` | kiki_settings |
| ROUTER_MODEL | `llama3:latest` | kiki_settings |
| OLLAMA_BASE_URL | `http://localhost:11434` | kiki_settings |
| KNOWLEDGE_ROUTING_THRESHOLD | `0.5` | kiki_settings |
| CHROMADB_PERSIST_DIRECTORY | `data/chromadb` | kiki_settings |
| REASONING_TIMEOUT_SECONDS | `60` | kiki_settings |
| ROUTER_TIMEOUT_SECONDS | `30` | kiki_settings |

---

## 5. Active Collections & Index Provenance

| Collection Name | Count | Provenance Status | Notes |
|----------------|-------|-------------------|-------|
| `kiki_knowledge_documents` | 564 | ⚠️ LEGACY_PROVENANCE_INCOMPLETE | No embedding_model, dimension, or corpus_hash in metadata |
| `finpixe_global_knowledge` | 109 | ⚠️ PARTIAL — no corpus_hash, embedding_dimension | Has description only |
| `forensic_phase17_3_collection` | 85 | ⚠️ LEGACY_PROVENANCE_INCOMPLETE | Forensic test collection |
| `idx_1786343063_0c943269` | 64 | ✅ FULL PROVENANCE | embedding_model, dimension, distance_metric, created_at |
| `idx_1786342895_36e015c6` | 0 | ⚠️ EMPTY — candidate index | Empty collection, not promoted |
| `forensic_security_test` | 2 | ⚠️ LEGACY_PROVENANCE_INCOMPLETE | Security test collection |
| `forensic_inventory_test` | 850 | ⚠️ LEGACY_PROVENANCE_INCOMPLETE | Phase 17.1 forensic collection |

### Index Provenance Finding

> **CRITICAL FINDING:** The **production collection `kiki_knowledge_documents` (564 chunks)** does **NOT** contain provenance metadata (embedding_model, dimension, corpus_hash, index_version). This means it is **impossible to verify** what embedding model was used to generate the stored vectors, whether dimension matches the active BGE 1024-dim model, or when it was indexed. This is classified as:
>
> **LEGACY_PROVENANCE_INCOMPLETE — REQUIRE REBUILD WITH FULL PROVENANCE**

---

## 6. Potential Hardcodes Identified

| Location | Hardcode | Classification |
|----------|----------|----------------|
| `knowledge_indexer.py:106` | `tenant_id="global"` | CONFIGURATION — global knowledge is legitimately "global" |
| `knowledge_indexer.py:108` | `security_level="Public"` | CONFIGURATION — global knowledge is public |
| `knowledge_indexer.py:124` | `version="2025.1"` | ⚠️ CONFIGURATION HARDCODE — should come from settings |
| `vector_store.py:69` | `"finpixe_global_knowledge"` | CONFIGURATION — collection name should be in settings |
| `vector_store.py:107` | `"finpixe_global_knowledge"` | CONFIGURATION — duplicate, should be a constant |
| `knowledge_indexer.py:20` | `GLOBAL_COLLECTION_NAME = "finpixe_global_knowledge"` | CONFIGURATION — module constant, acceptable |

---

## 7. Failure Handling Summary

| Failure Mode | Detected Handling | Assessment |
|--------------|------------------|------------|
| Chroma unavailable | Exception propagates to kernel → fallback reply | PASS |
| BM25 unavailable | search_sparse returns [] → RRF uses dense only | PASS |
| Embedding unavailable | Exception → HTTP 503 | PASS |
| Reranker unavailable | Results passthrough (no reranking) | PASS |
| Ollama unavailable | Timeout → KikiModelTimeoutException | PASS |
| Invalid embedding dim | Dimension mismatch detection + collection recreate | PASS |
| Wrong tenant | TenantGuard enforces server-side | PASS |

---

## 8. Test Coverage Gaps

- No automated unit tests for BM25SparseEngine.search_sparse()
- No automated integration test for RRF fusion correctness
- No automated test for reranker warm vs cold start distinction
- No automated security isolation test in CI
- No automated provenance validation at index time

---

*Report generated by KIKI Phase 17.3 Forensic Audit — 2026-08-10*
