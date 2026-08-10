"""
KIKI Session Store
==================
Thread-safe in-memory session store with TTL expiration.
No Redis or database dependency — air-gapped compatible.
"""
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from .conversation_state import ConversationState
from ..config import kiki_settings
from ..logging import get_kiki_logger

logger = get_kiki_logger("session_store")


class SessionStore:
    """Thread-safe in-memory session registry with automatic TTL expiration."""

    def __init__(self):
        self._sessions: Dict[str, ConversationState] = {}
        self._lock = threading.Lock()

    def get_or_create(self, session_id: str, tenant_id: str) -> ConversationState:
        """Returns existing session or creates a fresh one."""
        with self._lock:
            self._evict_expired()
            if session_id not in self._sessions:
                logger.info(f"[SESSION STORE] Creating new session: {session_id} | Tenant: {tenant_id}")
                self._sessions[session_id] = ConversationState(
                    session_id=session_id,
                    tenant_id=tenant_id
                )
            return self._sessions[session_id]

    def save(self, state: ConversationState) -> None:
        """Persists updated session state."""
        with self._lock:
            state.last_active = datetime.utcnow()
            self._sessions[state.session_id] = state

    def _evict_expired(self) -> None:
        """Removes sessions exceeding TTL (called inside lock)."""
        ttl_minutes = getattr(kiki_settings, "CONTEXT_SESSION_TTL_MINUTES", 30)
        cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
        expired = [sid for sid, s in self._sessions.items() if s.last_active < cutoff]
        for sid in expired:
            logger.info(f"[SESSION STORE] Evicting expired session: {sid}")
            del self._sessions[sid]

    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)


session_store = SessionStore()
