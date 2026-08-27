"""
Business Ontology & Knowledge Graph Layer
=========================================
Maps natural business terminology ("Customer", "Sales", "GST", "Inventory", "Voucher") to physical database topology.
"""
from typing import Dict, Any, List, Optional

class BusinessOntologyGraph:
    """Enterprise Business Ontology Model."""
    
    # Core domain concepts mapping to physical database schemas
    DOMAINS: Dict[str, Dict[str, Any]] = {
        "Sales": {
            "description": "Customer billing, sales vouchers, revenue entries, and receivables.",
            "primary_tables": [
                "master_voucher_sales",
                "voucher_sales_items",
                "sales_invoices",
                "vouchers",
                "customer_master_customer_basicdetails"
            ],
            "concepts": {
                "Customer": {
                    "table": "customer_master_customer_basicdetails",
                    "aliases": ["customer", "client", "buyer", "party", "sundry debtor", "top customers"],
                    "primary_key": "id"
                },
                "SalesOrder": {
                    "table": "master_voucher_sales",
                    "aliases": ["sales", "sales invoice", "bill", "tax invoice", "sales order", "sales by month", "revenue", "total sales"]
                }
            }
        },
        "Purchase": {
            "description": "Vendor procurement, purchase vouchers, and payables.",
            "primary_tables": [
                "master_voucher_purchases",
                "voucher_purchase_items",
                "vouchers",
                "vendor_master"
            ],
            "concepts": {
                "Vendor": {
                    "table": "vendor_master",
                    "aliases": ["vendor", "supplier", "seller", "top vendors"],
                    "primary_key": "id"
                }
            }
        },
        "Finance": {
            "description": "Ledger balances, trial balance, daybook, journal vouchers, profit/loss.",
            "primary_tables": ["master_ledgers", "advance_allocation"],
            "concepts": {
                "Ledger": {
                    "table": "master_ledgers",
                    "aliases": ["ledger account", "account", "head", "outstanding invoices", "balance"],
                    "primary_key": "id"
                }
            }
        },
        "Inventory": {
            "description": "Stock items, item categories, warehouse stock balances.",
            "primary_tables": ["inventory_master_inventoryitems", "inventory_stock_items"],
            "concepts": {
                "StockItem": {
                    "table": "inventory_master_inventoryitems",
                    "aliases": ["item", "product", "sku", "goods", "stock", "inventory"],
                    "primary_key": "id"
                }
            }
        },
        "GST": {
            "description": "GSTR-1, GSTR-3B reconciliation, HSN codes, tax calculations.",
            "primary_tables": ["gst_reconciliation_gstr3b_reports", "customer_master_customer_gstdetails"],
            "concepts": {
                "GSTIN": {
                    "table": "customer_master_customer_gstdetails",
                    "aliases": ["gst number", "tax id", "gstin", "gst collected", "gst mismatch"]
                }
            }
        }
    }

    @classmethod
    def resolve_domain_for_term(cls, term: str) -> Optional[str]:
        """Find the matching domain key for a given business term or synonym."""
        term_lower = term.lower().strip()
        for domain_name, domain_info in cls.DOMAINS.items():
            if term_lower in domain_name.lower():
                return domain_name
            for concept_name, concept_info in domain_info.get("concepts", {}).items():
                if term_lower in concept_name.lower():
                    return domain_name
                for alias in concept_info.get("aliases", []):
                    if term_lower in alias or alias in term_lower:
                        return domain_name
        return None

    @classmethod
    def get_tables_for_domain(cls, domain_name: str) -> List[str]:
        """Get the physical table names for a business domain."""
        if domain_name in cls.DOMAINS:
            return cls.DOMAINS[domain_name].get("primary_tables", [])
        return []

ontology_graph = BusinessOntologyGraph()
