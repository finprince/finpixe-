"""
KIKI Conversation State Data Model
====================================
Lightweight per-session conversation memory for multi-turn dialogue.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ConversationTurn:
    """Single turn in the conversation history."""
    turn_index: int
    original_question: str
    rewritten_question: str
    intent: str                          # "KNOWLEDGE" | "KPI_QUERY" | "GREETING" etc.
    engine_hint: str                     # "KNOWLEDGE" | "ERP" | "GREETING"
    resolved_entity: Optional[str]
    resolved_topic: Optional[str]
    resolved_document: Optional[str]
    domain: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConversationState:
    """Rolling window conversation state for a single session."""
    session_id: str
    tenant_id: str
    turns: List[ConversationTurn] = field(default_factory=list)

    # Current active context slots
    current_entity: Optional[str] = None          # e.g. "deepak", "ABC FIRE INDIA"
    current_document: Optional[str] = None        # e.g. "AST-RIM Optimizer User Manual"
    current_topic: Optional[str] = None           # e.g. "Optimization Engine"
    current_domain: str = "UNKNOWN"               # "KNOWLEDGE" | "ERP"
    current_module: Optional[str] = None          # e.g. "Sales", "Purchase", "Receivables", "Payables", "GST"
    current_business_object: Optional[str] = None # e.g. "Invoice", "StockItem", "Ledger"
    current_time_context: Optional[str] = None    # e.g. "today", "August 2026", "FY 2025-26"
    active_date_range: Optional[dict] = None      # e.g. {"start_date": "2026-08-01", "end_date": "2026-08-31", "label": "August 2026"}
    active_entity: Optional[str] = None           # e.g. "deepak", "ABC FIRE INDIA"
    active_domain: Optional[str] = None           # e.g. "Sales", "Purchase", "Receivables"

    last_active: datetime = field(default_factory=datetime.utcnow)

    def add_turn(self, turn: ConversationTurn, max_turns: int = 10) -> None:
        """Append turn to history, evicting oldest if over limit."""
        self.turns.append(turn)
        if len(self.turns) > max_turns:
            self.turns = self.turns[-max_turns:]
        self.last_active = datetime.utcnow()

    def update_context(self, nlu_result: dict) -> None:
        """Update context slots from NLU JSON result."""
        entity = nlu_result.get("resolved_entity")
        document = nlu_result.get("resolved_document")
        topic = nlu_result.get("resolved_topic")
        engine_hint = nlu_result.get("engine_hint", "UNKNOWN")
        domain = nlu_result.get("domain")

        if entity:
            self.current_entity = entity
            self.active_entity = entity
        if document:
            self.current_document = document
        if topic:
            self.current_topic = topic
        if engine_hint in ("KNOWLEDGE", "ERP"):
            self.current_domain = engine_hint
        if domain:
            self.active_domain = domain

    def set_active_date_range(self, date_range: Optional[dict]) -> None:
        """Set active date range context."""
        if date_range:
            self.active_date_range = date_range
            self.current_time_context = date_range.get("label")

    def set_active_entity(self, entity: Optional[str]) -> None:
        """Set active customer/vendor/item entity context."""
        if entity:
            self.active_entity = entity
            self.current_entity = entity

    def set_active_domain(self, domain: Optional[str]) -> None:
        """Set active business domain context."""
        if domain:
            self.active_domain = domain
            self.current_module = domain

    def get_history_summary(self, last_n: int = 5) -> str:
        """Returns a compact conversation history string for the NLU prompt."""
        recent = self.turns[-last_n:] if self.turns else []
        lines = []
        for turn in recent:
            lines.append(f"User: {turn.original_question}")
            if turn.rewritten_question != turn.original_question:
                lines.append(f"Rewritten: {turn.rewritten_question}")
            if turn.resolved_entity:
                lines.append(f"Entity: {turn.resolved_entity}")
            lines.append(f"Intent: {turn.engine_hint}")
        return "\n".join(lines) if lines else "No previous conversation."

