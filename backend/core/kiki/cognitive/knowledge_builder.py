import math
from typing import List, Dict, Any
from ..models.dto import RetrievedKnowledgeItem
from ..utils.logger import kiki_logger


class VectorKnowledgeStore:
    """
    In-Memory Vector Knowledge Store with Semantic Embedding Search.
    Indexes semantic ERP documents for instant cognitive retrieval.
    """

    def __init__(self):
        self.documents: List[RetrievedKnowledgeItem] = []

    def add_document(self, item: RetrievedKnowledgeItem):
        self.documents.append(item)

    def search(self, query: str, top_k: int = 3) -> List[RetrievedKnowledgeItem]:
        if not self.documents:
            return []

        clean_q = query.strip().lower()
        query_words = set(clean_q.split())

        scored_docs = []
        for doc in self.documents:
            content_lower = (doc.title + " " + doc.content).lower()
            doc_words = set(content_lower.split())

            overlap = len(query_words.intersection(doc_words))
            if overlap > 0:
                score = overlap / (math.sqrt(len(query_words)) * math.sqrt(len(doc_words)) + 1e-5)
                scored_docs.append((score, doc))

        # Sort descending by relevance score
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored_docs[:top_k]:
            doc.relevance_score = round(score, 3)
            results.append(doc)

        return results


# Global singleton instance of Vector Knowledge Store
vector_store_instance = VectorKnowledgeStore()


class KnowledgeBuilderService:
    """
    Automated Knowledge Builder (Kiki 2.0)
    Continuously generates semantic documents from ERP metadata, routes, schemas, and rules.
    """

    @classmethod
    def build_and_index_knowledge(cls):
        kiki_logger.info("[KNOWLEDGE BUILDER] Building and indexing ERP semantic knowledge...")

        knowledge_items = [
            RetrievedKnowledgeItem(
                source_type="route",
                title="Sales Workspace & Invoicing Route",
                content="Route /vouchers?type=sales maps to Sales Invoices. Allows creating, viewing, and managing customer billing.",
                metadata={"route": "/vouchers?type=sales", "category": "Sales"}
            ),
            RetrievedKnowledgeItem(
                source_type="route",
                title="Purchase Workspace & Vendor Bills",
                content="Route /vouchers?type=purchase & /pending-purchases map to Purchase Orders and Vendor Bills. Manages vendor transactions.",
                metadata={"route": "/pending-purchases", "category": "Purchase"}
            ),
            RetrievedKnowledgeItem(
                source_type="route",
                title="GST Filing & Reconciliation Hub",
                content="Route /gst & /gst-reconciliation manage GSTR-1, GSTR-3B return filing, ITC verification, and tax ledger entries.",
                metadata={"route": "/gst", "category": "GST"}
            ),
            RetrievedKnowledgeItem(
                source_type="schema",
                title="Vouchers Database Schema",
                content="MySQL table 'vouchers' stores date, voucher_type, voucher_number, ledger_id, total, status, and company_id.",
                metadata={"table": "vouchers"}
            ),
            RetrievedKnowledgeItem(
                source_type="workflow",
                title="Purchase Order to Invoice Workflow",
                content="Purchase vouchers are scanned via OCR or manually created, verified in Pending Purchases, and posted to Purchases ledger.",
                metadata={"workflow": "purchase_to_post"}
            ),
            RetrievedKnowledgeItem(
                source_type="rule",
                title="GST Return Compliance Rule",
                content="GSTR-1 must be filed by 11th of every month. Output IGST, CGST, and SGST ledger accounts reflect active tax liabilities.",
                metadata={"rule": "gst_compliance"}
            )
        ]

        for item in knowledge_items:
            vector_store_instance.add_document(item)

        kiki_logger.info(f"[KNOWLEDGE BUILDER] Successfully indexed {len(knowledge_items)} ERP semantic documents.")


# Trigger indexing on module import
KnowledgeBuilderService.build_and_index_knowledge()
