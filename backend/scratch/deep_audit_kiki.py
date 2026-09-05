"""
Deep Validation and Accounting Accuracy Audit Script
====================================================
Runs comprehensive 3-way comparisons:
  [1] Kiki Tools Engine
  [2] Existing ERP Logic (reports_views / reports.flow)
  [3] Direct MySQL Ground Truth Query
"""
import os
import sys
import datetime
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.db import connection
from core.kiki.tools.business_tools import business_tools, format_inr
from core.kiki.tools.date_resolver import date_resolver
from core.kiki.kernel import ai_kernel
from core.kiki.security.tenant_guard import tenant_guard
from core.kiki.exceptions import KikiTenantSecurityException
from core.models import Tenant, MasterUser

from django.contrib.auth.models import AnonymousUser

# Test Tenant
TENANT_ID = "2eda0ac6-6af2-493e-8792-bc973fe946b7"

class MockUser:
    def __init__(self, tenant_id=TENANT_ID, user_id="audit_user", role="Admin"):
        self.is_authenticated = True
        self.tenant_id = tenant_id
        self.id = user_id
        self.role = role
        self.company_id = tenant_id

class MockRequest:
    def __init__(self, user, tenant_id=TENANT_ID, headers=None):
        self.user = user
        self.tenant_id = tenant_id
        self.META = headers or {"HTTP_X_TENANT_ID": tenant_id}

print("=" * 90)
print("KIKI AGENT DEEP VALIDATION & ACCOUNTING ACCURACY AUDIT")
print(f"Target Tenant: {TENANT_ID}")
print("=" * 90)

# ── 1. AUTHENTICATION & TENANT ISOLATION AUDIT ────────────────────────────────
print("\n[SECTION 2] AUTHENTICATION & TENANT ISOLATION AUDIT")
print("-" * 90)

# Test A: Authenticated User Tenant A
try:
    user_a = MockUser(tenant_id=TENANT_ID)
    req_a = MockRequest(user_a, tenant_id=TENANT_ID)
    ctx_a = tenant_guard.extract_context(user_a, request=req_a)
    print(f"Test A (Auth User Tenant A): SUCCESS -> resolved tenant_id = '{ctx_a['tenant_id']}', is_anonymous = {ctx_a['is_anonymous']}")
except Exception as e:
    print(f"Test A FAILED: {e}")

# Test B: Attempt to spoof Tenant B with X-Tenant-ID header when user belongs to Tenant A
try:
    user_a = MockUser(tenant_id=TENANT_ID)
    req_b_spoof = MockRequest(user_a, tenant_id="tenant-b-spoofed-id", headers={"HTTP_X_TENANT_ID": "tenant-b-spoofed-id"})
    ctx_b = tenant_guard.extract_context(user_a, request=req_b_spoof)
    print(f"Test B (Tenant B Spoof check): Resolved tenant_id = '{ctx_b['tenant_id']}'")
    # Note: If user_a has tenant_id = TENANT_ID, let's check if req_tenant overrode it or user tenant was enforced
except Exception as e:
    print(f"Test B Result: {e}")

# Test C: Unauthenticated Request
try:
    anon_user = AnonymousUser()
    req_anon = MockRequest(anon_user, tenant_id=None, headers={})
    ctx_anon = tenant_guard.extract_context(anon_user, request=req_anon)
    print(f"Test C (Unauthenticated Request): is_anonymous = {ctx_anon.get('is_anonymous')}, resolved tenant_id = '{ctx_anon.get('tenant_id')}'")
except Exception as e:
    print(f"Test C (Unauthenticated fail-closed): Expected exception -> {e}")

# ── 2. SALES 3-WAY COMPARISON ─────────────────────────────────────────────────
print("\n[SECTION 3] SALES 3-WAY COMPARISON")
print("-" * 90)

# 2.1 Kiki Sales
kiki_sales = business_tools.get_sales_summary(TENANT_ID)

# 2.2 Direct MySQL Calculation
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(total), 0), COALESCE(SUM(total_taxable_amount), 0),
               COALESCE(SUM(total_cgst), 0), COALESCE(SUM(total_sgst), 0), COALESCE(SUM(total_igst), 0)
        FROM vouchers
        WHERE tenant_id = %s AND LOWER(type) = 'sales'
    """, [TENANT_ID])
    db_sales = cursor.fetchone()

# 2.3 Existing ERP Voucher Extraction
try:
    from accounting.models import Voucher
    erp_vouchers = list(Voucher.objects.filter(tenant_id=TENANT_ID, type='sales'))
    erp_sales_total = sum(float(getattr(v, 'total', 0) or 0) for v in erp_vouchers)
    erp_sales_count = len(erp_vouchers)
except Exception as e:
    erp_sales_total = f"ERP Query Error: {e}"
    erp_sales_count = 0

print(f"Total Sales Comparison:")
print(f"  - Kiki Tools:      Count={kiki_sales['count']}, Total={kiki_sales['total_sales_formatted']}, Taxable={kiki_sales['total_taxable_formatted']}, Tax={kiki_sales['total_tax_formatted']}")
print(f"  - Direct MySQL:    Count={db_sales[0]}, Total={format_inr(db_sales[1])}, Taxable={format_inr(db_sales[2])}, CGST={format_inr(db_sales[3])}, SGST={format_inr(db_sales[4])}, IGST={format_inr(db_sales[5])}")
print(f"  - Existing ERP:    Count={erp_sales_count}, Total={format_inr(erp_sales_total)}")

# ── 3. PURCHASES 3-WAY COMPARISON ─────────────────────────────────────────────
print("\n[SECTION 4] PURCHASES 3-WAY COMPARISON")
print("-" * 90)

kiki_purch = business_tools.get_purchase_summary(TENANT_ID)
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(total), 0), COALESCE(SUM(total_taxable_amount), 0),
               COALESCE(SUM(total_cgst + total_sgst + total_igst), 0)
        FROM vouchers
        WHERE tenant_id = %s AND LOWER(type) = 'purchase'
    """, [TENANT_ID])
    db_purch = cursor.fetchone()

try:
    from accounting.models import Voucher
    erp_p_vouchers = list(Voucher.objects.filter(tenant_id=TENANT_ID, type='purchase'))
    erp_purch_total = sum(float(getattr(v, 'total', 0) or 0) for v in erp_p_vouchers)
    erp_purch_count = len(erp_p_vouchers)
except Exception as e:
    erp_purch_total = f"ERP Query Error: {e}"
    erp_purch_count = 0


print(f"Total Purchases Comparison:")
print(f"  - Kiki Tools:      Count={kiki_purch['count']}, Total={kiki_purch['total_purchases_formatted']}, Taxable={kiki_purch['total_taxable_formatted']}, Tax={kiki_purch['total_tax_formatted']}")
print(f"  - Direct MySQL:    Count={db_purch[0]}, Total={format_inr(db_purch[1])}, Taxable={format_inr(db_purch[2])}, Tax={format_inr(db_purch[3])}")
print(f"  - Existing ERP:    Count={erp_purch_count}, Total={format_inr(erp_purch_total)}")

# ── 4. RECEIVABLES & OUTSTANDING DUES DEEP DIVE ───────────────────────────────
print("\n[SECTION 5] RECEIVABLES & CUSTOMER OUTSTANDING DEEP DIVE")
print("-" * 90)

kiki_rec = business_tools.get_receivables_summary(TENANT_ID)

# Inspect advance_allocation for receivables
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(original_amount), 0), COALESCE(SUM(allocated_amount), 0)
        FROM advance_allocation
        WHERE tenant_id = %s AND party_customer_id IS NOT NULL
    """, [TENANT_ID])
    adv_rec = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(original_amount), 0), COALESCE(SUM(allocated_amount), 0)
        FROM pending_transaction
        WHERE tenant_id = %s AND party_customer_id IS NOT NULL
    """, [TENANT_ID])
    pend_rec = cursor.fetchone()

    # Inspect master_ledgers Sundry Debtors
    cursor.execute("""
        SELECT l.id, l.ledger_type, l.ledger, l.opening_balance, l.opening_balance_type,
               COALESCE(SUM(e.debit), 0) as dr, COALESCE(SUM(e.credit), 0) as cr
        FROM master_ledgers l
        LEFT JOIN entries e ON e.ledger_id = l.id
        WHERE l.tenant_id = %s AND (LOWER(l.group) LIKE '%%debtor%%' OR LOWER(l.category) = 'asset')
        GROUP BY l.id, l.ledger_type, l.ledger, l.opening_balance, l.opening_balance_type
    """, [TENANT_ID])
    debtor_ledgers = cursor.fetchall()

    # Inspect sales vouchers payment status
    cursor.execute("""
        SELECT id, voucher_number, invoice_no, party, total
        FROM vouchers
        WHERE tenant_id = %s AND LOWER(type) = 'sales'
    """, [TENANT_ID])
    sales_vouchers = cursor.fetchall()


print(f"Receivables Analysis:")
print(f"  - Kiki Tool Result:            Count={kiki_rec['count']}, Total={kiki_rec['total_receivable_formatted']}")
print(f"  - advance_allocation (Cust):   Count={adv_rec[0]}, Original={format_inr(adv_rec[1])}, Allocated={format_inr(adv_rec[2])}")
print(f"  - pending_transaction (Cust):  Count={pend_rec[0]}, Amount={format_inr(pend_rec[1])}, Paid={format_inr(pend_rec[2])}")
print(f"  - Sales Vouchers in DB:        Count={len(sales_vouchers)}")
for sv in sales_vouchers:
    print(f"      Voucher ID={sv[0]}, Number={sv[1]}, InvoiceNo={sv[2]}, Party={sv[3]}, Total={format_inr(sv[4])}")

print(f"  - Sundry Debtors Ledgers:      Count={len(debtor_ledgers)}")
for dl in debtor_ledgers:
    ob = float(dl[3] or 0)
    dr = float(dl[5] or 0)
    cr = float(dl[6] or 0)
    bal = ob + dr - cr
    print(f"      Ledger ID={dl[0]}, Name={dl[1]}, OB={ob}, Dr={dr}, Cr={cr} -> Net Balance={format_inr(bal)}")

# ── 5. PAYABLES & SUPPLIER DUES DEEP DIVE ─────────────────────────────────────
print("\n[SECTION 6] PAYABLES & SUPPLIER OUTSTANDING DEEP DIVE")
print("-" * 90)

kiki_pay = business_tools.get_payables_summary(TENANT_ID)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(original_amount), 0), COALESCE(SUM(allocated_amount), 0)
        FROM advance_allocation
        WHERE tenant_id = %s AND party_vendor_id IS NOT NULL
    """, [TENANT_ID])
    adv_pay = cursor.fetchone()

    cursor.execute("""
        SELECT l.id, l.ledger_type, l.ledger, l.opening_balance, l.opening_balance_type,
               COALESCE(SUM(e.debit), 0) as dr, COALESCE(SUM(e.credit), 0) as cr
        FROM master_ledgers l
        LEFT JOIN entries e ON e.ledger_id = l.id
        WHERE l.tenant_id = %s AND (LOWER(l.group) LIKE '%%creditor%%' OR LOWER(l.category) = 'liability')
        GROUP BY l.id, l.ledger_type, l.ledger, l.opening_balance, l.opening_balance_type
        HAVING (COALESCE(SUM(e.credit) - SUM(e.debit), 0) + COALESCE(l.opening_balance, 0)) > 0
    """, [TENANT_ID])
    creditor_ledgers = cursor.fetchall()
    tot_cred_bal = sum(float(cl[3] or 0) + float(cl[6] or 0) - float(cl[5] or 0) for cl in creditor_ledgers)

print(f"Payables Analysis:")
print(f"  - Kiki Tool Result:            Count={kiki_pay['count']}, Total={kiki_pay['total_payable_formatted']}")
print(f"  - advance_allocation (Vend):   Count={adv_pay[0]}, Original={format_inr(adv_pay[1])}, Allocated={format_inr(adv_pay[2])}")
print(f"  - Sundry Creditors Ledgers:    Count={len(creditor_ledgers)}, Total Balance={format_inr(tot_cred_bal)}")

# ── 6. INVENTORY & STOCK VALUATION DEEP DIVE ──────────────────────────────────
print("\n[SECTION 7] INVENTORY & VALUATION DEEP DIVE")
print("-" * 90)

kiki_inv = business_tools.get_inventory_summary(TENANT_ID)

with connection.cursor() as cursor:
    # 1. inventory_master_inventoryitems
    cursor.execute("""
        SELECT COUNT(*), 
               COALESCE(SUM(opening_stock), 0),
               COALESCE(SUM(rate * opening_stock), 0),
               COALESCE(SUM(CASE WHEN opening_stock <= reorder_level AND reorder_level > 0 THEN 1 ELSE 0 END), 0)
        FROM inventory_master_inventoryitems
        WHERE tenant_id = %s AND is_active = 1
    """, [TENANT_ID])
    inv_master = cursor.fetchone()

    # 2. inventory_stock_items
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(current_balance), 0), COALESCE(SUM(current_balance * rate), 0)
        FROM inventory_stock_items
        WHERE tenant_id = %s
    """, [TENANT_ID])
    inv_stock = cursor.fetchone()

    # Sample items with rate and opening stock
    cursor.execute("""
        SELECT item_code, item_name, rate, opening_stock, reorder_level
        FROM inventory_master_inventoryitems
        WHERE tenant_id = %s AND is_active = 1
        LIMIT 10
    """, [TENANT_ID])
    sample_items = cursor.fetchall()

print(f"Inventory Analysis:")
print(f"  - Kiki Tool Result:            Items={kiki_inv['total_items']}, Total Qty={kiki_inv['total_quantity']}, Valuation={kiki_inv['total_valuation_formatted']}, Low Stock={kiki_inv['low_stock_count']}")
print(f"  - inventoryitems Table:        Items={inv_master[0]}, Total Qty={inv_master[1]}, Valuation={format_inr(inv_master[2])}, Low Stock={inv_master[3]}")
print(f"  - inventory_stock_items Table: Items={inv_stock[0]}, Total Qty={inv_stock[1]}, Valuation={format_inr(inv_stock[2])}")
print(f"  - Sample Items (Rate vs Opening Stock):")
for it in sample_items:
    print(f"      Code={it[0]}, Name={it[1][:30]}, Rate={it[2]}, OpeningStock={it[3]}, ReorderLevel={it[4]}")

# ── 7. CASH AND BANK BALANCES DEEP DIVE ───────────────────────────────────────
print("\n[SECTION 8] CASH AND BANK BALANCES DEEP DIVE")
print("-" * 90)

kiki_cash = business_tools.get_ledger_balances(TENANT_ID, group_filter="cash")
kiki_bank = business_tools.get_ledger_balances(TENANT_ID, group_filter="bank")

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, ledger_type, ledger, `group`, category, opening_balance, opening_balance_type
        FROM master_ledgers
        WHERE tenant_id = %s AND (LOWER(`group`) LIKE '%%cash%%' OR LOWER(`group`) LIKE '%%bank%%' OR LOWER(ledger_type) LIKE '%%cash%%' OR LOWER(ledger_type) LIKE '%%bank%%')
    """, [TENANT_ID])
    cash_bank_ledgers = cursor.fetchall()

print(f"Cash & Bank Ledgers in DB (Count={len(cash_bank_ledgers)}):")
for cb in cash_bank_ledgers:
    print(f"  - ID={cb[0]}, Name='{cb[1]}', Group='{cb[3]}', Category='{cb[4]}', OB={cb[5]} ({cb[6]})")
print(f"Kiki Cash Balance Result: {kiki_cash['total_balance_formatted']} ({kiki_cash['count']} accounts)")
print(f"Kiki Bank Balance Result: {kiki_bank['total_balance_formatted']} ({kiki_bank['count']} accounts)")

# ── 8. PROFIT & LOSS COMPARISON WITH ERP ──────────────────────────────────────
print("\n[SECTION 9] PROFIT & LOSS COMPARISON WITH ERP")
print("-" * 90)

kiki_pnl = business_tools.get_profit_loss_summary(TENANT_ID)

try:
    from reports.flow import generate_profit_and_loss_data
    erp_pnl = generate_profit_and_loss_data(user_a)
    erp_net_profit = erp_pnl.get("net_profit", erp_pnl.get("net_profit_or_loss", 0.0))
except Exception as e:
    erp_pnl = f"Error in generate_profit_and_loss_data: {e}"
    erp_net_profit = "N/A"

print(f"Profit & Loss Analysis:")
print(f"  - Kiki Tool Result:            Sales={kiki_pnl['total_sales_formatted']}, Purchases={kiki_pnl['total_purchases_formatted']}, Expenses={kiki_pnl['other_expenses_formatted']}, Net Profit={kiki_pnl['net_profit_formatted']}")
print(f"  - ERP generate_profit_and_loss: {erp_pnl}")

# ── 9. GST CALCULATION AUDIT ──────────────────────────────────────────────────
print("\n[SECTION 10] GST CALCULATION AUDIT")
print("-" * 90)

kiki_gst = business_tools.get_gst_summary(TENANT_ID)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT COALESCE(SUM(total_taxable_amount), 0), COALESCE(SUM(total_cgst), 0), COALESCE(SUM(total_sgst), 0), COALESCE(SUM(total_igst), 0)
        FROM vouchers
        WHERE tenant_id = %s AND LOWER(type) = 'sales'
    """, [TENANT_ID])
    db_out_gst = cursor.fetchone()

    cursor.execute("""
        SELECT COALESCE(SUM(total_taxable_amount), 0), COALESCE(SUM(total_cgst), 0), COALESCE(SUM(total_sgst), 0), COALESCE(SUM(total_igst), 0)
        FROM vouchers
        WHERE tenant_id = %s AND LOWER(type) = 'purchase'
    """, [TENANT_ID])
    db_in_gst = cursor.fetchone()

print(f"GST Analysis:")
print(f"  - Kiki Output GST: {kiki_gst['total_output_gst_formatted']} (CGST={kiki_gst['output_cgst']}, SGST={kiki_gst['output_sgst']}, IGST={kiki_gst['output_igst']})")
print(f"  - DB Output GST:   Taxable={format_inr(db_out_gst[0])}, CGST={format_inr(db_out_gst[1])}, SGST={format_inr(db_out_gst[2])}, IGST={format_inr(db_out_gst[3])}")
print(f"  - Kiki Input ITC:  {kiki_gst['total_input_gst_formatted']} (CGST={kiki_gst['input_cgst']}, SGST={kiki_gst['input_sgst']}, IGST={kiki_gst['input_igst']})")
print(f"  - DB Input ITC:    Taxable={format_inr(db_in_gst[0])}, CGST={format_inr(db_in_gst[1])}, SGST={format_inr(db_in_gst[2])}, IGST={format_inr(db_in_gst[3])}")
print(f"  - Net Liability:   {kiki_gst['net_liability_formatted']}")

print("\n" + "=" * 90)
print("AUDIT EXECUTION COMPLETE")
print("=" * 90 + "\n")
