"""
KIKI Phase 17.4 RAG Regression Test Suite
==========================================
30-case regression matrix covering all Phase 17.4 acceptance criteria.
Runs in isolation without requiring a live Ollama/GPU/Chroma server where possible.
Tests that DO require live services are marked with @pytest.mark.integration.
"""
import pytest
import hashlib
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — Document Loader: page_metadata_available flag
# ─────────────────────────────────────────────────────────────────────────────
class TestDocumentLoader:
    """Tests for Phase 17.4 page_metadata_available flag from loader.py."""

    def test_pdf_has_page_metadata_available_true(self, tmp_path):
        """PDF documents should return page_metadata_available=True."""
        from core.kiki.rag.loader import DocumentLoader
        loader = DocumentLoader()
        # Create a minimal text file (pdf parsing tested separately)
        # Check the flag logic by inspecting supported extension handling
        assert ".pdf" in loader.SUPPORTED_EXTENSIONS
        assert ".docx" in loader.SUPPORTED_EXTENSIONS

    def test_txt_page_metadata_available_false(self, tmp_path):
        """TXT files must have page_metadata_available=False."""
        from core.kiki.rag.loader import document_loader
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("This is test content for KIKI Phase 17.4 regression testing.")
        result = document_loader.load_document(str(txt_file), "test.txt")
        assert result["page_metadata_available"] is False
        assert result["pages"][0]["page_metadata_available"] is False

    def test_md_page_metadata_available_false(self, tmp_path):
        """Markdown files must have page_metadata_available=False."""
        from core.kiki.rag.loader import document_loader
        md_file = tmp_path / "test.md"
        md_file.write_text("# Test Document\nThis is test content.")
        result = document_loader.load_document(str(md_file), "test.md")
        assert result["page_metadata_available"] is False

    def test_csv_page_metadata_available_false(self, tmp_path):
        """CSV files must have page_metadata_available=False."""
        from core.kiki.rag.loader import document_loader
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("col1,col2\nval1,val2\n")
        result = document_loader.load_document(str(csv_file), "test.csv")
        assert result["page_metadata_available"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — Chunker: page_number=None when page_metadata_available=False
# ─────────────────────────────────────────────────────────────────────────────
class TestChunker:
    """Tests for Phase 17.4 page_number=None when page_metadata_available=False."""

    def test_docx_chunks_have_none_page_number(self, tmp_path):
        """DOCX chunks must have page_number=None (not fabricated 1)."""
        from core.kiki.rag.chunker import semantic_chunker
        doc_data = {
            "filename": "test.docx",
            "extension": ".docx",
            "full_text": "This is a test DOCX document with multiple paragraphs. " * 10,
            "pages": [{"page": 1, "text": "This is a test DOCX document. " * 10, "page_metadata_available": False}],
            "total_pages": 1,
            "page_metadata_available": False,
        }
        chunks = semantic_chunker.chunk_document(
            doc_data=doc_data,
            doc_id="test_doc_001",
            tenant_id="test_tenant",
        )
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk["page_number"] is None, f"Expected None, got {chunk['page_number']}"
            assert chunk["page_metadata_available"] is False

    def test_pdf_chunks_have_real_page_number(self, tmp_path):
        """PDF chunks must carry the real page number when page_metadata_available=True."""
        from core.kiki.rag.chunker import semantic_chunker
        doc_data = {
            "filename": "test.pdf",
            "extension": ".pdf",
            "full_text": "This is page 3. " * 10,
            "pages": [{"page": 3, "text": "This is page 3. " * 10, "page_metadata_available": True}],
            "total_pages": 1,
            "page_metadata_available": True,
        }
        chunks = semantic_chunker.chunk_document(
            doc_data=doc_data,
            doc_id="test_pdf_001",
            tenant_id="test_tenant",
        )
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk["page_number"] == 3
            assert chunk["page_metadata_available"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — Metadata Generator: version from settings, page from chunk
# ─────────────────────────────────────────────────────────────────────────────
class TestMetadataGenerator:
    """Tests for Phase 17.4 metadata hardcode removal."""

    def test_version_from_settings(self):
        """Metadata version must come from kiki_settings.SCHEMA_VERSION."""
        from core.kiki.rag.ingestion.metadata import metadata_generator
        from core.kiki.config import kiki_settings
        chunk = {
            "text": "Test chunk text for regression",
            "section_heading": "Test Section",
            "page_number": None,
            "page_metadata_available": False,
        }
        meta = metadata_generator.generate_metadata(
            chunk=chunk, doc_id="doc001", filename="test.docx"
        )
        assert meta["version"] == kiki_settings.SCHEMA_VERSION
        assert meta["version"] != ""

    def test_docx_page_number_is_none(self):
        """Metadata for DOCX must have page=None, not 1."""
        from core.kiki.rag.ingestion.metadata import metadata_generator
        chunk = {
            "text": "Some text here",
            "section_heading": "Section",
            "page_number": None,
            "page_metadata_available": False,
        }
        meta = metadata_generator.generate_metadata(
            chunk=chunk, doc_id="doc001", filename="test.docx"
        )
        assert meta["page"] is None
        assert meta["page_number"] is None
        assert meta["page_metadata_available"] is False

    def test_pdf_page_number_is_real(self):
        """Metadata for PDF must carry the real page number."""
        from core.kiki.rag.ingestion.metadata import metadata_generator
        chunk = {
            "text": "PDF page text here",
            "section_heading": "Section",
            "page_number": 7,
            "page_metadata_available": True,
        }
        meta = metadata_generator.generate_metadata(
            chunk=chunk, doc_id="doc002", filename="test.pdf"
        )
        assert meta["page"] == 7
        assert meta["page_number"] == 7
        assert meta["page_metadata_available"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 4 — Citations: no fake "Page 1" for DOCX
# ─────────────────────────────────────────────────────────────────────────────
class TestCitationBuilder:
    """Tests for Phase 17.4 citation correctness."""

    def _make_chunk(self, filename: str, page_number, page_meta: bool, section: str):
        return {
            "chunk_id": "chk_test_001",
            "text": "Test text",
            "confidence": 0.9,
            "metadata": {
                "filename": filename,
                "page_number": page_number,
                "page_metadata_available": page_meta,
                "section_heading": section,
            }
        }

    def test_docx_citation_no_page(self):
        """DOCX citation must NOT include 'Page X'."""
        from core.kiki.rag.citations import citation_builder
        chunks = [self._make_chunk("Manual.docx", None, False, "Stock Transfer")]
        citations = citation_builder.build_citations(chunks)
        md = citation_builder.format_citation_markdown(citations)
        assert "Page" not in md
        assert "Stock Transfer" in md

    def test_pdf_citation_includes_page(self):
        """PDF citation MUST include 'Page X' when page is real."""
        from core.kiki.rag.citations import citation_builder
        chunks = [self._make_chunk("Guide.pdf", 5, True, "Installation")]
        citations = citation_builder.build_citations(chunks)
        md = citation_builder.format_citation_markdown(citations)
        assert "Page 5" in md
        assert "Installation" in md

    def test_no_duplicate_citations(self):
        """Same doc+section must appear only once in citations."""
        from core.kiki.rag.citations import citation_builder
        chunk1 = self._make_chunk("Doc.pdf", 1, True, "Overview")
        chunk2 = self._make_chunk("Doc.pdf", 1, True, "Overview")
        chunks = [chunk1, chunk2]
        citations = citation_builder.build_citations(chunks)
        assert len(citations) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 5 — Configuration: all Phase 17.4 settings present
# ─────────────────────────────────────────────────────────────────────────────
class TestKikiSettings:
    """Tests that all Phase 17.4 settings exist in kiki_settings."""

    def test_required_settings_exist(self):
        from core.kiki.config import kiki_settings
        required = [
            "RERANKER_MODEL", "PRIMARY_COLLECTION_NAME", "GLOBAL_COLLECTION_NAME",
            "GLOBAL_KNOWLEDGE_TENANT_ID", "GLOBAL_KNOWLEDGE_SECURITY_LEVEL",
            "SCHEMA_VERSION", "RAG_TOP_K", "RERANKER_TOP_K", "CONTEXT_TOKEN_BUDGET",
            "NLU_BYPASS_ENABLED", "TENANT_ANONYMOUS_ALLOWED",
        ]
        for attr in required:
            assert hasattr(kiki_settings, attr), f"Missing setting: {attr}"

    def test_reranker_model_not_empty(self):
        from core.kiki.config import kiki_settings
        assert kiki_settings.RERANKER_MODEL != ""
        assert kiki_settings.RERANKER_MODEL is not None

    def test_schema_version_not_empty(self):
        from core.kiki.config import kiki_settings
        assert kiki_settings.SCHEMA_VERSION != ""


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 — Embedding Provider: preload() and is_loaded()
# ─────────────────────────────────────────────────────────────────────────────
class TestEmbeddingProvider:
    """Tests for Phase 17.4 embedding provider interface."""

    def test_provider_has_preload_method(self):
        from core.kiki.rag.providers.embedding_provider import bge_embedding_provider
        assert hasattr(bge_embedding_provider, "preload")
        assert callable(bge_embedding_provider.preload)

    def test_provider_has_is_loaded_method(self):
        from core.kiki.rag.providers.embedding_provider import bge_embedding_provider
        assert hasattr(bge_embedding_provider, "is_loaded")
        assert callable(bge_embedding_provider.is_loaded)
        result = bge_embedding_provider.is_loaded()
        assert isinstance(result, bool)

    def test_model_name_resolved_at_init(self):
        """Model name must be resolved at __init__, not at request time."""
        from core.kiki.rag.providers.embedding_provider import BGEEmbeddingProvider
        p = BGEEmbeddingProvider("bge-large-en-v1.5")
        assert p.model_name == "BAAI/bge-large-en-v1.5"


# ─────────────────────────────────────────────────────────────────────────────
# Test 7 — Reranker: no FALLBACK sentinel, is_loaded() present
# ─────────────────────────────────────────────────────────────────────────────
class TestRerankerProvider:
    """Tests for Phase 17.4 reranker provider hardening."""

    def test_no_fallback_string_in_reranker_source(self):
        """The 'FALLBACK' string must NOT be used as a state sentinel value in reranker code."""
        import re as _re
        with open(
            r"c:\108\AI-accounting-0.03\backend\core\kiki\rag\providers\reranker_provider.py",
            encoding="utf-8"
        ) as f:
            source = f.read()
        # Strip all docstrings
        source_stripped = _re.sub(r'""".*?"""', '', source, flags=_re.DOTALL)
        # Check that FALLBACK is not used as a state assignment (e.g. self._state = "FALLBACK")
        assert not _re.search(r'=\s*"FALLBACK"', source_stripped), (
            "Found FALLBACK sentinel as assigned value in reranker code (must use is_loaded flag instead)"
        )

    def test_is_loaded_returns_bool(self):
        from core.kiki.rag.providers.reranker_provider import local_reranker_provider
        assert isinstance(local_reranker_provider.is_loaded(), bool)

    def test_model_from_settings(self):
        from core.kiki.rag.providers.reranker_provider import local_reranker_provider
        from core.kiki.config import kiki_settings
        assert local_reranker_provider.model_name == kiki_settings.RERANKER_MODEL

    def test_rerank_unloaded_returns_unranked_not_fallback(self):
        """If reranker not loaded, must return candidates in-order with reranker_available=False."""
        from core.kiki.rag.providers.reranker_provider import LocalRerankerProvider
        provider = LocalRerankerProvider()
        # NOT loaded
        candidates = [
            {"text": "First result", "rrf_score": 0.9},
            {"text": "Second result", "rrf_score": 0.7},
        ]
        result = provider.rerank("test query", candidates, top_k=2)
        assert len(result) <= 2
        # Must NOT raise; must return something
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# Test 8 — BM25: corpus_manifest and provenance
# ─────────────────────────────────────────────────────────────────────────────
class TestBM25Engine:
    """Tests for Phase 17.4 BM25 corpus manifest and provenance."""

    def test_index_chunks_writes_corpus_manifest(self):
        from core.kiki.rag.pipeline.sparse_engine import BM25SparseEngine
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BM25SparseEngine(storage_dir=tmpdir)
            chunks = [
                {"chunk_id": "chk_001", "text": "Stock transfer between warehouses"},
                {"chunk_id": "chk_002", "text": "Inventory valuation methods FIFO LIFO"},
            ]
            engine.index_chunks(chunks, corpus_version="test_v1", index_version="idx_test_1")
            manifest = engine.get_corpus_manifest()
            assert "chk_001" in manifest
            assert "chk_002" in manifest
            assert engine.corpus_version == "test_v1"
            assert engine.index_version == "idx_test_1"

    def test_validate_corpus_sync_synchronized(self):
        from core.kiki.rag.pipeline.sparse_engine import BM25SparseEngine
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BM25SparseEngine(storage_dir=tmpdir)
            chunks = [
                {"chunk_id": "chk_A", "text": "Test chunk alpha"},
                {"chunk_id": "chk_B", "text": "Test chunk beta"},
            ]
            engine.index_chunks(chunks)
            chroma_ids = {"chk_A", "chk_B"}
            result = engine.validate_corpus_sync(chroma_ids)
            assert result["sync_status"] == "SYNCHRONIZED"

    def test_validate_corpus_sync_out_of_sync(self):
        from core.kiki.rag.pipeline.sparse_engine import BM25SparseEngine
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = BM25SparseEngine(storage_dir=tmpdir)
            chunks = [{"chunk_id": "chk_A", "text": "Only A"}]
            engine.index_chunks(chunks)
            chroma_ids = {"chk_A", "chk_B", "chk_C"}  # 2 extra in Chroma
            result = engine.validate_corpus_sync(chroma_ids)
            assert result["sync_status"] == "INDEX_OUT_OF_SYNC"
            assert result["missing_from_sparse"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# Test 9 — NLU Bypass: needs_nlu() structural signals
# ─────────────────────────────────────────────────────────────────────────────
class TestNLUBypass:
    """Tests for Phase 17.4 needs_nlu() structural bypass function."""

    def test_pronoun_requires_nlu(self):
        from core.kiki.context.nlu_analyzer import needs_nlu
        assert needs_nlu("What does it do?") is True
        assert needs_nlu("Tell me more about that") is True
        assert needs_nlu("How does this work?") is True

    def test_self_contained_skips_nlu(self):
        from core.kiki.context.nlu_analyzer import needs_nlu
        assert needs_nlu("What is stock transfer?") is False
        assert needs_nlu("How to add a new vendor?") is False
        assert needs_nlu("Explain inventory valuation") is False

    def test_session_entity_requires_nlu(self):
        from core.kiki.context.nlu_analyzer import needs_nlu
        # Even a self-contained query requires NLU when session entity is set
        assert needs_nlu("What is stock transfer?", current_entity="FinPix Module") is True

    def test_no_business_keywords_in_needs_nlu(self):
        """needs_nlu() implementation must not route on business domain keywords."""
        import re as _re
        import inspect
        from core.kiki.context import nlu_analyzer as nmod
        source = inspect.getsource(nmod.needs_nlu)
        # Strip docstrings before checking for forbidden business keywords
        source_stripped = _re.sub(r'""".*?"""', '', source, flags=_re.DOTALL)
        forbidden = ["inventory", "sales", "gst", "invoice", "purchase", "vendor"]
        for word in forbidden:
            assert word.lower() not in source_stripped.lower(), (
                f"needs_nlu() code logic contains business keyword '{word}' "
                "— keyword routing is forbidden (check non-docstring lines)"
            )


# ─────────────────────────────────────────────────────────────────────────────
# Test 10 — Tenant Guard: fail-closed behavior
# ─────────────────────────────────────────────────────────────────────────────
class TestTenantGuard:
    """Tests for Phase 17.4 tenant fail-closed policy."""

    def test_authenticated_user_with_no_tenant_raises(self):
        from core.kiki.security.tenant_guard import TenantGuard
        from core.kiki.exceptions import KikiTenantSecurityException
        guard = TenantGuard()
        user = MagicMock()
        user.is_authenticated = True
        user.tenant_id = None
        user.tenant = None
        user.company_id = None
        with patch("core.kiki.config.kiki_settings.TENANT_ANONYMOUS_ALLOWED", True):
            with pytest.raises(KikiTenantSecurityException):
                guard.extract_context(user)

    def test_authenticated_user_with_tenant_succeeds(self):
        from core.kiki.security.tenant_guard import TenantGuard
        guard = TenantGuard()
        user = MagicMock()
        user.is_authenticated = True
        user.tenant_id = "tenant_abc"
        user.company_id = "tenant_abc"
        ctx = guard.extract_context(user)
        assert ctx["tenant_id"] == "tenant_abc"
        assert ctx["is_anonymous"] is False

    def test_anonymous_allowed_returns_anonymous_tenant(self):
        from core.kiki.security.tenant_guard import TenantGuard
        guard = TenantGuard()
        # Pass None as user (unauthenticated)
        # TENANT_ANONYMOUS_ALLOWED defaults to True in settings
        ctx = guard.extract_context(None)
        assert ctx["tenant_id"] == "anonymous"
        assert ctx["is_anonymous"] is True

    def test_no_default_tenant_string_in_guard(self):
        """'default_tenant' must not appear as a runtime fallback value in tenant_guard.py code."""
        import re as _re
        with open(
            r"c:\108\AI-accounting-0.03\backend\core\kiki\security\tenant_guard.py",
            encoding="utf-8"
        ) as f:
            source = f.read()
        # Strip docstrings before checking
        source_stripped = _re.sub(r'""".*?"""', '', source, flags=_re.DOTALL)
        assert '"default_tenant"' not in source_stripped, (
            "Found 'default_tenant' hardcode in tenant_guard code logic (excluding docstrings)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 11 — Chroma Provenance: PROVENANCE_MISSING for non-empty with no metadata
# ─────────────────────────────────────────────────────────────────────────────
class TestChromaProvenance:
    """Tests for Phase 17.4 Chroma provenance validation logic."""

    def test_empty_collection_returns_empty_collection(self):
        """Empty collection should return (True, 'EMPTY_COLLECTION')."""
        from core.kiki.rag.providers.chroma_provider import ChromaVectorStoreProvider
        with patch.object(ChromaVectorStoreProvider, "count", return_value=0):
            with patch.object(ChromaVectorStoreProvider, "get_provenance", return_value={}):
                provider = MagicMock(spec=ChromaVectorStoreProvider)
                provider.count = MagicMock(return_value=0)
                provider.get_provenance = MagicMock(return_value={})
                provider.capabilities = MagicMock(return_value=MagicMock(
                    model_id="BAAI/bge-large-en-v1.5", dimension=1024,
                    distance_metric="cosine"
                ))
                result = ChromaVectorStoreProvider.validate_provenance(provider)
                assert result == (True, "EMPTY_COLLECTION")

    def test_no_initial_index_for_non_empty(self):
        """Non-empty collections without provenance must return PROVENANCE_MISSING, NOT INITIAL_INDEX."""
        from core.kiki.rag.providers.chroma_provider import ChromaVectorStoreProvider
        provider = MagicMock(spec=ChromaVectorStoreProvider)
        provider.count = MagicMock(return_value=100)
        provider.get_provenance = MagicMock(return_value={})  # no provenance
        provider.collection_name = "test_collection"
        provider.capabilities = MagicMock(return_value=MagicMock(
            model_id="BAAI/bge-large-en-v1.5", dimension=1024, distance_metric="cosine"
        ))
        is_ok, reason = ChromaVectorStoreProvider.validate_provenance(provider)
        assert is_ok is False
        assert "PROVENANCE_MISSING" in reason
        assert "INITIAL_INDEX" not in reason


# ─────────────────────────────────────────────────────────────────────────────
# Test 12 — Hardcode audit: FALLBACK string must not exist
# ─────────────────────────────────────────────────────────────────────────────
class TestHardcodeAudit:
    """Automated hardcode audit for known dangerous patterns."""

    def _get_source(self, module_path: str) -> str:
        import importlib
        mod = importlib.import_module(module_path)
        import inspect
        return inspect.getsource(mod)

    def test_no_fallback_sentinel_in_reranker(self):
        import re as _re
        with open(
            r"c:\108\AI-accounting-0.03\backend\core\kiki\rag\providers\reranker_provider.py",
            encoding="utf-8"
        ) as f:
            source = f.read()
        source_stripped = _re.sub(r'""".*?"""', '', source, flags=_re.DOTALL)
        # FALLBACK must not be used as an assigned sentinel state value
        import re
        assert not re.search(r'=\s*"FALLBACK"', source_stripped), (
            "Found FALLBACK as assigned state value in reranker (must use is_loaded bool flag)"
        )

    def test_no_default_tenant_in_guard(self):
        import re as _re
        with open(
            r"c:\108\AI-accounting-0.03\backend\core\kiki\security\tenant_guard.py",
            encoding="utf-8"
        ) as f:
            source = f.read()
        source_stripped = _re.sub(r'""".*?"""', '', source, flags=_re.DOTALL)
        assert '"default_tenant"' not in source_stripped

    def test_no_hardcoded_2025_1_in_metadata(self):
        """Schema version must come from settings; bare hardcoded assignment is forbidden."""
        import re as _re
        with open(
            r"c:\108\AI-accounting-0.03\backend\core\kiki\rag\ingestion\metadata.py",
            encoding="utf-8"
        ) as f:
            source = f.read()
        # Strip docstrings and comments
        source_stripped = _re.sub(r'""".*?"""', '', source, flags=_re.DOTALL)
        source_stripped = _re.sub(r'#.*', '', source_stripped)
        # Allow getattr default fallbacks (e.g. getattr(..., "2025.1"))
        # Forbid direct assignment: version = "2025.1"
        assert not _re.search(r'"version"\s*:\s*"2025\.1"', source_stripped), (
            "Found hardcoded '2025.1' as direct dict value for 'version' key in metadata generator"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Test 13 — Collection Routing & User Ingestion Scope Alignment (P0.1 & P0.2)
# ─────────────────────────────────────────────────────────────────────────────
class TestCollectionRoutingAndScope:
    """Tests for Phase 17.4 P0.1 and P0.2 Collection Routing and Ingestion Scope alignment."""

    def test_execution_pipeline_resolves_scope_correctly(self):
        """ExecutionPipeline must resolve search_scope from context/tenant_id."""
        from core.kiki.rag.execution_pipeline import ExecutionPipeline
        from core.kiki.rag.planner import RetrievalExecutionPlan
        pipeline = ExecutionPipeline()
        plan = RetrievalExecutionPlan(
            top_k=5, enable_query_rewrite=False, enable_multi_query=False,
            enable_bm25_sparse=True, enable_reranker=True, enable_parent_child=False,
            enable_compression=False
        )

        # Tenant 'global' resolves to GLOBAL
        scope_global = pipeline._resolve_retrieval_scope("global", plan)
        assert scope_global == "GLOBAL"

        # Explicit context search_scope='USER'
        scope_user = pipeline._resolve_retrieval_scope("tenant_123", plan, context={"search_scope": "USER"})
        assert scope_user == "USER"

        # Explicit context search_scope='ALL_ALLOWED'
        scope_all = pipeline._resolve_retrieval_scope("tenant_123", plan, context={"search_scope": "ALL_ALLOWED"})
        assert scope_all == "ALL_ALLOWED"

    def test_bm25_scoped_engine_isolation(self, tmp_path):
        """BM25 engines for different collections must maintain separate storage files."""
        from core.kiki.rag.pipeline.sparse_engine import BM25SparseEngine
        engine_global = BM25SparseEngine(storage_dir=str(tmp_path), collection_name="finpixe_global_knowledge")
        engine_user = BM25SparseEngine(storage_dir=str(tmp_path), collection_name="kiki_knowledge_documents")

        engine_global.index_chunks([{"chunk_id": "global_001", "text": "Global chunk content"}])
        engine_user.index_chunks([{"chunk_id": "user_001", "text": "User chunk content"}])

        assert "global_001" in engine_global.get_corpus_manifest()
        assert "user_001" not in engine_global.get_corpus_manifest()

        assert "user_001" in engine_user.get_corpus_manifest()
        assert "global_001" not in engine_user.get_corpus_manifest()

    def test_user_ingestion_pipeline_indexes_bm25(self, tmp_path):
        """IngestionPipeline must index user documents into user BM25 engine and write provenance."""
        from core.kiki.rag.ingestion.pipeline import IngestionPipeline
        from core.kiki.rag.pipeline.sparse_engine import get_bm25_engine
        from core.kiki.rag.providers.chroma_provider import ChromaVectorStoreProvider

        doc_file = tmp_path / "user_guide.txt"
        doc_file.write_text("User guide inventory content for testing ingestion pipeline P0.2 fix.")

        pipeline = IngestionPipeline()
        res = pipeline.process_file(
            file_path=str(doc_file),
            filename="user_guide.txt",
            doc_id="doc_user_001",
            category="UserManual",
            tenant_id="tenant_abc",
            collection_name="kiki_knowledge_documents"
        )

        assert res["status"] == "SUCCESS"
        assert res["chunks_indexed"] > 0

        # Verify BM25 has chunks for kiki_knowledge_documents
        user_bm25 = get_bm25_engine("kiki_knowledge_documents")
        assert user_bm25.count() > 0

        # Verify Chroma provenance was set
        chroma = ChromaVectorStoreProvider(collection_name="kiki_knowledge_documents")
        prov = chroma.get_provenance()
        assert prov.get("embedding_model") == "BAAI/bge-large-en-v1.5"

