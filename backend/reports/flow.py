"""
Reports Flow Layer - Business Logic + Branch Validation
This is the ONLY place for business decisions in the Reports module.
Every function MUST start with tenant validation.
"""
import logging
from core.tenant import get_user_tenant_id
from . import database as db
logger = logging.getLogger('reports.flow')

def generate_daybook_data(user, start_date=None, end_date=None):
    """
    Generate day book report data.
    """
    tenant_id = get_user_tenant_id(user)
    if not tenant_id:
        raise PermissionError('User has no associated tenant')
    return db.get_vouchers_for_daybook(tenant_id, start_date, end_date)

def generate_ledger_report_data(user, ledger_name, start_date=None, end_date=None):
    """
    Generate ledger report data.
    """
    tenant_id = get_user_tenant_id(user)
    if not tenant_id:
        raise PermissionError('User has no associated tenant')
    if not ledger_name:
        raise ValueError('Ledger name is required')
    return db.get_vouchers_for_ledger(tenant_id, ledger_name, start_date, end_date)

def generate_trial_balance_data(user, start_date=None, end_date=None):
    """
    Generate trial balance report data with date filters.
    """
    tenant_id = get_user_tenant_id(user)
    if not tenant_id:
        raise PermissionError('User has no associated tenant')
    ledger_balances = db.get_trial_balance_data(tenant_id, start_date, end_date)
    result = []
    for item in ledger_balances:
        debit = item['total_debit'] or 0
        credit = item['total_credit'] or 0
        net_debit = 0
        net_credit = 0
        if debit > credit:
            net_debit = debit - credit
        elif credit > debit:
            net_credit = credit - debit
        if net_debit == 0 and net_credit == 0:
            continue
        result.append({'ledger': item['ledger__name'], 'debit': float(net_debit), 'credit': float(net_credit)})
    return result

def generate_balance_sheet_data(user, end_date=None):
    """
    Generate balance sheet report data as of a specific date.
    Reuses existing ledger classification and authoritative closing calculations.
    """
    tenant_id = get_user_tenant_id(user)
    if not tenant_id:
        raise PermissionError('User has no associated tenant')
    ledger_balances = db.get_ledger_balances(tenant_id, end_date)
    assets = {'fixed_assets': [], 'current_assets': [], 'total_fixed_assets': 0.0, 'total_current_assets': 0.0, 'total': 0.0}
    liabilities = {'long_term_liabilities': [], 'current_liabilities': [], 'total_long_term': 0.0, 'total_current': 0.0, 'total': 0.0}
    capital = {'capital_account': [], 'total_capital': 0.0, 'retained_earnings': 0.0, 'total': 0.0}
    retained_earnings = 0.0
    for item in ledger_balances:
        name = item['ledger__name']
        debit = float(item['total_debit'] or 0)
        credit = float(item['total_credit'] or 0)
        ob = float(item['ledger__opening_balance'] or 0)
        ob_type = str(item['ledger__opening_balance_type'] or 'Dr').strip().lower()
        is_debit = ob_type in ('debit', 'dr')
        category = item['ledger__category']
        group = item['ledger__group'] or ''
        if category in {'Asset', 'Expenditure', 'Expense'}:
            balance = debit - credit
            balance += ob if is_debit else -ob
        else:
            balance = credit - debit
            balance += ob if not is_debit else -ob
        if abs(balance) < 0.001:
            continue
        if category == 'Asset':
            if 'fixed' in group.lower():
                assets['fixed_assets'].append({'name': name, 'balance': balance})
                assets['total_fixed_assets'] += balance
            else:
                assets['current_assets'].append({'name': name, 'balance': balance})
                assets['total_current_assets'] += balance
        elif category == 'Liability':
            if 'current' in group.lower() or 'creditor' in group.lower() or 'tax' in group.lower():
                liabilities['current_liabilities'].append({'name': name, 'balance': balance})
                liabilities['total_current'] += balance
            else:
                liabilities['long_term_liabilities'].append({'name': name, 'balance': balance})
                liabilities['total_long_term'] += balance
        elif category == 'Capital':
            capital['capital_account'].append({'name': name, 'balance': balance})
            capital['total_capital'] += balance
        elif category in {'Revenue', 'Income'}:
            retained_earnings += balance
        elif category in {'Expense', 'Expenditure'}:
            retained_earnings -= balance
    assets['total'] = assets['total_fixed_assets'] + assets['total_current_assets']
    liabilities['total'] = liabilities['total_long_term'] + liabilities['total_current']
    capital['retained_earnings'] = retained_earnings
    capital['total'] = capital['total_capital'] + capital['retained_earnings']
    return {'assets': assets, 'liabilities': liabilities, 'capital': capital, 'is_balanced': abs(assets['total'] - (liabilities['total'] + capital['total'])) < 0.01}

def generate_stock_summary_data(user, start_date=None, end_date=None):
    """
    Generate stock summary report data.
    """
    tenant_id = get_user_tenant_id(user)
    if not tenant_id:
        raise PermissionError('User has no associated tenant')
    stock_items = db.get_stock_items(tenant_id)
    movements = db.get_stock_movements(tenant_id, start_date, end_date)
    return {'stock_items': stock_items, 'movements': movements}