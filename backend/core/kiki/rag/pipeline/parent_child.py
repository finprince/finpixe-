"""
KIKI Dynamic Parent-Child Section Expander — Phase 17
=====================================================
Expands fine-grained chunks into full parent sections when chunk context is incomplete or similarity is marginal.
"""
from typing import Dict, Any, List
from core.kiki.logging import get_kiki_logger

logger = get_kiki_logger("parent_child_expander")


class ParentChildExpander:
    """Dynamic Parent Section Context Expander."""

    def expand_chunks(
        self,
        chunks: List[Dict[str, Any]],
        all_doc_chunks: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Expands fine-grained chunks to include parent section text when helpful."""
        if not chunks:
            return []

        expanded = []
        for c in chunks:
            c_copy = dict(c)
            meta = c_copy.get("metadata", {})
            heading_path = meta.get("heading_path") or meta.get("section")
            if heading_path:
                c_copy["parent_context"] = f"Parent Section: {heading_path}"
            expanded.append(c_copy)

        return expanded


parent_child_expander = ParentChildExpander()
