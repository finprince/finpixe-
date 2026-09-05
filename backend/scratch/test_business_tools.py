import os
import sys
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from core.kiki.tools.business_tools import business_tools
from core.kiki.tools.date_resolver import date_resolver

tenant_id = "2eda0ac6-6af2-493e-8792-bc973fe946b7"

print("=== TESTING BUSINESS TOOLS ON TENANT ===")

# 1. Sales
sales_all = business_tools.get_sales_summary(tenant_id)
print("\n1. Sales (All Time):", sales_all["total_sales_formatted"], f"({sales_all['count']} invoices)")
for r in sales_all["formatted_records"][:3]:
    print("   ", r)

# 2. Purchases
purch_all = business_tools.get_purchase_summary(tenant_id)
print("\n2. Purchases (All Time):", purch_all["total_purchases_formatted"], f"({purch_all['count']} bills)")
for r in purch_all["formatted_records"][:3]:
    print("   ", r)

# 3. Purchases for vendor 'muthu'
purch_muthu = business_tools.get_purchase_summary(tenant_id, vendor_name="muthu")
print("\n3. Purchases for 'muthu':", purch_muthu["total_purchases_formatted"], f"({purch_muthu['count']} bills)")

# 4. Receivables
rec = business_tools.get_receivables_summary(tenant_id)
print("\n4. Receivables:", rec["total_receivable_formatted"], f"({rec['count']} items)")
for r in rec["formatted_records"][:3]:
    print("   ", r)

# 5. Payables
pay = business_tools.get_payables_summary(tenant_id)
print("\n5. Payables:", pay["total_payable_formatted"], f"({pay['count']} items)")
for r in pay["formatted_records"][:3]:
    print("   ", r)

# 6. Inventory
inv = business_tools.get_inventory_summary(tenant_id)
print("\n6. Inventory:", f"{inv['total_items']} items, Valuation: {inv['total_valuation_formatted']}, Low stock: {inv['low_stock_count']}")
for r in inv["formatted_records"][:3]:
    print("   ", r)

# 7. Customers
cust = business_tools.get_customers_summary(tenant_id)
print("\n7. Customers:", f"{cust['count']} customers found")
for r in cust["formatted_records"][:3]:
    print("   ", r)

# 8. Suppliers
supp = business_tools.get_suppliers_summary(tenant_id)
print("\n8. Suppliers:", f"{supp['count']} suppliers found")
for r in supp["formatted_records"][:3]:
    print("   ", r)

# 9. GST Summary
gst = business_tools.get_gst_summary(tenant_id)
print("\n9. GST Summary: Output=", gst["total_output_gst_formatted"], "Input=", gst["total_input_gst_formatted"], "Net Liability=", gst["net_liability_formatted"])

# 10. Ledger / Cash & Bank
bank = business_tools.get_ledger_balances(tenant_id, group_filter="bank")
print("\n10. Bank Balances:", bank["total_balance_formatted"], f"({bank['count']} accounts)")
for r in bank["formatted_records"][:3]:
    print("   ", r)

# 11. Profit & Loss
pnl = business_tools.get_profit_loss_summary(tenant_id)
print("\n11. Profit & Loss: Sales=", pnl["total_sales_formatted"], "Expenses=", pnl["total_expenses_formatted"], "Net Profit=", pnl["net_profit_formatted"])
