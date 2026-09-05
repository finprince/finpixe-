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
            "description": "Customer billing, sales vouchers, revenue entries, customer invoices, and receivables.",
            "primary_tables": [
                "vouchers",
                "voucher_sales_invoicedetails",
                "voucher_sales_paymentdetails",
                "voucher_sales_items",
                "customer_master_customer_basicdetails"
            ],
            "concepts": {
                "SalesInvoice": {
                    "table": "vouchers",
                    "aliases": ["sales", "sale", "sales invoice", "bill", "tax invoice", "sales order", "sales by month", "revenue", "total sales", "sold"]
                },
                "Customer": {
                    "table": "customer_master_customer_basicdetails",
                    "aliases": ["customer", "customers", "client", "clients", "buyer", "party", "sundry debtor", "top customers"],
                    "primary_key": "id"
                }
            }
        },
        "Purchase": {
            "description": "Vendor procurement, purchase vouchers, bills, and payables.",
            "primary_tables": [
                "vouchers",
                "voucher_purchase_supplier_details",
                "voucher_purchase_items",
                "voucher_purchase_supply_inr_details",
                "vendor_master_vendorcreation_basicdetail"
            ],
            "concepts": {
                "PurchaseInvoice": {
                    "table": "vouchers",
                    "aliases": ["purchase", "purchases", "procurement", "bought", "purchase bill", "supplier invoice", "total purchases"]
                },
                "Vendor": {
                    "table": "vendor_master_vendorcreation_basicdetail",
                    "aliases": ["vendor", "vendors", "supplier", "suppliers", "seller", "top vendors", "top suppliers"],
                    "primary_key": "id"
                }
            }
        },
        "Receivables": {
            "description": "Outstanding customer balances, unpaid sales invoices, and dues.",
            "primary_tables": ["advance_allocation", "pending_transaction", "vouchers", "customer_master_customer_basicdetails"],
            "concepts": {
                "Receivable": {
                    "table": "advance_allocation",
                    "aliases": ["receivable", "receivables", "owe me", "owes me", "customer dues", "unpaid sales", "overdue invoices", "outstanding customer", "pending invoices", "debtors"]
                }
            }
        },
        "Payables": {
            "description": "Outstanding vendor bills, supplier dues, and payables.",
            "primary_tables": ["advance_allocation", "pending_transaction", "vouchers", "vendor_master_vendorcreation_basicdetail"],
            "concepts": {
                "Payable": {
                    "table": "advance_allocation",
                    "aliases": ["payable", "payables", "i owe", "we owe", "supplier dues", "vendor dues", "unpaid bills", "overdue bills", "outstanding supplier", "pending bills", "creditors"]
                }
            }
        },
        "Inventory": {
            "description": "Stock items, item categories, warehouse stock balances, and reorder levels.",
            "primary_tables": ["inventory_master_inventoryitems", "inventory_stock_items", "inventory_stock_movements"],
            "concepts": {
                "StockItem": {
                    "table": "inventory_master_inventoryitems",
                    "aliases": ["item", "items", "product", "products", "sku", "goods", "stock", "inventory", "low stock", "reorder", "valuation"],
                    "primary_key": "id"
                }
            }
        },
        "Finance": {
            "description": "Ledger balances, cash balance, bank balance, trial balance, daybook, profit/loss.",
            "primary_tables": ["master_ledgers", "entries", "transactions", "advance_allocation"],
            "concepts": {
                "Ledger": {
                    "table": "master_ledgers",
                    "aliases": ["ledger", "ledgers", "ledger balance", "account", "accounts", "cash", "bank", "cash balance", "bank balance", "profit", "loss", "daybook", "trial balance"],
                    "primary_key": "id"
                }
            }
        },
        "GST": {
            "description": "GSTR-1, GSTR-2B, GSTR-3B tax calculations, output tax, input tax credit.",
            "primary_tables": ["vouchers", "gst_reconciliation_gstr2b_invoices", "gst_reconciliation_gstr3b_reports"],
            "concepts": {
                "GST": {
                    "table": "vouchers",
                    "aliases": ["gst", "gst collected", "tax", "cgst", "sgst", "igst", "input gst", "output gst", "net gst", "tax liability", "tax collected"]
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
