"""
KIKI Configuration Settings — Phase 19 Hardened
=================================================
Configuration driven architecture settings loaded from environment or defaults.
Single source of truth for RAG models, CUDA/GPU devices, local paths, and offline flags.
"""
import os

class KikiSettings:
    # Ollama Local Runtime Configuration
    OLLAMA_BASE_URL: str = os.getenv("KIKI_OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("KIKI_OLLAMA_MODEL", "qwen2.5vl:7b")
    ROUTER_MODEL: str = os.getenv("KIKI_ROUTER_MODEL", "llama3:latest")
    REASONING_MODEL: str = os.getenv("KIKI_REASONING_MODEL", "qwen2.5vl:7b")
    EMBEDDING_MODEL: str = os.getenv("KIKI_EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
    RERANKER_MODEL: str = os.getenv(
        "KIKI_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 19 — Local-Only RAG & CUDA GPU Acceleration Configuration
    # ─────────────────────────────────────────────────────────────────────────
    EMBEDDING_DEVICE: str = os.getenv("KIKI_EMBEDDING_DEVICE", "cuda")
    RERANKER_DEVICE: str = os.getenv("KIKI_RERANKER_DEVICE", "cuda")
    RAG_REQUIRE_GPU: bool = os.getenv("KIKI_RAG_REQUIRE_GPU", "true").lower() == "true"
    DEVELOPMENT_ALLOW_CPU_FALLBACK: bool = os.getenv("KIKI_ALLOW_CPU_FALLBACK", "false").lower() == "true"

    # Offline / Local-Only Enforcements (Zero Runtime Internet Network Calls)
    HF_LOCAL_ONLY: bool = os.getenv("HF_LOCAL_ONLY", "true").lower() == "true"
    HF_HUB_OFFLINE: bool = os.getenv("HF_HUB_OFFLINE", "true").lower() == "true"
    TRANSFORMERS_OFFLINE: bool = os.getenv("TRANSFORMERS_OFFLINE", "true").lower() == "true"
    RAG_NETWORK_REQUIRED: bool = os.getenv("KIKI_RAG_NETWORK_REQUIRED", "false").lower() == "true"

    # Local Model Storage Directory (Pre-provisioned by prepare_local_rag_models)
    LOCAL_MODELS_DIR: str = os.getenv(
        "KIKI_LOCAL_MODELS_DIR",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "models", "rag"))
    )


    OLLAMA_GPU_REQUIRED: bool = os.getenv("KIKI_OLLAMA_GPU_REQUIRED", "true").lower() == "true"

    # Model Execution Timeouts (Seconds)
    ROUTER_TIMEOUT_SECONDS: int = int(os.getenv("KIKI_ROUTER_TIMEOUT", "30"))
    REASONING_TIMEOUT_SECONDS: int = int(os.getenv("KIKI_REASONING_TIMEOUT", "60"))
    
    # Redis Cache Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TTL: int = int(os.getenv("KIKI_CACHE_TTL", "900"))  # 15 mins
    
    # Vector DB (ChromaDB) Configuration
    CHROMADB_PERSIST_DIRECTORY: str = os.getenv(
        "KIKI_CHROMADB_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "chromadb")
    )
    
    # Query Safety Limits
    MAX_QUERY_ROW_LIMIT: int = int(os.getenv("KIKI_MAX_QUERY_ROW_LIMIT", "500"))
    MAX_QUERY_SCAN_LIMIT: int = int(os.getenv("KIKI_MAX_QUERY_SCAN_LIMIT", "50000"))
    
    # Semantic Knowledge Routing Threshold
    KNOWLEDGE_ROUTING_THRESHOLD: float = float(os.getenv("KIKI_KNOWLEDGE_ROUTING_THRESHOLD", "0.50"))

    # Phase 15 — Conversation Context Engine
    MAX_CONTEXT_TURNS: int = int(os.getenv("KIKI_MAX_CONTEXT_TURNS", "10"))
    CONTEXT_SESSION_TTL_MINUTES: int = int(os.getenv("KIKI_SESSION_TTL_MINUTES", "30"))
    NLU_MAX_HISTORY_TURNS: int = int(os.getenv("KIKI_NLU_HISTORY_TURNS", "5"))
    
    # Active Providers (Provider Pattern)
    LLM_PROVIDER: str = os.getenv("KIKI_LLM_PROVIDER", "ollama")
    EMBEDDING_PROVIDER: str = os.getenv("KIKI_EMBEDDING_PROVIDER", "bge_local")
    VECTOR_PROVIDER: str = os.getenv("KIKI_VECTOR_PROVIDER", "chromadb")
    CACHE_PROVIDER: str = os.getenv("KIKI_CACHE_PROVIDER", "redis")

    # Phase 17.1 — RAG Embedding Explicit Configuration
    EMBEDDING_DISTANCE_METRIC: str = os.getenv("KIKI_EMBEDDING_DISTANCE_METRIC", "cosine")
    EMBEDDING_NORMALIZED: bool = os.getenv("KIKI_EMBEDDING_NORMALIZED", "true").lower() == "true"
    RAG_INDEX_RETENTION_COUNT: int = int(os.getenv("KIKI_INDEX_RETENTION_COUNT", "3"))

    # Chroma collection names
    PRIMARY_COLLECTION_NAME: str = os.getenv(
        "KIKI_PRIMARY_COLLECTION", "kiki_knowledge_documents"
    )
    GLOBAL_COLLECTION_NAME: str = os.getenv(
        "KIKI_GLOBAL_COLLECTION", "finpixe_global_knowledge"
    )

    # Global knowledge corpus tenant / security identity
    GLOBAL_KNOWLEDGE_TENANT_ID: str = os.getenv("KIKI_GLOBAL_TENANT_ID", "global")
    GLOBAL_KNOWLEDGE_SECURITY_LEVEL: str = os.getenv(
        "KIKI_GLOBAL_SECURITY_LEVEL", "Public"
    )

    # Schema / metadata version written into every indexed chunk
    SCHEMA_VERSION: str = os.getenv("KIKI_SCHEMA_VERSION", "2025.1")

    # Retrieval tuning knobs
    RAG_TOP_K: int = int(os.getenv("KIKI_RAG_TOP_K", "10"))
    RERANKER_TOP_K: int = int(os.getenv("KIKI_RERANKER_TOP_K", "5"))
    CONTEXT_TOKEN_BUDGET: int = int(os.getenv("KIKI_CONTEXT_TOKEN_BUDGET", "2584"))

    # NLU adaptive bypass
    NLU_BYPASS_ENABLED: bool = os.getenv("KIKI_NLU_BYPASS", "true").lower() == "true"

    # Tenant security — fail-closed policy
    TENANT_ANONYMOUS_ALLOWED: bool = (
        os.getenv("KIKI_TENANT_ANON_ALLOWED", "true").lower() == "true"
    )

    # Phase 18 & 18.1: Ollama performance, dynamic token budget & synthesis settings
    OLLAMA_KEEP_ALIVE: str = os.getenv("KIKI_OLLAMA_KEEP_ALIVE", "60m")
    OLLAMA_MIN_CTX: int = int(os.getenv("KIKI_OLLAMA_MIN_CTX", "2048"))
    OLLAMA_MAX_CTX: int = int(os.getenv("KIKI_OLLAMA_MAX_CTX", "8192"))
    OLLAMA_MIN_OUTPUT_TOKENS: int = int(os.getenv("KIKI_OLLAMA_MIN_OUTPUT", "128"))
    OLLAMA_DEFAULT_OUTPUT_TOKENS: int = int(os.getenv("KIKI_OLLAMA_DEFAULT_OUTPUT", "512"))
    OLLAMA_MAX_OUTPUT_TOKENS: int = int(os.getenv("KIKI_OLLAMA_MAX_OUTPUT", "1536"))
    OLLAMA_NUM_THREAD: int = int(os.getenv("KIKI_OLLAMA_NUM_THREAD", "8"))
    SYNTHESIS_PROMPT_VERSION: str = os.getenv("KIKI_SYNTHESIS_PROMPT_VER", "v2025.1")
    RESPONSE_CACHE_ENABLED: bool = os.getenv("KIKI_RESPONSE_CACHE_ENABLED", "true").lower() == "true"
    RESPONSE_CACHE_TTL_SECONDS: int = int(os.getenv("KIKI_RESPONSE_CACHE_TTL", "3600"))

kiki_settings = KikiSettings()

if kiki_settings.HF_HUB_OFFLINE:
    os.environ["HF_HUB_OFFLINE"] = "1"
if kiki_settings.TRANSFORMERS_OFFLINE:
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
if kiki_settings.HF_LOCAL_ONLY:
    os.environ["HF_LOCAL_ONLY"] = "1"

