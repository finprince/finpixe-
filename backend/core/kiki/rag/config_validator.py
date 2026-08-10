"""
KIKI RAG Configuration Validator — Phase 17.1 Zero Hardcode Architecture
========================================================================
Enforces strict explicit configuration presence for RAG embedding parameters.
Returns False if any required setting is unconfigured or blank.
Prevents silent fallback strings or default booleans in code constructors.
"""
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("rag_config_validator")


class RAGConfigurationValidator:
    """Strict Configuration Validator for RAG Subsystem Parameters."""

    REQUIRED_SETTINGS = [
        "EMBEDDING_MODEL",
        "EMBEDDING_DISTANCE_METRIC",
        "EMBEDDING_NORMALIZED",
        "RAG_INDEX_RETENTION_COUNT"
    ]

    @classmethod
    def validate(cls) -> bool:
        """
        Validates presence of all required RAG configuration keys.
        Logs explicit errors if any parameter is unconfigured.
        """
        missing_keys = []
        for key in cls.REQUIRED_SETTINGS:
            val = getattr(kiki_settings, key, None)
            if val is None or str(val).strip() == "":
                missing_keys.append(key)

        if missing_keys:
            logger.error(
                f"[RAG CONFIG ERROR] Missing explicit configuration keys: {missing_keys}. "
                "Subsystem state set to NOT_READY."
            )
            return False

        logger.info("[RAG CONFIG VALIDATION] All required RAG settings explicitly configured.")
        return True


rag_config_validator = RAGConfigurationValidator()
