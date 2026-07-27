import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from django.db import connection
from ..utils.logger import kiki_logger


@dataclass
class EntityResolution:
    """
    Structured result of resolving an entity string (e.g. "OM Muruga Steels")
    against database master tables and transaction records.
    """
    entity_name: str
    entity_type: str  # "vendor", "customer", "party", "unknown"
    resolved_id: Optional[int] = None
    resolved_name: Optional[str] = None


class EntityResolver:
    """
    Component — Entity Resolver
    Resolves raw entity names from user questions (e.g. "OM Muruga Steels", "deepak", "ABC FIRE INDIA")
    against database master tables and transaction ledgers before SQL query building.
    Ensures text names are never compared against integer ID columns like party_customer_id.
    """

    @classmethod
    def resolve(cls, entity_name: str, context: Optional[Any] = None) -> EntityResolution:
        if not entity_name or not isinstance(entity_name, str):
            return EntityResolution(entity_name="", entity_type="unknown")

        clean_name = entity_name.strip()
        kiki_logger.info(f"[ENTITY RESOLVER] Resolving entity: '{clean_name}'")

        try:
            with connection.cursor() as cursor:
                # 1. Search transaction vouchers for existing party name
                cursor.execute(
                    "SELECT DISTINCT party FROM vouchers WHERE party LIKE %s LIMIT 1",
                    [f"%{clean_name}%"]
                )
                row = cursor.fetchone()
                if row and row[0]:
                    resolved_party = row[0]
                    kiki_logger.info(f"[ENTITY RESOLVER] Matched party in vouchers: '{resolved_party}'")
                    return EntityResolution(
                        entity_name=clean_name,
                        entity_type="party",
                        resolved_id=None,
                        resolved_name=resolved_party
                    )

                # 2. Search vendor master table
                cursor.execute(
                    "SELECT id, vendor_name FROM vendor_master_vendorcreation_basicdetail WHERE vendor_name LIKE %s LIMIT 1",
                    [f"%{clean_name}%"]
                )
                row = cursor.fetchone()
                if row:
                    v_id, v_name = row[0], row[1]
                    kiki_logger.info(f"[ENTITY RESOLVER] Matched vendor in master: id={v_id}, name='{v_name}'")
                    return EntityResolution(
                        entity_name=clean_name,
                        entity_type="vendor",
                        resolved_id=int(v_id),
                        resolved_name=v_name
                    )

                # 3. Search customer master table
                cursor.execute(
                    "SELECT id, customer_name FROM customer_master_customer_basicdetails WHERE customer_name LIKE %s LIMIT 1",
                    [f"%{clean_name}%"]
                )
                row = cursor.fetchone()
                if row:
                    c_id, c_name = row[0], row[1]
                    kiki_logger.info(f"[ENTITY RESOLVER] Matched customer in master: id={c_id}, name='{c_name}'")
                    return EntityResolution(
                        entity_name=clean_name,
                        entity_type="customer",
                        resolved_id=int(c_id),
                        resolved_name=c_name
                    )

        except Exception as e:
            kiki_logger.warning(f"[ENTITY RESOLVER] Error resolving entity '{clean_name}': {e}")

        # Fallback if not found in database: return text entity
        return EntityResolution(
            entity_name=clean_name,
            entity_type="party",
            resolved_id=None,
            resolved_name=clean_name
        )
