"""
RAG Response & Retrieval Cache (Phase 18.1 Hardened)
=====================================================
Provides scope-aware, authorization-aware, conversation-aware, and model-versioned
in-memory caching for deterministic RAG query turns.

Security Invariants:
1. Tenant Isolation: tenant_id included in key
2. Authorization Isolation: auth_fingerprint included in key (roles/document ACLs)
3. Scope Isolation: search_scope included in key
4. Index Version Invalidation: index_version included in key
5. Model & Prompt Invalidation: model_id and synthesis_prompt_version included in key
6. Conversation Isolation: conversation_context hash included for multi-turn coref turns
"""
import hashlib
import time
import threading
from typing import Dict, Any, Optional, Tuple
from core.kiki.config import kiki_settings
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("response_cache")


class RAGResponseCache:
    """Thread-safe, authorization-aware, conversation-aware RAG response cache."""

    def __init__(self, ttl_seconds: Optional[int] = None):
        self.ttl = ttl_seconds or getattr(kiki_settings, "RESPONSE_CACHE_TTL_SECONDS", 3600)
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self._lock = threading.Lock()

    def _make_key(
        self,
        query: str,
        tenant_id: str,
        scope: str,
        auth_fingerprint: Optional[str] = None,
        conversation_context: Optional[str] = None,
        index_version: Optional[str] = None,
        model_id: Optional[str] = None,
        prompt_version: Optional[str] = None
    ) -> str:
        """Generates a secure, multi-dimensional SHA-256 cache key."""
        normalized_q = query.strip().lower()
        auth_fp = auth_fingerprint or "default_auth"
        conv_ctx = conversation_context or "standalone"
        idx_ver = index_version or "v1"
        model = model_id or getattr(kiki_settings, "OLLAMA_MODEL", "qwen2.5vl:7b")
        prompt_ver = prompt_version or getattr(kiki_settings, "SYNTHESIS_PROMPT_VERSION", "v2025.1")

        key_raw = (
            f"tenant:{tenant_id}|auth:{auth_fp}|scope:{scope}|"
            f"index:{idx_ver}|model:{model}|prompt:{prompt_ver}|"
            f"conv:{conv_ctx}|q:{normalized_q}"
        )
        return hashlib.sha256(key_raw.encode('utf-8')).hexdigest()

    def get(
        self,
        query: str,
        tenant_id: str,
        scope: str,
        auth_fingerprint: Optional[str] = None,
        conversation_context: Optional[str] = None,
        index_version: Optional[str] = None,
        model_id: Optional[str] = None,
        prompt_version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves cached response payload if valid and not expired."""
        if not getattr(kiki_settings, "RESPONSE_CACHE_ENABLED", True):
            return None

        key = self._make_key(
            query=query,
            tenant_id=tenant_id,
            scope=scope,
            auth_fingerprint=auth_fingerprint,
            conversation_context=conversation_context,
            index_version=index_version,
            model_id=model_id,
            prompt_version=prompt_version
        )
        now = time.time()

        with self._lock:
            if key in self._cache:
                payload, cached_at = self._cache[key]
                if (now - cached_at) <= self.ttl:
                    logger.info(f"[RAG CACHE] ✅ Secure Cache HIT for tenant '{tenant_id}' | scope '{scope}'")
                    return payload
                else:
                    del self._cache[key]

        return None

    def set(
        self,
        query: str,
        tenant_id: str,
        scope: str,
        response_data: Dict[str, Any],
        auth_fingerprint: Optional[str] = None,
        conversation_context: Optional[str] = None,
        index_version: Optional[str] = None,
        model_id: Optional[str] = None,
        prompt_version: Optional[str] = None
    ) -> None:
        """Stores a response payload in the cache with complete security metadata."""
        if not getattr(kiki_settings, "RESPONSE_CACHE_ENABLED", True):
            return

        key = self._make_key(
            query=query,
            tenant_id=tenant_id,
            scope=scope,
            auth_fingerprint=auth_fingerprint,
            conversation_context=conversation_context,
            index_version=index_version,
            model_id=model_id,
            prompt_version=prompt_version
        )
        now = time.time()

        with self._lock:
            self._cache[key] = (response_data, now)
            if len(self._cache) > 10000:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]

        logger.info(f"[RAG CACHE] Stored secure response entry for tenant '{tenant_id}' | scope '{scope}'")

    def invalidate_all(self) -> None:
        """Clears the entire cache."""
        with self._lock:
            self._cache.clear()
        logger.info("[RAG CACHE] Invalidated all cache entries.")

# Global Singleton Instance
rag_response_cache = RAGResponseCache()
