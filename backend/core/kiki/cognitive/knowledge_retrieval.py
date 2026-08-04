from typing import List
from ..models.dto import RetrievedKnowledgeItem
from .knowledge_builder import vector_store_instance
from ..utils.logger import kiki_logger


class KnowledgeRetrievalService:
    """
    Component — Knowledge Retrieval Layer (Kiki 2.0)
    Retrieves semantic ERP knowledge documents from Vector Database prior to worker execution.
    Knowledge retrieved enriches the business reasoning phase.
    """

    @classmethod
    def retrieve_knowledge(cls, query: str, top_k: int = 3) -> List[RetrievedKnowledgeItem]:
        kiki_logger.info(f"[KNOWLEDGE RETRIEVAL] Performing vector search for query: '{query}'")
        items = vector_store_instance.search(query, top_k=top_k)
        kiki_logger.info(f"[KNOWLEDGE RETRIEVAL] Retrieved {len(items)} semantic knowledge items.")
        return items
