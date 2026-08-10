# KIKI 2027 — PHASE 17.3 HARDCODE AUDIT

**Generated:** 2026-08-10  
**Method:** Static code analysis via ripgrep across entire `backend/core/kiki/` tree  
**Scope:** Business domain routing, collection names, model names, tenant IDs, embedding dimensions

---

## Audit Results

| # | Pattern Found | File | Line | Classification | Risk | Action |
|---|--------------|------|------|---------------|------|--------|
| 1 | `tenant_id="global"` | `rag/knowledge_indexer.py:106` | 106 | CONFIGURATION — global knowledge is legitimately served to all tenants | LOW | None — correct |
| 2 | `security_level="Public"` | `rag/knowledge_indexer.py:108` | 108 | CONFIGURATION — global documents are public knowledge | LOW | None — correct |
| 3 | `version="2025.1"` | `rag/knowledge_indexer.py:124` | 124 | ⚠️ CONFIG HARDCODE — chunk schema version embedded in code | MEDIUM | Move to `kiki_settings.SCHEMA_VERSION` |
| 4 | `"finpixe_global_knowledge"` | `rag/vector_store.py:69` | 69 | CONFIGURATION — collection name should be a settings constant | LOW | Move to `kiki_settings.GLOBAL_COLLECTION_NAME` |
| 5 | `"finpixe_global_knowledge"` | `rag/vector_store.py:107` | 107 | CONFIGURATION — duplicate of above | LOW | Use same settings constant |
| 6 | `GLOBAL_COLLECTION_NAME = "finpixe_global_knowledge"` | `rag/knowledge_indexer.py:20` | 20 | CONFIGURATION MODULE CONSTANT — acceptable | LOW | Could also come from settings |
| 7 | `Priority: 90` | `capabilities/knowledge_retrieval.py` | — | LEGITIMATE ENUM — plugin priority ordering | LOW | None |
| 8 | `Priority: 85` | `capabilities/workflow_automation.py` | — | LEGITIMATE ENUM | LOW | None |
| 9 | `Priority: 80` | `capabilities/erp_analytics.py` | — | LEGITIMATE ENUM | LOW | None |
| 10 | `Priority: 70` | `capabilities/navigation.py` | — | LEGITIMATE ENUM | LOW | None |
| 11 | `k1=1.5, b=0.75` | `rag/pipeline/sparse_engine.py` | — | ALGORITHM CONSTANTS — standard BM25 defaults | LOW | None — documented defaults |
| 12 | `n_results=10` | `rag/execution_pipeline.py` | — | CONFIGURATION — top-K retrieval count | LOW | Move to `kiki_settings.RAG_TOP_K` |
| 13 | `top_k=5` | `rag/providers/reranker_provider.py` | — | CONFIGURATION — reranker output count | LOW | Move to `kiki_settings.RERANKER_TOP_K` |
| 14 | `2584` (token budget) | `rag/pipeline/compressor_engine.py` | — | CONFIGURATION — context token budget | LOW | Move to `kiki_settings.CONTEXT_TOKEN_BUDGET` |
| 15 | `"Sales"` | `capabilities/erp_analytics.py` | — | DOCUMENT CONTENT / ENUM — ERP domain classification | LOW | Acceptable — ERP module name |
| 16 | `"Purchase"` | `capabilities/erp_analytics.py` | — | DOCUMENT CONTENT / ENUM | LOW | Acceptable |
| 17 | `"Inventory"` | `capabilities/erp_analytics.py` | — | DOCUMENT CONTENT / ENUM | LOW | Acceptable |
| 18 | `"GST"` | `capabilities/erp_analytics.py` | — | DOCUMENT CONTENT / ENUM | LOW | Acceptable |
| 19 | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `rag/providers/reranker_provider.py` | — | CONFIGURATION — reranker model name | LOW | Move to `kiki_settings.RERANKER_MODEL` |
| 20 | `1024` | `rag/vector_store.py` | — | CONFIGURATION — expected embedding dimension | LOW | Should come from `bge_embedding_provider.dimension` |

---

## Domain Routing Hardcode Search

Searched for: Sales, Purchase, Inventory, GST, Invoice, Customer, Vendor in decision paths (planner, kernel, capabilities, routing).

**Result:** All occurrences of business domain terms in decision paths are:
- ERP module ENUM values used for capability matching (not routing by string comparison)
- Document content labels in knowledge categories
- Configuration constants, not routing logic

**No `if domain == "Sales"` or `if keyword in ["Invoice", "GST"]` pattern routing found in any decision path.**

---

## Conclusion

> **"No inappropriate business-domain routing hardcodes were identified in the audited decision paths."**

The evidence fully supports this conclusion. All business domain terms found are either:
- Legitimate configuration constants
- ERP module enumeration values
- Document content classification labels

There are **no keyword-matching routing switches** that would inappropriately steer queries based on hardcoded business vocabulary.

**Minor items to clean up (P2):**
- `version="2025.1"` → move to settings
- `"finpixe_global_knowledge"` string literals → consolidate to one settings constant
- `n_results=10`, `top_k=5`, `2584` token budget → move to settings for configurability
- `cross-encoder/ms-marco-MiniLM-L-6-v2` → add `RERANKER_MODEL` to kiki_settings

---

*KIKI Phase 17.3 Hardcode Audit — 2026-08-10*
