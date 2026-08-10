# KIKI 2027 Phase 17.1 — Hardcode Audit (Before Refactor)

## Classified Hardcode Occurrences

| File | Line | Hardcoded Value | Classification | Problem | Replacement Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `capabilities/plugins/erp_plugin.py` | 35 | `"customer_master_customer_basicdetails"` | DANGEROUS | Fixed table target in probe | Dynamic schema discovery via `schema_selector.select_schema_for_domain()` |
| `capabilities/plugins/erp_plugin.py` | 38 | `domain="Sales"` | DANGEROUS | Hardcoded domain assumption | Dynamic schema domain discovery |
| `capabilities/plugins/erp_plugin.py` | 56 | `reason="No analytical metrics..."` | DANGEROUS | Passed non-existent kwarg `reason=` | Standardize `failure_reason: Optional[str] = None` in `CapabilityProbeResult` |
| `rag/providers/embedding_provider.py` | 30 | `"all-MiniLM-L6-v2"` | DANGEROUS | Hardcoded MiniLM string fallback | Strict explicit `kiki_settings.EMBEDDING_MODEL` check with `RAGConfigurationValidator` |
| `rag/providers/embedding_provider.py` | 22 | `self._dim = 1024` | DANGEROUS | Static dimension assumption | Discover `_dim` dynamically via `encoder.get_sentence_embedding_dimension()` |
| `rag/pipeline/compressor_engine.py` | 18 | `1500 tokens` | DANGEROUS | Fixed token limit threshold | Calculate `safe_evidence_budget` dynamically based on model context limit |
| `rag/citations.py` | 70 | `.replace(".md", "").replace("_", " ")` | UI | Basic text cleaning | Dynamic metadata rendering from `Citation` object |
