# KIKI Modern RAG Current Runtime Architecture Flow Map

```
DOCX File (C:\Users\ulaganathan\Downloads\Finpixe Inventory sample content.docx)
  │
  ▼
[Document Loader] (core/kiki/rag/loader.py -> DocumentLoader.load_document)
  │  - Python-docx parser: docx.Document(file_path)
  │  - Output: {"full_text": str (33,209 chars), "total_pages": 1, "filename": str}
  │
  ▼
[Text Cleaner] (core/kiki/rag/ingestion/cleaner.py -> TextCleaner.clean_text)
  │  - Strips non-printable control chars, normalizes whitespace & quotes
  │  - Output: Cleaned text (32,764 chars)
  │
  ▼
[Structure Extractor] (core/kiki/rag/ingestion/structure.py -> StructureExtractor.extract_heading_path)
  │  - Scans for structural heading patterns
  │  - Output: Heading path string
  │
  ▼
[Semantic Chunker] (core/kiki/rag/chunker.py -> SemanticChunker.chunk_document)
  │  - Paragraph-boundary chunking with target size ~500 chars (65 words)
  │  - Output: List of 85 raw chunk dictionaries
  │
  ▼
[Metadata Generator] (core/kiki/rag/ingestion/metadata.py -> MetadataGenerator.generate_metadata)
  │  - Attaches document_id, filename, category, tenant_id, security_level, page_number, section_heading
  │  - Output: Enriched chunk dictionaries with metadata
  │
  ▼
[Chunk Validator] (core/kiki/rag/ingestion/validator.py -> ChunkValidator.validate_chunks)
  │  - Minimum length shield (>20 chars), non-empty validation, deduplication check
  │  - Output: List of 85 validated chunk dictionaries
  │
  ├───────────────────────────────────────────────────────┐
  ▼                                                       ▼
[BGE Embedding Provider]                                [BM25 Sparse Engine]
(core/kiki/rag/providers/embedding_provider.py)         (core/kiki/rag/pipeline/sparse_engine.py)
  │ - Model: BAAI/bge-large-en-v1.5 (1024-dim)              │ - Tokenizer: Regex word tokenizer
  │ - Generates 1024-dim L2 normalized vectors            │ - Inverted index serialized to disk
  ▼                                                       ▼
[Chroma Vector Store]                                   [BM25 Index Storage]
(core/kiki/rag/providers/chroma_provider.py)            (data/bm25/bm25_index.pkl)
  │ - Collection: 'forensic_inventory_test'               │ - 85 chunks indexed with term freqs
  └───────────────────────────┬───────────────────────────┘
                              │
  ┌───────────────────────────┘
  ▼
User Query (Frontend / API)
  │
  ▼
[Semantic NLU Analyzer] (core/kiki/context/nlu_analyzer.py -> NLUAnalyzer.analyze)
  │  - Ollama local model extracts resolved_entity and produces self-contained rewritten_question
  │
  ├───────────────────────────────────────────────────────┐
  ▼                                                       ▼
[Dense Retrieval]                                       [BM25 Sparse Search]
(ChromaVectorStoreProvider.query_vectors)                (BM25SparseEngine.search_sparse)
  │ - Vector similarity search (Cosine, top_k=10)         │ - Lexical term frequency BM25 score (top_k=10)
  └───────────────────────────┬───────────────────────────┘
                              │
                              ▼
[Reciprocal Rank Fusion (RRF)] (core/kiki/rag/pipeline/fusion_engine.py -> RRFFusionEngine.fuse_results)
  │  - Fuses dense and sparse candidate lists using RRF score = 1 / (60 + rank)
  │  - Merges top 10 hybrid candidates
  │
  ▼
[Cross-Encoder Reranker] (core/kiki/rag/providers/reranker_provider.py -> LocalRerankerProvider.rerank)
  │  - Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  │  - Reranks top 10 candidates down to top 5 evidence chunks
  │
  ▼
[Evidence Builder] (core/kiki/rag/pipeline/evidence_builder.py -> EvidenceBuilder.build_evidence)
  │  - Wraps top chunks into standardized Evidence DTOs with metadata & provenance
  │
  ▼
[Evidence Aggregator] (core/kiki/evidence/aggregator.py -> EvidenceAggregator.aggregate)
  │  - Ranks evidence objects by confidence and formats citation packages
  │
  ▼
[Context Compressor Engine] (core/kiki/rag/pipeline/compressor_engine.py -> ContextCompressorEngine.compress_chunks)
  │  - Computes safe_evidence_budget = max_tokens - response_reserve - 1000
  │  - Evidence tokens <= budget: sentence compression bypassed (100% text preserved)
  │
  ▼
[Ollama LLM Synthesis] (core/kiki/runtime/ollama_client.py -> OllamaClient.generate)
  │  - Model: llama3:latest
  │  - Generates grounded factual response strictly based on evidence
  │
  ▼
Clean Grounded Response + Markdown Citations
```
