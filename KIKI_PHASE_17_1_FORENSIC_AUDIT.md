# KIKI 2027 Phase 17.1 — Forensic Audit Document

## 1. Executive Summary
This forensic audit documents all identified implementation defects, contract mismatches, and architectural hardcoding across the KIKI 2027 codebase.

---

## 2. Classified Audit Findings

| ID | Component | Finding Description | Severity | Target File |
| :--- | :--- | :--- | :--- | :--- |
| **AUD-01** | Embedding Provider | `BGEEmbeddingProvider._get_encoder()` hardcoded `SentenceTransformer("all-MiniLM-L6-v2")` inside line 30 despite reading `EMBEDDING_MODEL` setting (`bge-large-en-v1.5`). | **P0** | `backend/core/kiki/rag/providers/embedding_provider.py` |
| **AUD-02** | Vector Store Provider | `ChromaVectorStoreProvider` lacked index dimension and provenance metadata validation during startup and vector search. | **P0** | `backend/core/kiki/rag/providers/chroma_provider.py` |
| **AUD-03** | Capability Contract | `CapabilityProbeResult` dataclass lacked `failure_reason: Optional[str] = None`. `erp_plugin.py` passed `reason="..."`, raising `TypeError`. | **P0** | `backend/core/kiki/capabilities/base.py`, `plugins/erp_plugin.py` |
| **AUD-04** | Startup Lifecycle | Models (`SentenceTransformer`, `CrossEncoder`) were lazy-loaded during user HTTP query requests instead of preloading during app initialization. | **P0** | `backend/core/apps.py` |
| **AUD-05** | ERP Capability Probe | `ERPAnalyticsCapability.probe()` hardcoded `target_table = "customer_master_customer_basicdetails"` and `domain = "Sales"`. | **P0** | `backend/core/kiki/capabilities/plugins/erp_plugin.py` |
| **AUD-06** | Context Compressor | `ContextCompressorEngine` stripped non-query-word sentences, causing complementary multi-chunk factual context loss. | **P0** | `backend/core/kiki/rag/pipeline/compressor_engine.py` |
| **AUD-07** | Frontend UI | `KikiPanel.tsx` rendered raw sub-card `msg.evidence_package` which displayed internal summary logs (`[KNOWLEDGE from ...]`). | **P1** | `frontend/src/components/kiki/KikiPanel.tsx` |
| **AUD-08** | Configuration Defaults | Missing explicit settings validator `RAGConfigurationValidator` to enforce configuration presence. | **P1** | `backend/core/kiki/rag/config_validator.py` |
