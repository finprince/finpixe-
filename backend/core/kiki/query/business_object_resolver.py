import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from django.db import connection
from ..utils.logger import kiki_logger


@dataclass
class BusinessObjectReference:
    """
    Resolved Business Object Reference DTO.
    Represents internal entity ID, master table, and entity type before SQL generation.
    """
    object_type: str  # "vendor", "customer", "ledger", "item", "voucher", "unknown"
    entity_name: str
    resolved_id: Optional[int] = None
    resolved_name: Optional[str] = None
    master_table: Optional[str] = None
    transaction_table: str = "vouchers"
    id_column: Optional[str] = None
    name_column: Optional[str] = None


class BusinessObjectResolver:
    """
    Component — Business Object Resolver
    Resolves entity names from user questions against ERP master tables (Vendor, Customer, Ledger, Item).
    Maps resolved entities to appropriate business object references before QueryBuilder generates SQL.
    """

    @classmethod
    def resolve(cls, question: str, entity_name: Optional[str] = None) -> BusinessObjectReference:
        clean_q = question.strip().lower()
        search_name = (entity_name or "").strip()

        # Extract entity from question if not provided
        if not search_name:
            # Simple NER heuristic
            match = re.search(r"\b(for|of|by|to)\s+([A-Za-z0-9\s]+?)(?=\s+|\?|$)", question, re.IGNORECASE)
            if match:
                search_name = match.group(2).strip()

        kiki_logger.info(f"[BUSINESS OBJECT RESOLVER] Resolving query='{question}', search_name='{search_name}'")

        try:
            with connection.cursor() as cursor:
                # 1. Vendor Master Resolution
                if any(w in clean_q for w in ["vendor", "supplier", "purchase", "payables"]) or search_name:
                    cursor.execute(
                        "SELECT id, vendor_name FROM vendor_master_vendorcreation_basicdetail WHERE vendor_name LIKE %s LIMIT 1",
                        [f"%{search_name}%"] if search_name else ["%"]
                    )
                    row = cursor.fetchone()
                    if row and search_name:
                        return BusinessObjectReference(
                            object_type="vendor",
                            entity_name=search_name,
                            resolved_id=int(row[0]),
                            resolved_name=row[1],
                            master_table="vendor_master_vendorcreation_basicdetail",
                            transaction_table="vouchers",
                            id_column="party_vendor_id",
                            name_column="party"
                        )

                # 2. Customer Master Resolution
                if any(w in clean_q for w in ["customer", "client", "sales", "receivables"]) or search_name:
                    cursor.execute(
                        "SELECT id, customer_name FROM customer_master_customer_basicdetails WHERE customer_name LIKE %s LIMIT 1",
                        [f"%{search_name}%"] if search_name else ["%"]
                    )
                    row = cursor.fetchone()
                    if row and search_name:
                        return BusinessObjectReference(
                            object_type="customer",
                            entity_name=search_name,
                            resolved_id=int(row[0]),
                            resolved_name=row[1],
                            master_table="customer_master_customer_basicdetails",
                            transaction_table="vouchers",
                            id_column="party_customer_id",
                            name_column="party"
                        )

                # 3. Check Vouchers Party Text Match
                if search_name:
                    cursor.execute(
                        "SELECT DISTINCT party FROM vouchers WHERE party LIKE %s LIMIT 1",
                        [f"%{search_name}%"]
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        return BusinessObjectReference(
                            object_type="party",
                            entity_name=search_name,
                            resolved_id=None,
                            resolved_name=row[0],
                            master_table="vouchers",
                            transaction_table="vouchers",
                            id_column=None,
                            name_column="party"
                        )

        except Exception as e:
            kiki_logger.warning(f"[BUSINESS OBJECT RESOLVER] Resolution warning: {e}")

        # Fallback default
        return BusinessObjectReference(
            object_type="voucher",
            entity_name=search_name,
            resolved_id=None,
            resolved_name=search_name if search_name else None,
            master_table="vouchers",
            transaction_table="vouchers",
            id_column=None,
            name_column="party"
        )
