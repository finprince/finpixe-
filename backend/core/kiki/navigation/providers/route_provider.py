from typing import List
from .base_provider import BaseDiscoveryProvider, NavigationNode


class RouteDiscoveryProvider(BaseDiscoveryProvider):
    """
    Provider — Route Discovery Provider
    Authoritative Source: Application Frontend Route Tree
    """

    def discover(self) -> List[NavigationNode]:
        # Discovers application routes matching frontend pages
        return [
            NavigationNode(
                id="core.dashboard",
                title="Dashboard",
                route="/dashboard?page=dashboard",
                category="Core Workspace",
                business_domain="Overview",
                description="Main executive dashboard with financial KPIs, sales overview, and recent activity.",
                capabilities=["view dashboard", "check financial overview", "view kpi metrics"],
                search_terms=["dashboard", "home", "main page", "kpi", "overview"]
            ),
            NavigationNode(
                id="vouchers.entry",
                title="Voucher Entry",
                route="/dashboard?page=vouchers",
                category="Core Workspace",
                business_domain="Accounting",
                description="Create, view, and manage accounting vouchers including sales, purchase, payment, and receipt.",
                capabilities=["create voucher", "view vouchers", "record transaction", "journal entry"],
                search_terms=["voucher", "vouchers", "voucher entry", "create voucher", "transaction"]
            ),
            NavigationNode(
                id="vendor.portal",
                title="Vendor Portal",
                route="/dashboard?page=vendor-portal",
                category="Portals & Operations",
                business_domain="Purchase",
                description="Manage vendor details, supplier creation, bank details, TDS settings, and vendor master list.",
                capabilities=["create vendor", "manage suppliers", "view vendor master", "edit supplier details"],
                search_terms=["vendor", "vendors", "supplier", "supplier portal", "vendor master"]
            ),
            NavigationNode(
                id="customer.portal",
                title="Customer Portal",
                route="/dashboard?page=customer-portal",
                category="Portals & Operations",
                business_domain="Sales",
                description="Manage customer master details, client creation, credit limits, and customer lists.",
                capabilities=["create customer", "manage clients", "view customer master", "edit customer details"],
                search_terms=["customer", "customers", "client", "customer portal", "customer master"]
            ),
            NavigationNode(
                id="inventory.management",
                title="Inventory Management",
                route="/dashboard?page=inventory",
                category="Portals & Operations",
                business_domain="Inventory",
                description="Track stock items, warehouse inventory, item groups, units of measure, and stock adjustments.",
                capabilities=["manage stock", "view inventory", "create stock item", "stock adjustment", "manage warehouses"],
                search_terms=["inventory", "stock", "items", "warehouse", "item master", "products"]
            ),
            NavigationNode(
                id="purchase.pending_purchase",
                title="Pending Purchase",
                route="/dashboard?page=PendingPurchase",
                category="Portals & Operations",
                business_domain="Purchase",
                description="Review, validate, and approve OCR scanned supplier invoices awaiting GRN or voucher creation.",
                capabilities=["approve supplier invoices", "validate OCR invoices", "review pending bills", "approve purchase"],
                search_terms=["pending purchase", "ocr validation", "review bill", "approve invoice", "ocr"]
            ),
            NavigationNode(
                id="purchase.orders",
                title="Purchase Orders",
                route="/dashboard?page=purchase",
                category="Portals & Operations",
                business_domain="Purchase",
                description="Manage purchase orders, pending purchase requisitions, and PO status.",
                capabilities=["create purchase order", "manage po", "view purchase orders"],
                search_terms=["purchase", "purchase order", "po", "pending purchase orders"]
            ),
            NavigationNode(
                id="reports.financial",
                title="Reports",
                route="/dashboard?page=reports",
                category="Compliance & Audit",
                business_domain="Compliance",
                description="Generate financial statements, balance sheets, profit and loss, trial balance, and sales reports.",
                capabilities=["view reports", "generate balance sheet", "view profit and loss", "view trial balance", "financial analytics"],
                search_terms=["reports", "analytics", "financial reports", "balance sheet", "p&l", "trial balance", "trial balance report"]
            ),
            NavigationNode(
                id="gst.gstr1",
                title="GSTR-1 Report",
                route="/dashboard?page=gst",
                category="Compliance & Audit",
                business_domain="Compliance",
                description="Prepare GSTR-1, GSTR-3B filings, GST reconciliation, and tax summary reports.",
                capabilities=["prepare gst return", "view gstr-1", "gst reconciliation", "tax summary"],
                search_terms=["gst", "gstr1", "gstr-1", "gstr3b", "gst report", "returns"]
            ),
            NavigationNode(
                id="accounting.ledgers",
                title="Accounting Ledgers",
                route="/dashboard?page=ledgers",
                category="Core Workspace",
                business_domain="Accounting",
                description="Manage chart of accounts, ledger masters, ledger groups, trial balance, and account balances.",
                capabilities=["manage ledgers", "view chart of accounts", "create ledger", "account balances", "view trial balance"],
                search_terms=["ledger", "ledgers", "chart of accounts", "accounting master", "trial balance"]
            ),

            NavigationNode(
                id="banking.reconciliation",
                title="Bank Reconciliation",
                route="/dashboard?page=bank-upload",
                category="Portals & Operations",
                business_domain="Banking",
                description="Upload bank statements, reconcile bank transactions, and auto-match voucher entries.",
                capabilities=["upload bank statement", "reconcile bank statements", "bank reconciliation", "match transactions"],
                search_terms=["bank upload", "bank statement", "bank reconciliation", "reconcile bank"]
            )
        ]
