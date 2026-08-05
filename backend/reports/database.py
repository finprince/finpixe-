"""
Reports Database Layer - Pure Data Access
NO business logic, NO RBAC, NO tenant validation.
Only database queries accepting tenant_id as parameter.
"""
import logging
from django.db.models import Sum, Q
from accounting.models import Voucher, JournalEntry
from inventory.models import InventoryStockItem, StockMovement
logger = logging.getLogger('reports.database')

def get_vouchers_for_daybook(tenant_id, start_date=None, end_date=None):
    """Get all vouchers for day book report."""
    vouchers = Voucher.objects.filter(tenant_id=tenant_id)
    if start_date:
        vouchers = vouchers.filter(date__gte=start_date)
    if end_date:
        vouchers = vouchers.filter(date__lte=end_date)
    return vouchers.order_by('date', 'id')

def get_vouchers_for_ledger(tenant_id, ledger_name, start_date=None, end_date=None):
    """Get all vouchers involving a specific ledger."""
    vouchers = Voucher.objects.filter(tenant_id=tenant_id)
    if start_date:
        vouchers = vouchers.filter(date__gte=start_date)
    if end_date:
        vouchers = vouchers.filter(date__lte=end_date)
    q_party = Q(party=ledger_name)
    q_account = Q(account=ledger_name)
    q_contra = Q(from_account=ledger_name) | Q(to_account=ledger_name)
    from django.db.models import Exists, OuterRef
    journal_vouchers = JournalEntry.objects.filter(Q(ledger_name=ledger_name) | Q(ledger__name=ledger_name), tenant_id=tenant_id, voucher_id=OuterRef('id'))
    return vouchers.filter(q_party | q_account | q_contra | Exists(journal_vouchers)).distinct().order_by('date', 'id')

def get_trial_balance_data(tenant_id, start_date=None, end_date=None):
    """Get aggregated ledger balances for trial balance with date filtering.
    Groups by ledger FK first, then falls back to ledger_name for unlinked entries.
    """
    from django.db.models import Value
    from django.db.models.functions import Coalesce
    entries = JournalEntry.objects.filter(tenant_id=tenant_id)
    if start_date:
        entries = entries.filter(transaction_date__gte=start_date)
    if end_date:
        entries = entries.filter(transaction_date__lte=end_date)
    from collections import defaultdict
    raw = entries.values('ledger_id', 'ledger__name', 'ledger_name').annotate(total_debit=Sum('debit'), total_credit=Sum('credit'))
    merged = defaultdict(lambda: {'total_debit': 0, 'total_credit': 0})
    for item in raw:
        name = item['ledger__name'] or item['ledger_name'] or '(Unknown)'
        merged[name]['total_debit'] += float(item['total_debit'] or 0)
        merged[name]['total_credit'] += float(item['total_credit'] or 0)
    return [{'ledger__name': name, 'total_debit': vals['total_debit'], 'total_credit': vals['total_credit']} for name, vals in sorted(merged.items())]

def get_ledger_balances(tenant_id, as_of_date=None):
    """Get all ledger balances as of a specific date."""
    entries = JournalEntry.objects.filter(tenant_id=tenant_id)
    if as_of_date:
        entries = entries.filter(transaction_date__lte=as_of_date)
    return entries.values('ledger__id', 'ledger__name', 'ledger__category', 'ledger__group', 'ledger__opening_balance', 'ledger__opening_balance_type').annotate(total_debit=Sum('debit'), total_credit=Sum('credit'))

def get_stock_items(tenant_id):
    """Get all stock items for stock summary."""
    return InventoryStockItem.objects.filter(tenant_id=tenant_id)

def get_stock_movements(tenant_id, start_date=None, end_date=None):
    """Get stock movements for stock summary."""
    movements = StockMovement.objects.filter(tenant_id=tenant_id)
    if start_date:
        movements = movements.filter(date__gte=start_date)
    if end_date:
        movements = movements.filter(date__lte=end_date)
    return movements.order_by('date')