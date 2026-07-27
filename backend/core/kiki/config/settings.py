import os

class KikiSettings:
    """
    Centralized configuration settings for Kiki AI ERP Agent.
    All configurable parameters are read from environment variables with sensible defaults.
    """
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip('/')
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b")
    MAX_INVESTIGATION_STEPS: int = int(os.getenv("KIKI_MAX_STEPS", "4"))
    MAX_ROWS_PER_QUERY: int = int(os.getenv("KIKI_MAX_ROWS", "200"))
    QUERY_TIMEOUT_SECONDS: int = int(os.getenv("KIKI_QUERY_TIMEOUT", "30"))
    SCHEMA_REFRESH_INTERVAL: int = int(os.getenv("KIKI_SCHEMA_REFRESH", "3600"))
    LLM_TEMPERATURE: float = float(os.getenv("KIKI_LLM_TEMP", "0.1"))
    LLM_TOP_P: float = float(os.getenv("KIKI_LLM_TOP_P", "0.9"))
    MAX_SCHEMA_MATCHES: int = int(os.getenv("KIKI_MAX_SCHEMA_MATCHES", "6"))
    OLLAMA_REQUEST_TIMEOUT: int = int(os.getenv("KIKI_OLLAMA_TIMEOUT", "120"))

