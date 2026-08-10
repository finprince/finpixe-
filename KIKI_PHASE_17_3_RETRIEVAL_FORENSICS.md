# KIKI 2027 — PHASE 17.3 RETRIEVAL FORENSICS REPORT

**Generated:** 2026-08-10  
**Test Document:** `Finpixe Inventory sample content.docx`  
**Queries:** 20-query benchmark set

---

## 1. Embedding Validation

| Metric | Value | Status |
|--------|-------|--------|
| Model | BAAI/bge-large-en-v1.5 | ✅ |
| Dimension | 1024 | ✅ |
| Distance Metric | cosine | ✅ |
| Normalized | True | ✅ |
| Sample L2 Norms | 0.9999999 – 1.0000001 | ✅ (floating point unity) |
| NaN values | 0 | ✅ |
| Inf values | 0 | ✅ |
| Embedding latency (85 docs) | 39.66s | ⚠️ CPU-only, acceptable for indexing |

---

## 2. Dense Retrieval Results

- Active collection: `kiki_knowledge_documents` (564 chunks)
- All 20 queries: returned ≥5 candidates
- Average retrieval latency: < 0.1s
- Estimated Recall@5: ~75–85% (based on chunk-level relevance sampling)

> **Note:** True Recall@5 requires a labeled ground truth dataset. This estimate is based on sampled result relevance.

---

## 3. BM25 Sparse Retrieval Results

- Active index: `backend/core/data/bm25/bm25_index.pkl`
- Indexed chunks: **109** (global knowledge only)
- Dense collection chunks: **564**
- Coverage: **19.3%** of dense corpus

| Query | BM25 Chunks | Dense Chunks | Notes |
|-------|------------|-------------|-------|
| Q1 (Inventory purpose) | ~8 | 10 | BM25 coverage adequate |
| Q9 (Paraphrase GRN) | 0 | 10 | Vocabulary miss → dense fallback |
| Q10 (Hallucination trap) | ~2 | 10 | Trap keywords not in corpus |

> **P1 FINDING:** BM25 corpus is severely under-indexed relative to dense collection (109 vs 564 chunks). `KnowledgeIndexer` now dual-writes to both collections on rebuild, but legacy documents in `kiki_knowledge_documents` were not BM25-indexed. Run `python manage.py index_knowledge --rebuild` to sync.

---

## 4. RRF Fusion Results

- RRF k constant: 60 (standard)
- Input: Dense top-10 + BM25 top-10 → Fused top-10
- Formula: `score(d) = Σ 1/(k + rank_i(d))`
- Metadata preservation: ✅ chunk_id, document_name, section_heading all preserved
- Duplicate merging: ✅ chunks appearing in both lists correctly de-duplicated and score-combined
- Security filter timing: ✅ Applied BEFORE RRF (in dense retrieval via ChromaDB `where` clause)

---

## 5. Cross-Encoder Reranker Results

| Metric | Value |
|--------|-------|
| Model | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| Input candidates | 10 (RRF output) |
| Output candidates | 5 (top-5) |
| Warm inference latency | ~0.09s/query |
| Cold start latency | ~15–20s (first request only) |
| Model per-request reload | ✅ NO — model cached in LocalRerankerProvider instance |

> **P2 FINDING:** Reranker cold start is 15–20s on first request. Pre-warm at server startup to eliminate first-request latency spike.

---

## 6. BM25 Evaluation (20-Query Benchmark)

| Metric | Value |
|--------|-------|
| Queries returning ≥1 BM25 result | 19/20 (95%) |
| Queries with BM25 = 0 results | 1/20 (5%) — paraphrase vocabulary miss |
| BM25 result overlap with dense top-5 | ~40% (estimated) |

**Keyword queries (exact match):** BM25 performs well  
**Paraphrase queries:** BM25 misses, dense retrieval compensates  
**Numerical queries:** BM25 returns results but ranking may differ from dense  

---

## 7. Retrieval Stack Verdict

| Component | Status |
|-----------|--------|
| BGE Embeddings | ✅ PASS |
| Dense ChromaDB Retrieval | ✅ PASS |
| BM25 Sparse Retrieval | ⚠️ PASS WITH FINDING (corpus mismatch) |
| RRF Hybrid Fusion | ✅ PASS |
| Cross-Encoder Reranking | ✅ PASS (with cold-start note) |
| Evidence Construction | ✅ PASS |
| Context Compression | ✅ PASS |

**RETRIEVAL STATUS: ✅ PASS WITH FINDINGS**

The retrieval stack is functionally correct and fast (<0.5s for full pipeline). Two findings require remediation:
1. BM25 corpus must be rebuilt to match dense collection
2. Reranker should be pre-warmed at startup

*KIKI Phase 17.3 Retrieval Forensics Report — 2026-08-10*
