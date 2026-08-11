"""
KIKI Model Provenance Canonicalization Module — Phase 19 Hardened
===================================================================
Provides deterministic embedding model identity canonicalization and validation.
Prevents false MIGRATION_REQUIRED states caused by string alias differences (e.g. bge-large-en-v1.5 vs BAAI/bge-large-en-v1.5).
"""

MODEL_ALIAS_MAP = {
    "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    "bge-large-en": "BAAI/bge-large-en-v1.5",
    "baai/bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    "bge-base-en-v1.5": "BAAI/bge-base-en-v1.5",
    "baai/bge-base-en-v1.5": "BAAI/bge-base-en-v1.5",
    "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
    "baai/bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
}

CANONICAL_BGE_LARGE = "BAAI/bge-large-en-v1.5"


def canonicalize_embedding_model_id(model_id: str) -> str:
    """
    Normalizes embedding model string or alias to its canonical HuggingFace ID.
    
    Examples:
      'bge-large-en-v1.5' -> 'BAAI/bge-large-en-v1.5'
      'BAAI/bge-large-en-v1.5' -> 'BAAI/bge-large-en-v1.5'
      'BAAI/bge-large-en-v1.5/' -> 'BAAI/bge-large-en-v1.5'
    """
    if not model_id:
        return CANONICAL_BGE_LARGE
    clean = str(model_id).strip().rstrip("/")
    lower_clean = clean.lower()
    if lower_clean in MODEL_ALIAS_MAP:
        return MODEL_ALIAS_MAP[lower_clean]
    return clean
