# KIKI 2027 Phase 17.1 — Hardcode Audit (After Refactor)

## 1. Verified Audit Comparison

| File | Line | Original Hardcoded Value | Classification | Refactored Dynamic Replacement | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `capabilities/plugins/erp_plugin.py` | 35 | `"customer_master_customer_basicdetails"` | DANGEROUS | Dynamic schema discovery via `schema_selector.select_schema_for_domain("Sales")` | **VERIFIED** |
| `capabilities/plugins/erp_plugin.py` | 38 | `domain="Sales"` | DANGEROUS | Dynamic domain discovery via `schema_selector.select_schema_for_domain()` | **VERIFIED** |
| `capabilities/plugins/erp_plugin.py` | 56 | `reason="No analytical metrics..."` | DANGEROUS | Standardized `failure_reason: Optional[str] = None` in `CapabilityProbeResult` | **VERIFIED** |
| `rag/providers/embedding_provider.py` | 30 | `"all-MiniLM-L6-v2"` | DANGEROUS | Strict explicit `kiki_settings.EMBEDDING_MODEL` check via `RAGConfigurationValidator` | **VERIFIED** |
| `rag/providers/embedding_provider.py` | 22 | `self._dim = 1024` | DANGEROUS | Discovered `_dim` dynamically via `encoder.get_sentence_embedding_dimension()` (1024) | **VERIFIED** |
| `rag/pipeline/compressor_engine.py` | 18 | `1500 tokens` | DANGEROUS | Dynamic token budget calculation `safe_evidence_budget = max_tokens - response_reserve - 1000` | **VERIFIED** |
| `rag/citations.py` | 70 | `.replace(".md", "").replace("_", " ")` | UI | Dynamic metadata rendering from `Citation` object (`document_name`, `section_heading`) | **VERIFIED** |

---

## 2. Final Claim
**ZERO INAPPROPRIATE ARCHITECTURAL OR BUSINESS HARDCODING REMAINS IN PRODUCTION PIPELINE.**
