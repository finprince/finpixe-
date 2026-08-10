# KIKI 2027 — PHASE 17.3 CONTRADICTION MATRIX

**Generated:** 2026-08-10  
**Scope:** Comparison of Phase 17.1 + 17.2 claims vs Phase 17.3 empirical evidence

---

| # | Area | Phase 17.1/17.2 Claim | Phase 17.3 Evidence | Contradiction? | Severity | Root Cause | Required Fix | Verification Method |
|---|------|-----------------------|--------------------|----------------|---------|-----------|-------------|-------------------|
| 1 | **Page Metadata** | Citations reference "Page 1, Section X" implying source-derived page numbers | DOCX loader does NOT perform physical page rendering. All chunks carry `page_number=1` regardless of actual page | ✅ YES — DOCX has no page API | **HIGH** | DOCX python-docx library does not expose physical page boundaries. Page=1 is a fallback assignment. | Change citation format to `PAGE_METADATA_UNAVAILABLE` or section-level only | Run DOCX through LibreOffice PDF export and verify page mapping |
| 2 | **E2E QPS** | Phase 17.2 reported "RAG Search QPS" — never measured actual KIKI E2E QPS | Phase 17.3 measured real E2E: 0.04 QPS at 1 user (22.8s P50) | ✅ YES — Prior reports conflated retrieval QPS with E2E QPS | **CRITICAL** | Phase 17.2 tested RAG in isolation, not the full HTTP → NLU → LLM path | Report E2E QPS separately from retrieval QPS | Measure full HTTP path with concurrent users |
| 3 | **BM25/Dense Corpus Sync** | Phase 17.1/17.2 assumed BM25 and Dense operate on same corpus | BM25 index: 109 chunks. Dense `kiki_knowledge_documents`: 564 chunks. Corpus mismatch of 455 chunks (81%) | ✅ YES — NOT SYNCED | **HIGH** | KnowledgeIndexer was not always dual-writing to both stores. Legacy documents in Dense were not BM25-indexed | Rebuild BM25 from full Dense corpus | Count BM25 chunks == ChromaDB collection count |
| 4 | **Index Provenance** | Phase 17.2 declared "index provenance complete" | `kiki_knowledge_documents` (564 chunks, production collection) has NO provenance metadata | ✅ YES — INCOMPLETE | **HIGH** | Production collection was created directly, not via RAGReindexManager provenance path | Rebuild collection via RAGReindexManager with full provenance | Check collection.metadata for all required fields |
| 5 | **Reranker Cold Start** | Phase 17.1 stated reranker is "warm" — no cold start characterization | First request cold start: 15–20s for model download/load. Subsequent: ~0.09s | ✅ YES — Cold start uncharacterized | **MEDIUM** | Reranker loaded lazily on first request, not pre-warmed at startup | Pre-warm LocalRerankerProvider at Django `AppConfig.ready()` | Time first vs second reranker call |
| 6 | **Security Isolation** | Phase 17.2 claimed "security PASS" from limited testing | Phase 17.3 ran 12 adversarial multi-tenant tests — 12/12 PASSED | ❌ NO CONTRADICTION — confirmed stronger | **LOW** | — | — | Additional adversarial testing with injected tenant_id headers |
| 7 | **Ollama as Bottleneck** | Phase 17.2 listed "Ollama latency" as a warning but did not quantify | Measured: 22.8s P50 at 1 user; 133s P50 at 50 users; 0.04–0.37 QPS | Phases underestimated severity | **CRITICAL** | Ollama llama3 on CPU is extremely slow for real-time multi-user serving | GPU deployment mandatory | Measure Ollama tokens/sec with nvidia-smi |
| 8 | **Hybrid Retrieval Improvement** | Phase 17.1 claimed "hybrid improves recall" | With BM25 at 19% of dense corpus, hybrid benefit is severely limited. BM25 returned 0 results on 1 of 20 queries | ✅ PARTIAL — claim overstated | **MEDIUM** | BM25 only indexed global knowledge (109 chunks), not all documents in Dense | Sync BM25 to full dense corpus | Measure Recall@5 for dense-only vs hybrid on same query set |
| 9 | **GPU Status** | Phase 17.1/17.2 mentioned GPU as "future optimization" | GPU_TEST_UNAVAILABLE — no GPU on test system | Not a contradiction — correctly deferred | **LOW** | No GPU hardware | Deploy on GPU instance | Measure with nvidia-smi during Ollama inference |
| 10 | **Embedding Model Identity** | Phase 17.1 claimed "bge-large-en-v1.5" vs "BAAI/bge-large-en-v1.5" as potential mismatch | Phase 17.3 confirmed: cosmetic string difference only. Same model resolves correctly from HuggingFace | ❌ NO CONTRADICTION — Phase 17.1 was overly cautious | **LOW** | Settings use short name `bge-large-en-v1.5` → resolves to `BAAI/bge-large-en-v1.5` | None required — cosmetic only | Verify model card URL matches |

---

## Summary

| Severity | Count | Areas |
|---------|-------|-------|
| CRITICAL | 2 | E2E QPS measurement gap, Ollama bottleneck severity |
| HIGH | 3 | Page metadata fiction, BM25/Dense corpus mismatch, index provenance gap |
| MEDIUM | 2 | Reranker cold start uncharacterized, hybrid recall overstatement |
| LOW | 3 | Security (confirmed stronger), GPU (correctly deferred), model ID cosmetic |

---

*KIKI Phase 17.3 Contradiction Matrix — 2026-08-10*
