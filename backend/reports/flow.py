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
    return db.get_trial_balance_data(tenant_id, start_date, end_date)

def _get_trade_payable_bucket_type(v_cat_str: str) -> str:
    """
    Returns 'OTHER_CURRENT_LIABILITY' if the vendor/ledger category belongs to:
    Packing Material, Fixed Assets, Capital Goods, Services, Work in Progress.
    Returns 'TRADE_PAYABLE' if the category belongs to:
    Raw Material, Stores and Spares, Stock-in Trade, Consumables, Jobwork (or unassigned/general).
    """
    if not v_cat_str:
        return 'TRADE_PAYABLE'
    
    c = v_cat_str.lower().strip()
    
    # Categories that MUST go to Other Current Liabilities (even if MSME)
    other_liab_keys = [
        'packing material', 'packing materials', 'packing',
        'fixed asset', 'fixed assets',
        'capital good', 'capital goods',
        'service', 'services',
        'work in progress', 'wip', 'work-in-progress'
    ]
    if any(k in c for k in other_liab_keys):
        return 'OTHER_CURRENT_LIABILITY'

def _get_main_category(cat_str: str) -> str:
    """
    Strips sub-group hierarchy breadcrumbs (e.g., 'RAW MATERIAL > IMPORT > ONE' -> 'RAW MATERIAL')
    and returns the main top-level category name.
    """
    if not cat_str:
        return 'General'
    s = str(cat_str).strip()
    if '>' in s:
        s = s.split('>')[0].strip()
    elif '/' in s and not ('work in progress' in s.lower() or 'wip' in s.lower()):
        parts = s.split('/')
        if len(parts) > 1 and parts[0].strip():
            s = parts[0].strip()
    if not s or s.lower() in {'-', 'none', 'null'}:
        return 'General'
    return s

def generate_balance_sheet_data(user, end_date=None):
    """
    Generate balance sheet report data as of a specific date.
    Reuses existing ledger classification and authoritative closing calculations.
    Supports both standard format and Non-Corporate Schedule III Vertical format.
    """
    tenant_id = get_user_tenant_id(user)
    if not tenant_id:
        raise PermissionError('User has no associated tenant')
    
    from core.models import Tenant
    from accounting.models import MasterLedger
    
    tenant = Tenant.objects.filter(id=tenant_id).first()
    business_type = (tenant.business_type if tenant else '') or ''
    company_name = (tenant.name if tenant else '') or ''

    # Get master ledgers to check subgroup details
    ml_qs = MasterLedger.objects.filter(tenant_id=tenant_id)
    ml_map = {l.name.lower().strip(): l for l in ml_qs if l.name}

    # Fetch ledgers associated with MSME Vendors and Customers
    msme_ledgers = set()
    try:
        from vendors.models import VendorMasterBasicDetail
        msme_vendors = VendorMasterBasicDetail.objects.filter(
            tenant_id=tenant_id,
            tds_details__msme_udyam_no__isnull=False
        ).exclude(tds_details__msme_udyam_no__exact='').values_list('ledger__name', flat=True)
        for n in msme_vendors:
            if n:
                msme_ledgers.add(n.lower().strip())
    except Exception as e:
        logger.warning(f"Failed to fetch MSME vendor ledgers: {e}")

    try:
        from customerportal.models import CustomerMasterCustomerBasicDetails
        msme_customers = CustomerMasterCustomerBasicDetails.objects.filter(
            tenant_id=tenant_id,
            tds_details__msme_no__isnull=False
        ).exclude(tds_details__msme_no__exact='').values_list('ledger__name', flat=True)
        for n in msme_customers:
            if n:
                msme_ledgers.add(n.lower().strip())
    except Exception as e:
        logger.warning(f"Failed to fetch MSME customer ledgers: {e}")

    # Fetch vendor categories map for ledger categorization
    vendor_cat_map = {}
    try:
        from vendors.models import VendorMasterBasicDetail
        vb_qs = VendorMasterBasicDetail.objects.filter(tenant_id=tenant_id, is_deleted=False)
        for vb in vb_qs.select_related('ledger'):
            cat_val = _get_main_category(vb.vendor_category)
            if cat_val:
                if vb.ledger and vb.ledger.name:
                    vendor_cat_map[vb.ledger.name.lower().strip()] = cat_val
                if vb.vendor_name:
                    vendor_cat_map[vb.vendor_name.lower().strip()] = cat_val
    except Exception as e:
        logger.warning(f"Failed to fetch vendor categories: {e}")

    _, prev_ed = _calc_prev_period(None, end_date)
    ledger_balances = db.get_ledger_balances(tenant_id, end_date)
    prev_ledger_balances = db.get_ledger_balances(tenant_id, prev_ed)

    prev_balance_map = {}
    for item in prev_ledger_balances:
        p_name = item['ledger__name']
        if not p_name: continue
        p_debit = float(item['total_debit'] or 0)
        p_credit = float(item['total_credit'] or 0)
        p_ob = float(item['ledger__opening_balance'] or 0)
        p_ob_type = str(item['ledger__opening_balance_type'] or 'Dr').strip().lower()
        p_is_debit = p_ob_type in ('debit', 'dr')
        p_category = str(item['ledger__category'] or '').strip().upper()
        if p_category in {'ASSET', 'EXPENDITURE', 'EXPENSE'}:
            p_bal = p_debit - p_credit + (p_ob if p_is_debit else -p_ob)
        else:
            p_bal = p_credit - p_debit + (p_ob if not p_is_debit else -p_ob)
        prev_balance_map[p_name.lower().strip()] = p_bal

    assets = {'fixed_assets': [], 'current_assets': [], 'total_fixed_assets': 0.0, 'total_current_assets': 0.0, 'total': 0.0}
    liabilities = {'long_term_liabilities': [], 'current_liabilities': [], 'total_long_term': 0.0, 'total_current': 0.0, 'total': 0.0}
    capital = {'capital_account': [], 'total_capital': 0.0, 'retained_earnings': 0.0, 'total': 0.0}
    retained_earnings = 0.0
    prev_retained_earnings = 0.0

    # Non-Corporate Vertical Buckets
    nc_owners_capital = []
    nc_reserves_surplus = []

    nc_long_term_borrowings = []
    nc_deferred_tax_liab = []
    nc_other_long_term_liab = []
    nc_long_term_provisions = []

    nc_short_term_borrowings = []
    nc_trade_payables_msme = []
    nc_trade_payables_other = []
    nc_other_current_liab = []
    nc_short_term_provisions = []

    nc_ppe = []
    nc_intangibles = []
    nc_cwip = []
    nc_intangible_dev = []
    nc_non_current_inv = []
    nc_deferred_tax_assets = []
    nc_long_term_loans_adv = []
    nc_other_non_current_assets = []

    nc_current_inv = []
    nc_inventories = []
    nc_trade_receivables = []
    nc_cash_bank = []
    nc_short_term_loans_adv = []
    nc_other_current_assets = []

    for item in ledger_balances:
        name = item['ledger__name']
        if not name:
            continue
        debit = float(item['total_debit'] or 0)
        credit = float(item['total_credit'] or 0)
        ob = float(item['ledger__opening_balance'] or 0)
        ob_type = str(item['ledger__opening_balance_type'] or 'Dr').strip().lower()
        is_debit = ob_type in ('debit', 'dr')
        category = item['ledger__category']
        group = item['ledger__group'] or ''
        
        ml = ml_map.get(name.lower().strip())
        sg1 = getattr(ml, 'sub_group_1', '') or ''
        sg2 = getattr(ml, 'sub_group_2', '') or ''
        sg3 = getattr(ml, 'sub_group_3', '') or ''
        maj = getattr(ml, 'major_group', '') or ''

        text = f"{name} {group} {sg1} {sg2} {sg3} {maj}".lower()

        cat_upper = str(category or '').strip().upper()

        if cat_upper in {'ASSET', 'EXPENDITURE', 'EXPENSE'}:
            balance = debit - credit
            balance += ob if is_debit else -ob
        else:
            balance = credit - debit
            balance += ob if not is_debit else -ob

        prev_balance = prev_balance_map.get(name.lower().strip(), 0.0)

        if abs(balance) < 0.001 and abs(prev_balance) < 0.001:
            continue

        v_cat = vendor_cat_map.get(name.lower().strip())
        if not v_cat:
            v_cat = (sg1 or sg2 or sg3 or group or maj or '').strip()
        v_cat = _get_main_category(v_cat)

        item_entry = {'name': name, 'balance': balance, 'prev_balance': prev_balance, 'category': v_cat}

        if cat_upper in {'ASSET', 'ASSETS'}:
            if 'fixed' in group.lower():
                assets['fixed_assets'].append(item_entry)
                assets['total_fixed_assets'] += balance
            else:
                assets['current_assets'].append(item_entry)
                assets['total_current_assets'] += balance

            # Non-Corporate Categorization
            if any(k in text for k in ['fixed', 'property', 'equipment', 'plant', 'intangible', 'non-current', 'non current', 'long term', 'long-term']):
                if 'intangible asset under development' in text or 'intangible development' in text:
                    nc_intangible_dev.append(item_entry)
                elif 'capital work in progress' in text or 'cwip' in text or 'work in progress' in text:
                    nc_cwip.append(item_entry)
                elif 'intangible' in text or 'software' in text or 'patent' in text or 'trademark' in text:
                    nc_intangibles.append(item_entry)
                elif 'investment' in text:
                    nc_non_current_inv.append(item_entry)
                elif 'deferred tax' in text:
                    nc_deferred_tax_assets.append(item_entry)
                elif 'loan' in text or 'advance' in text or 'deposit' in text:
                    nc_long_term_loans_adv.append(item_entry)
                elif 'fixed' in text or 'property' in text or 'equipment' in text or 'plant' in text or 'vehicle' in text or 'building' in text or 'computer' in text:
                    nc_ppe.append(item_entry)
                else:
                    nc_other_non_current_assets.append(item_entry)
            else:
                if 'investment' in text:
                    nc_current_inv.append(item_entry)
                elif 'inventory' in text or 'stock' in text:
                    nc_inventories.append(item_entry)
                elif 'debtor' in text or 'receivable' in text:
                    nc_trade_receivables.append(item_entry)
                elif 'cash' in text or 'bank' in text or 'cheque' in text:
                    nc_cash_bank.append(item_entry)
                elif 'loan' in text or 'advance' in text:
                    nc_short_term_loans_adv.append(item_entry)
                else:
                    nc_other_current_assets.append(item_entry)

        elif cat_upper in {'LIABILITY', 'LIABILITIES'}:
            if 'current' in group.lower() or 'creditor' in group.lower() or 'tax' in group.lower():
                liabilities['current_liabilities'].append(item_entry)
                liabilities['total_current'] += balance
            else:
                liabilities['long_term_liabilities'].append(item_entry)
                liabilities['total_long_term'] += balance

            # Non-Corporate Categorization
            if any(k in text for k in ['current', 'creditor', 'duty', 'tax', 'payable', 'overdraft', 'od', 'short term', 'short-term']):
                if 'overdraft' in text or 'od' in text or 'cash credit' in text or 'working capital' in text or ('borrowing' in text and 'short' in text):
                    nc_short_term_borrowings.append(item_entry)
                elif any(k in text for k in ['tax', 'tds', 'tcs', 'gst', 'duty', 'duties', 'statutory', 'vat']):
                    nc_other_current_liab.append(item_entry)
                elif 'creditor' in text or 'payable' in text or 'trade' in text:
                    bucket_type = _get_trade_payable_bucket_type(v_cat)
                    if bucket_type == 'OTHER_CURRENT_LIABILITY':
                        nc_other_current_liab.append(item_entry)
                    else:
                        if name.lower().strip() in msme_ledgers or 'msme' in text or 'micro' in text or 'small' in text:
                            nc_trade_payables_msme.append(item_entry)
                        else:
                            nc_trade_payables_other.append(item_entry)
                elif 'provision' in text:
                    nc_short_term_provisions.append(item_entry)
                else:
                    nc_other_current_liab.append(item_entry)
            else:
                if 'deferred tax' in text:
                    nc_deferred_tax_liab.append(item_entry)
                elif 'provision' in text:
                    nc_long_term_provisions.append(item_entry)
                elif 'borrowing' in text or 'loan' in text or 'term' in text:
                    nc_long_term_borrowings.append(item_entry)
                else:
                    nc_other_long_term_liab.append(item_entry)

        elif cat_upper in {'CAPITAL', "OWNERS' FUNDS", "OWNERS'  FUNDS", "NPO FUNDS", "EQUITY"}:
            capital['capital_account'].append(item_entry)
            capital['total_capital'] += balance

            if any(k in text for k in ['reserve', 'surplus', 'retained', 'profit', 'loss']):
                nc_reserves_surplus.append(item_entry)
            else:
                nc_owners_capital.append(item_entry)

        elif cat_upper in {'REVENUE', 'INCOME'}:
            retained_earnings += balance
            prev_retained_earnings += prev_balance
        elif cat_upper in {'EXPENSE', 'EXPENDITURE'}:
            retained_earnings -= balance
            prev_retained_earnings -= prev_balance

    assets['total'] = assets['total_fixed_assets'] + assets['total_current_assets']
    liabilities['total'] = liabilities['total_long_term'] + liabilities['total_current']
    capital['retained_earnings'] = retained_earnings
    capital['total'] = capital['total_capital'] + capital['retained_earnings']

    if retained_earnings != 0 or prev_retained_earnings != 0:
        nc_reserves_surplus.append({'name': 'Retained Earnings (Profit / Loss)', 'balance': retained_earnings, 'prev_balance': prev_retained_earnings})

    # Subtotals for Non-Corporate Structure
    nc_owners_funds_total = sum(x['balance'] for x in nc_owners_capital) + sum(x['balance'] for x in nc_reserves_surplus)
    nc_owners_funds_prev_total = sum(x.get('prev_balance', 0) for x in nc_owners_capital) + sum(x.get('prev_balance', 0) for x in nc_reserves_surplus)

    nc_non_current_liab_total = (
        sum(x['balance'] for x in nc_long_term_borrowings) +
        sum(x['balance'] for x in nc_deferred_tax_liab) +
        sum(x['balance'] for x in nc_other_long_term_liab) +
        sum(x['balance'] for x in nc_long_term_provisions)
    )
    nc_non_current_liab_prev_total = (
        sum(x.get('prev_balance', 0) for x in nc_long_term_borrowings) +
        sum(x.get('prev_balance', 0) for x in nc_deferred_tax_liab) +
        sum(x.get('prev_balance', 0) for x in nc_other_long_term_liab) +
        sum(x.get('prev_balance', 0) for x in nc_long_term_provisions)
    )

    nc_current_liab_total = (
        sum(x['balance'] for x in nc_short_term_borrowings) +
        sum(x['balance'] for x in nc_trade_payables_msme) +
        sum(x['balance'] for x in nc_trade_payables_other) +
        sum(x['balance'] for x in nc_other_current_liab) +
        sum(x['balance'] for x in nc_short_term_provisions)
    )
    nc_current_liab_prev_total = (
        sum(x.get('prev_balance', 0) for x in nc_short_term_borrowings) +
        sum(x.get('prev_balance', 0) for x in nc_trade_payables_msme) +
        sum(x.get('prev_balance', 0) for x in nc_trade_payables_other) +
        sum(x.get('prev_balance', 0) for x in nc_other_current_liab) +
        sum(x.get('prev_balance', 0) for x in nc_short_term_provisions)
    )

    nc_total_equity_liab = nc_owners_funds_total + nc_non_current_liab_total + nc_current_liab_total
    nc_total_equity_liab_prev = nc_owners_funds_prev_total + nc_non_current_liab_prev_total + nc_current_liab_prev_total

    nc_ppe_and_intangibles_total = (
        sum(x['balance'] for x in nc_ppe) +
        sum(x['balance'] for x in nc_intangibles) +
        sum(x['balance'] for x in nc_cwip) +
        sum(x['balance'] for x in nc_intangible_dev)
    )
    nc_ppe_and_intangibles_prev_total = (
        sum(x.get('prev_balance', 0) for x in nc_ppe) +
        sum(x.get('prev_balance', 0) for x in nc_intangibles) +
        sum(x.get('prev_balance', 0) for x in nc_cwip) +
        sum(x.get('prev_balance', 0) for x in nc_intangible_dev)
    )

    nc_non_current_assets_total = (
        nc_ppe_and_intangibles_total +
        sum(x['balance'] for x in nc_non_current_inv) +
        sum(x['balance'] for x in nc_deferred_tax_assets) +
        sum(x['balance'] for x in nc_long_term_loans_adv) +
        sum(x['balance'] for x in nc_other_non_current_assets)
    )
    nc_non_current_assets_prev_total = (
        nc_ppe_and_intangibles_prev_total +
        sum(x.get('prev_balance', 0) for x in nc_non_current_inv) +
        sum(x.get('prev_balance', 0) for x in nc_deferred_tax_assets) +
        sum(x.get('prev_balance', 0) for x in nc_long_term_loans_adv) +
        sum(x.get('prev_balance', 0) for x in nc_other_non_current_assets)
    )

    nc_current_assets_total = (
        sum(x['balance'] for x in nc_current_inv) +
        sum(x['balance'] for x in nc_inventories) +
        sum(x['balance'] for x in nc_trade_receivables) +
        sum(x['balance'] for x in nc_cash_bank) +
        sum(x['balance'] for x in nc_short_term_loans_adv) +
        sum(x['balance'] for x in nc_other_current_assets)
    )
    nc_current_assets_prev_total = (
        sum(x.get('prev_balance', 0) for x in nc_current_inv) +
        sum(x.get('prev_balance', 0) for x in nc_inventories) +
        sum(x.get('prev_balance', 0) for x in nc_trade_receivables) +
        sum(x.get('prev_balance', 0) for x in nc_cash_bank) +
        sum(x.get('prev_balance', 0) for x in nc_short_term_loans_adv) +
        sum(x.get('prev_balance', 0) for x in nc_other_current_assets)
    )

    nc_total_assets = nc_non_current_assets_total + nc_current_assets_total
    nc_total_assets_prev = nc_non_current_assets_prev_total + nc_current_assets_prev_total

    nc_opening_balance_diff = []
    nc_opening_balance_diff_liab = []
    bs_diff = round(nc_total_equity_liab - nc_total_assets, 2)
    if bs_diff > 0.01:
        diff_entry = {'name': 'Difference in Opening Balances', 'balance': bs_diff, 'prev_balance': 0.0}
        nc_opening_balance_diff = [diff_entry]
        nc_total_assets += bs_diff
        assets['total_current_assets'] += bs_diff
        assets['total'] += bs_diff
    elif bs_diff < -0.01:
        abs_diff = abs(bs_diff)
        diff_entry = {'name': 'Difference in Opening Balances', 'balance': abs_diff, 'prev_balance': 0.0}
        nc_opening_balance_diff_liab = [diff_entry]
        nc_total_equity_liab += abs_diff
        capital['total_capital'] += abs_diff
        capital['total'] += abs_diff

    non_corporate_data = {
        'equity_and_liabilities': {
            'owners_funds': {
                'capital_account': nc_owners_capital,
                'reserves_and_surplus': nc_reserves_surplus,
                'total': nc_owners_funds_total,
                'prev_total': nc_owners_funds_prev_total
            },
            'non_current_liabilities': {
                'long_term_borrowings': nc_long_term_borrowings,
                'deferred_tax_liabilities': nc_deferred_tax_liab,
                'other_long_term_liabilities': nc_other_long_term_liab,
                'long_term_provisions': nc_long_term_provisions,
                'total': nc_non_current_liab_total,
                'prev_total': nc_non_current_liab_prev_total
            },
            'current_liabilities': {
                'short_term_borrowings': nc_short_term_borrowings,
                'trade_payables': {
                    'msme_dues': nc_trade_payables_msme,
                    'other_creditors_dues': nc_trade_payables_other,
                    'total': sum(x['balance'] for x in nc_trade_payables_msme) + sum(x['balance'] for x in nc_trade_payables_other),
                    'prev_total': sum(x.get('prev_balance', 0) for x in nc_trade_payables_msme) + sum(x.get('prev_balance', 0) for x in nc_trade_payables_other)
                },
                'other_current_liabilities': nc_other_current_liab,
                'short_term_provisions': nc_short_term_provisions,
                'total': nc_current_liab_total,
                'prev_total': nc_current_liab_prev_total
            },
            'difference_in_opening_balances': nc_opening_balance_diff_liab,
            'total': nc_total_equity_liab,
            'prev_total': nc_total_equity_liab_prev
        },
        'assets': {
            'non_current_assets': {
                'ppe_and_intangibles': {
                    'property_plant_equipment': nc_ppe,
                    'intangible_assets': nc_intangibles,
                    'capital_wip': nc_cwip,
                    'intangible_under_development': nc_intangible_dev,
                    'total': nc_ppe_and_intangibles_total,
                    'prev_total': nc_ppe_and_intangibles_prev_total
                },
                'non_current_investments': nc_non_current_inv,
                'deferred_tax_assets': nc_deferred_tax_assets,
                'long_term_loans_advances': nc_long_term_loans_adv,
                'other_non_current_assets': nc_other_non_current_assets,
                'total': nc_non_current_assets_total,
                'prev_total': nc_non_current_assets_prev_total
            },
            'current_assets': {
                'current_investments': nc_current_inv,
                'inventories': nc_inventories,
                'trade_receivables': nc_trade_receivables,
                'cash_and_bank_balances': nc_cash_bank,
                'short_term_loans_advances': nc_short_term_loans_adv,
                'other_current_assets': nc_other_current_assets,
                'total': nc_current_assets_total,
                'prev_total': nc_current_assets_prev_total
            },
            'difference_in_opening_balances': nc_opening_balance_diff,
            'total': nc_total_assets,
            'prev_total': nc_total_assets_prev
        }
    }

    return {
        'business_type': business_type,
        'company_name': company_name,
        'as_of_date': end_date,
        'assets': assets,
        'liabilities': liabilities,
        'capital': capital,
        'non_corporate': non_corporate_data,
        'is_balanced': abs(assets['total'] - (liabilities['total'] + capital['total'])) < 0.01
    }

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

def _calc_prev_period(start_date_str, end_date_str):
    """Calculate the exact previous financial year date range."""
    import datetime

    def to_date(val):
        if not val:
            return None
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.date() if isinstance(val, datetime.datetime) else val
        val_str = str(val).strip()
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
            try:
                return datetime.datetime.strptime(val_str, fmt).date()
            except ValueError:
                pass
        return None

    ed = to_date(end_date_str)
    if not ed:
        ed = datetime.date.today()

    sd = to_date(start_date_str)
    if not sd:
        if ed.month >= 4:
            sd = datetime.date(ed.year, 4, 1)
        else:
            sd = datetime.date(ed.year - 1, 4, 1)

    try:
        prev_sd = sd.replace(year=sd.year - 1)
    except ValueError:
        prev_sd = sd - datetime.timedelta(days=365)

    try:
        prev_ed = ed.replace(year=ed.year - 1)
    except ValueError:
        prev_ed = ed - datetime.timedelta(days=365)

    return prev_sd.strftime('%Y-%m-%d'), prev_ed.strftime('%Y-%m-%d')

def _get_inventory_stock_balances(tenant_id, start_date_str, end_date_str, prev_sd_str, prev_ed_str):
    import datetime
    from inventory.models import InventoryStockItem, StockMovement, InventoryItem
    from django.db.models import Sum

    def to_date(val):
        if not val:
            return None
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.date() if isinstance(val, datetime.datetime) else val
        val_str = str(val).strip()
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
            try:
                return datetime.datetime.strptime(val_str, fmt).date()
            except ValueError:
                pass
        return None

    ed = to_date(end_date_str)
    if not ed:
        ed = datetime.date.today()
    sd = to_date(start_date_str)
    if not sd:
        sd = datetime.date(ed.year, 4, 1) if ed.month >= 4 else datetime.date(ed.year - 1, 4, 1)

    prev_ed = to_date(prev_ed_str)
    prev_sd = to_date(prev_sd_str)

    stock_items = InventoryStockItem.objects.filter(tenant_id=tenant_id)
    master_items = InventoryItem.objects.filter(tenant_id=tenant_id).select_related('category')
    
    master_by_code = {}
    master_item_objs = {}
    for i in master_items:
        cat_main = i.category.category if i.category else 'General'
        sub = (i.category.subgroup if i.category else '') or (i.category_path if i.category_path else '')
        display_cat = f"{cat_main} > {sub}" if sub and cat_main != 'General' else (sub if sub else cat_main)
        if sub and cat_main in sub:
            display_cat = sub
        if i.item_code:
            master_by_code[i.item_code] = display_cat
            master_item_objs[i.item_code] = i

    cat_opening = {}
    cat_closing = {}
    prev_cat_opening = {}
    prev_cat_closing = {}

    for item in master_items:
        code = item.item_code
        cat = master_by_code.get(code, 'General')

        if cat not in cat_opening: cat_opening[cat] = 0
        if cat not in cat_closing: cat_closing[cat] = 0
        if cat not in prev_cat_opening: prev_cat_opening[cat] = 0
        if cat not in prev_cat_closing: prev_cat_closing[cat] = 0

        qs = StockMovement.objects.filter(tenant_id=tenant_id, item_code=code)
        
        m_item = master_item_objs.get(code)
        base_op_qty = float(m_item.opening_stock or 0) if m_item else 0
        base_op_rate = float(m_item.opening_rate or 0) if m_item else 0
        base_op_val = base_op_qty * base_op_rate

        def get_val(date_limit=None):
            f_qs = qs.filter(date__lte=date_limit) if date_limit else qs
            in_val = f_qs.filter(inward_qty__gt=0).aggregate(v=Sum('value'))['v'] or 0
            out_val = f_qs.filter(outward_qty__gt=0).aggregate(v=Sum('value'))['v'] or 0
            return float(base_op_val) + float(in_val) - float(out_val)

        op_date = sd - datetime.timedelta(days=1) if sd else None
        op_val = get_val(op_date) if sd else 0
        cl_val = get_val(ed)
        
        prev_op_date = prev_sd - datetime.timedelta(days=1) if prev_sd else None
        prev_op_val = get_val(prev_op_date) if prev_sd else 0
        prev_cl_val = get_val(prev_ed) if prev_ed else 0
        
        cat_opening[cat] += op_val
        cat_closing[cat] += cl_val
        prev_cat_opening[cat] += prev_op_val
        prev_cat_closing[cat] += prev_cl_val

    def build_tree(data_dict, prev_dict, negate=False):
        root = {}
        for path_str, val in data_dict.items():
            prev_val = prev_dict.get(path_str, 0)
            if val == 0 and prev_val == 0:
                continue
                
            parts = [p.strip() for p in path_str.split('>')]
            current = root
            for part in parts:
                if part not in current:
                    current[part] = {'val': 0, 'prev_val': 0, 'children': {}}
                current[part]['val'] += val
                current[part]['prev_val'] += prev_val
                current = current[part]['children']
                
        def to_list(node):
            res = []
            for k, v in node.items():
                mult = -1 if negate else 1
                item = {
                    'name': k,
                    'balance': v['val'] * mult,
                    'prev_balance': v['prev_val'] * mult
                }
                if v['children']:
                    item['sub_items'] = to_list(v['children'])
                res.append(item)
            return res
            
        return to_list(root)

    opening_sub = build_tree(cat_opening, prev_cat_opening, negate=False)
    closing_sub = build_tree(cat_closing, prev_cat_closing, negate=True)

    opening_item = None
    if opening_sub:
        opening_item = {
            'name': '(+) opening balance',
            'balance': sum(c['balance'] for c in opening_sub),
            'prev_balance': sum(c['prev_balance'] for c in opening_sub),
            'sub_items': opening_sub
        }

    closing_item = None
    if closing_sub:
        closing_item = {
            'name': '(-) closing balance',
            'balance': sum(c['balance'] for c in closing_sub),
            'prev_balance': sum(c['prev_balance'] for c in closing_sub),
            'sub_items': closing_sub
        }

    return opening_item, closing_item


def generate_profit_and_loss_data(user, start_date=None, end_date=None):
    """
    Generate Profit & Loss report data with date filters and comparative previous year figures.
    Supports Schedule III Non-Corporate Statement of Profit and Loss.
    """
    tenant_id = get_user_tenant_id(user)
    if not tenant_id:
        raise PermissionError('User has no associated tenant')
    
    from core.models import Tenant
    from accounting.models import MasterLedger
    
    tenant = Tenant.objects.filter(id=tenant_id).first()
    business_type = (tenant.business_type if tenant else '') or ''
    company_name = (tenant.name if tenant else '') or ''

    ml_qs = MasterLedger.objects.filter(tenant_id=tenant_id)
    ml_map = {l.name.lower().strip(): l for l in ml_qs if l.name}

    prev_sd, prev_ed = _calc_prev_period(start_date, end_date)

    tb_rows = db.get_trial_balance_data(tenant_id, start_date, end_date)
    prev_tb_rows = db.get_trial_balance_data(tenant_id, prev_sd, prev_ed)

    ledger_data_map = {}

    def process_tb(rows, field_key):
        for row in rows:
            name = row.get('ledger') or row.get('name')
            if not name or str(name).strip().lower() == "difference in opening balances":
                continue
            
            category = row.get('category') or ''
            group = row.get('group', '') or ''
            
            ml = ml_map.get(name.lower().strip())
            if not category and ml:
                category = ml.category or ''
            if not group and ml:
                group = ml.group or ''

            sg1 = getattr(ml, 'sub_group_1', '') or ''
            sg2 = getattr(ml, 'sub_group_2', '') or ''
            sg3 = getattr(ml, 'sub_group_3', '') or ''
            maj = getattr(ml, 'major_group', '') or ''
            text = f"{name} {group} {sg1} {sg2} {sg3} {maj}".lower()

            p_dr = float(row.get('period_debit') or 0.0)
            p_cr = float(row.get('period_credit') or 0.0)
            cl_dr = float(row.get('closing_debit') or 0.0)
            cl_cr = float(row.get('closing_credit') or 0.0)

            cat_str = (category or (ml.category if ml else '') or '').strip()
            maj_str = (maj or (ml.major_group if ml else '') or '').strip()
            grp_str = (group or (ml.group if ml else '') or '').strip()

            cat_upper = cat_str.upper()
            maj_upper = maj_str.upper()
            text_lower = text.lower()

            # Balance Sheet categories / groups must NOT appear in Profit & Loss
            if cat_upper in {'ASSET', 'ASSETS', 'LIABILITY', 'LIABILITIES', 'CAPITAL', 'EQUITY', "OWNERS'  FUNDS", "OWNERS' FUNDS", "NPO FUNDS"}:
                continue
            if maj_upper in {'ASSET', 'ASSETS', 'LIABILITY', 'LIABILITIES', 'CAPITAL', 'EQUITY', "OWNERS'  FUNDS", "OWNERS' FUNDS", "NPO FUNDS"}:
                continue
            if any(k in text_lower for k in [
                'duties & taxes', 'duties and taxes', 'input gst', 'output gst', 'cgst', 'sgst', 'igst',
                'input tax', 'output tax', 'tcs receivable', 'tds receivable', 'tax credit',
                'sundry debtors', 'sundry creditors', 'bank accounts', 'cash-in-hand', 'fixed assets',
                'current assets', 'current liabilities', 'loans (liability)', 'capital account', 'reserves & surplus',
                'suspense account', 'provisions'
            ]):
                continue

            grp_upper = grp_str.upper()

            # Strict P&L Category matching — using category, major_group, or group from ML/TB
            is_revenue = (
                cat_upper in {'REVENUE', 'INCOME'} or
                maj_upper in {'REVENUE', 'INCOME'} or
                grp_upper in {'SALES ACCOUNTS', 'DIRECT INCOMES', 'INDIRECT INCOMES',
                              'REVENUE FROM OPERATIONS', 'OTHER INCOME'} or
                any(k in text_lower for k in ['sales accounts', 'revenue from operations',
                                              'direct incomes', 'indirect incomes'])
            )
            is_expense = (
                cat_upper in {'EXPENSE', 'EXPENDITURE', 'EXPENSES'} or
                maj_upper in {'EXPENSE', 'EXPENDITURE', 'EXPENSES'} or
                grp_upper in {
                    'PURCHASE ACCOUNTS', 'DIRECT EXPENSES', 'INDIRECT EXPENSES',
                    'OTHER EXPENSES', 'COST OF GOODS SOLD', 'EMPLOYEE BENEFITS EXPENSE',
                    'FINANCE COSTS', 'DEPRECIATION, AMORTIZATION AND IMPAIRMENT',
                    'MANUFACTURING EXPENSES', 'TAX LEDGERS',
                    # Tax expense sub-groups from Schedule III hierarchy
                    'TAX EXPENSE', 'CURRENT TAX', 'DEFERRED TAX CHARGE/(BENEFIT)',
                    'DEFERRED TAX CHARGE', 'DEFERRED TAX'
                } or
                any(k in text_lower for k in [
                    'purchase accounts', 'direct expenses', 'indirect expenses',
                    'other expenses', 'cost of goods sold', 'employee benefits',
                    'finance costs', 'depreciation', 'tax ledger',
                    # Tax expense keywords from hierarchy
                    'tax expense', 'current tax', 'deferred tax'
                ])
            )

            if not is_revenue and not is_expense:
                continue

            if start_date or end_date:
                net_change = p_cr - p_dr if is_revenue else p_dr - p_cr
            else:
                net_change = cl_cr - cl_dr if is_revenue else cl_dr - cl_cr

            if abs(net_change) < 0.001:
                net_change = cl_cr - cl_dr if is_revenue else cl_dr - cl_cr

            if abs(net_change) < 0.001:
                continue

            balance_val = abs(net_change)

            if name not in ledger_data_map:
                ledger_data_map[name] = {
                    'name': name,
                    'group': grp_str,
                    'current': 0.0,
                    'previous': 0.0,
                    'is_revenue': is_revenue,
                    'is_expense': is_expense,
                    'text': text,
                    'code': getattr(ml, 'code', None) if ml else None
                }
            
            ledger_data_map[name][field_key] = balance_val

    process_tb(tb_rows, 'current')
    process_tb(prev_tb_rows, 'previous')

    nc_groups = {
        'nc_rev_operations': ({}, {}),
        'nc_other_income': ({}, {}),
        'nc_cogs': ({}, {}),
        'nc_employee_expenses': ({}, {}),
        'nc_finance_costs': ({}, {}),
        'nc_depreciation': ({}, {}),
        'nc_other_expenses': ({}, {}),
        'nc_exceptional_items': ({}, {}),
        'nc_extraordinary_items': ({}, {}),
        'nc_tax_current': ({}, {}),
        'nc_tax_prior': ({}, {}),
        'nc_tax_deferred': ({}, {}),
        'nc_discontinuing_ops': ({}, {}),
        'nc_discontinuing_tax': ({}, {})
    }

    def add_to_group(key, grp_str, l_name, curr, prev):
        ignore_groups = {
            'revenue from operations', 'other income', 'cost of goods sold', 'cogs',
            'employee benefits expense', 'employee expenses', 'finance costs', 'finance cost',
            'depreciation and amortization expense', 'depreciation', 'other expenses', 'other expense',
            'exceptional items', 'extraordinary items', 'current tax', 'deferred tax',
            'discontinuing operations'
        }
        
        if not grp_str or grp_str.lower() == l_name.lower() or grp_str.lower().strip() in ignore_groups:
            path = l_name
        else:
            path = f"{grp_str} > {l_name}"
            
        curr_dict, prev_dict = nc_groups[key]
        curr_dict[path] = curr_dict.get(path, 0.0) + curr
        prev_dict[path] = prev_dict.get(path, 0.0) + prev

    for name, data in ledger_data_map.items():
        text = data['text']
        grp_str = data.get('group', '').strip()
        curr = data['current']
        prev = data['previous']

        if data['is_revenue']:
            if any(k in text for k in ['sale', 'operation', 'service', 'turnover', 'gross revenue', 'revenue', 'sales']):
                add_to_group('nc_rev_operations', grp_str, name, curr, prev)
            else:
                add_to_group('nc_other_income', grp_str, name, curr, prev)
        elif data['is_expense']:
            if any(k in text for k in ['cost of goods', 'cogs', 'purchase', 'direct cost', 'material', 'freight in', 'raw material', 'carriage inward']):
                add_to_group('nc_cogs', grp_str, name, curr, prev)
            elif any(k in text for k in ['salary', 'salaries', 'wages', 'employee', 'staff', 'provident fund', 'pf', 'bonus', 'payroll', 'gratuity', 'stipend']):
                add_to_group('nc_employee_expenses', grp_str, name, curr, prev)
            elif any(k in text for k in ['finance', 'interest', 'bank charges', 'processing fee', 'loan fee', 'borrowing cost']):
                add_to_group('nc_finance_costs', grp_str, name, curr, prev)
            elif any(k in text for k in ['depreciation', 'amortization', 'amortisation', 'depr']):
                add_to_group('nc_depreciation', grp_str, name, curr, prev)
            elif any(k in text for k in ['exceptional', 'exceptional item']):
                add_to_group('nc_exceptional_items', grp_str, name, curr, prev)
            elif any(k in text for k in ['extraordinary', 'extraordinary item']):
                add_to_group('nc_extraordinary_items', grp_str, name, curr, prev)
            elif any(k in text for k in ['deferred tax']) and not any(k in text for k in ['input', 'output', 'gst', 'tcs', 'tds']):
                add_to_group('nc_tax_deferred', grp_str, name, curr, prev)
            elif any(k in text for k in ['excess/short provision', 'excess short provision', 'provision of tax relating', 'excess provision of tax', 'short provision of tax']):
                add_to_group('nc_tax_prior', grp_str, name, curr, prev)
            elif data.get('code') == '202021000000000':
                # Map using the exact hierarchy code for Tax Expense to catch renamed ledgers
                add_to_group('nc_tax_current', grp_str, name, curr, prev)
            elif any(k in text for k in ['current tax', 'income tax', 'tax expense']) and not any(k in text for k in ['input', 'output', 'gst', 'tcs', 'tds']):
                add_to_group('nc_tax_current', grp_str, name, curr, prev)
            elif grp_str.lower() == 'tax expense' and not any(k in text for k in ['input', 'output', 'gst', 'tcs', 'tds']):
                # Any ledger directly under the 'Tax expense' group goes to current tax bucket
                add_to_group('nc_tax_current', grp_str, name, curr, prev)
            elif any(k in text for k in ['discontinuing']):
                add_to_group('nc_discontinuing_ops', grp_str, name, curr, prev)
            else:
                add_to_group('nc_other_expenses', grp_str, name, curr, prev)

    def build_tree(data_dict, prev_dict, negate=False):
        root = {}
        for path_str, val in data_dict.items():
            prev_val = prev_dict.get(path_str, 0)
            if val == 0 and prev_val == 0:
                continue
                
            parts = [p.strip() for p in path_str.split('>')]
            current = root
            for part in parts:
                if part not in current:
                    current[part] = {'val': 0, 'prev_val': 0, 'children': {}}
                current[part]['val'] += val
                current[part]['prev_val'] += prev_val
                current = current[part]['children']
                
        def to_list(node):
            res = []
            for k, v in node.items():
                mult = -1 if negate else 1
                item = {
                    'name': k,
                    'balance': v['val'] * mult,
                    'prev_balance': v['prev_val'] * mult
                }
                if v['children']:
                    item['sub_items'] = to_list(v['children'])
                res.append(item)
            return res
            
        return to_list(root)

    nc_rev_operations = build_tree(nc_groups['nc_rev_operations'][0], nc_groups['nc_rev_operations'][1])
    nc_other_income = build_tree(nc_groups['nc_other_income'][0], nc_groups['nc_other_income'][1])
    nc_cogs = build_tree(nc_groups['nc_cogs'][0], nc_groups['nc_cogs'][1])
    nc_employee_expenses = build_tree(nc_groups['nc_employee_expenses'][0], nc_groups['nc_employee_expenses'][1])
    nc_finance_costs = build_tree(nc_groups['nc_finance_costs'][0], nc_groups['nc_finance_costs'][1])
    nc_depreciation = build_tree(nc_groups['nc_depreciation'][0], nc_groups['nc_depreciation'][1])
    nc_other_expenses = build_tree(nc_groups['nc_other_expenses'][0], nc_groups['nc_other_expenses'][1])
    nc_exceptional_items = build_tree(nc_groups['nc_exceptional_items'][0], nc_groups['nc_exceptional_items'][1])
    nc_extraordinary_items = build_tree(nc_groups['nc_extraordinary_items'][0], nc_groups['nc_extraordinary_items'][1])
    nc_tax_current = build_tree(nc_groups['nc_tax_current'][0], nc_groups['nc_tax_current'][1])
    nc_tax_prior = build_tree(nc_groups['nc_tax_prior'][0], nc_groups['nc_tax_prior'][1])
    nc_tax_deferred = build_tree(nc_groups['nc_tax_deferred'][0], nc_groups['nc_tax_deferred'][1])
    nc_discontinuing_ops = build_tree(nc_groups['nc_discontinuing_ops'][0], nc_groups['nc_discontinuing_ops'][1])
    nc_discontinuing_tax = build_tree(nc_groups['nc_discontinuing_tax'][0], nc_groups['nc_discontinuing_tax'][1])

    try:
        op_item, cl_item = _get_inventory_stock_balances(tenant_id, start_date, end_date, prev_sd, prev_ed)
        if op_item:
            nc_cogs.insert(0, op_item)
        if cl_item:
            nc_cogs.append(cl_item)
    except Exception as e:
        import logging
        logging.getLogger('reports').error(f"Failed to append inventory cogs: {e}")

    def calc_totals(items):
        total_curr = sum(x['balance'] for x in items)
        total_prev = sum(x['prev_balance'] for x in items)
        return {'items': items, 'total': total_curr, 'prev_total': total_prev}

    rev_ops_data = calc_totals(nc_rev_operations)
    other_inc_data = calc_totals(nc_other_income)
    total_income = rev_ops_data['total'] + other_inc_data['total']
    prev_total_income = rev_ops_data['prev_total'] + other_inc_data['prev_total']

    cogs_data = calc_totals(nc_cogs)
    emp_data = calc_totals(nc_employee_expenses)
    fin_data = calc_totals(nc_finance_costs)
    depr_data = calc_totals(nc_depreciation)
    other_exp_data = calc_totals(nc_other_expenses)

    total_expenses = cogs_data['total'] + emp_data['total'] + fin_data['total'] + depr_data['total'] + other_exp_data['total']
    prev_total_expenses = cogs_data['prev_total'] + emp_data['prev_total'] + fin_data['prev_total'] + depr_data['prev_total'] + other_exp_data['prev_total']

    profit_before_exceptional = total_income - total_expenses
    prev_profit_before_exceptional = prev_total_income - prev_total_expenses

    exceptional_data = calc_totals(nc_exceptional_items)
    profit_before_extraordinary = profit_before_exceptional - exceptional_data['total']
    prev_profit_before_extraordinary = prev_profit_before_exceptional - exceptional_data['prev_total']

    extraordinary_data = calc_totals(nc_extraordinary_items)
    profit_before_tax = profit_before_extraordinary - extraordinary_data['total']
    prev_profit_before_tax = prev_profit_before_extraordinary - extraordinary_data['prev_total']

    tax_curr_data = calc_totals(nc_tax_current)
    tax_prior_data = calc_totals(nc_tax_prior)
    tax_def_data = calc_totals(nc_tax_deferred)
    total_tax = tax_curr_data['total'] + tax_prior_data['total'] + tax_def_data['total']
    prev_total_tax = tax_curr_data['prev_total'] + tax_prior_data['prev_total'] + tax_def_data['prev_total']

    profit_continuing = profit_before_tax - total_tax
    prev_profit_continuing = prev_profit_before_tax - prev_total_tax

    discont_ops_data = calc_totals(nc_discontinuing_ops)
    discont_tax_data = calc_totals(nc_discontinuing_tax)
    discont_after_tax = discont_ops_data['total'] - discont_tax_data['total']
    prev_discont_after_tax = discont_ops_data['prev_total'] - discont_tax_data['prev_total']

    net_profit = profit_continuing + discont_after_tax
    prev_net_profit = prev_profit_continuing + prev_discont_after_tax

    return {
        'business_type': business_type,
        'company_name': company_name,
        'start_date': start_date,
        'end_date': end_date,
        'prev_start_date': prev_sd,
        'prev_end_date': prev_ed,
        'total_income': total_income,
        'prev_total_income': prev_total_income,
        'total_expenses': total_expenses,
        'prev_total_expenses': prev_total_expenses,
        'net_profit': net_profit,
        'prev_net_profit': prev_net_profit,
        'non_corporate': {
            'revenue_from_operations': rev_ops_data,
            'other_income': other_inc_data,
            'total_income': total_income,
            'prev_total_income': prev_total_income,
            'expenses': {
                'cost_of_goods_sold': cogs_data,
                'employee_benefits_expense': emp_data,
                'finance_costs': fin_data,
                'depreciation_amortization': depr_data,
                'other_expenses': other_exp_data,
                'total': total_expenses,
                'prev_total': prev_total_expenses
            },
            'profit_before_exceptional_extraordinary': profit_before_exceptional,
            'prev_profit_before_exceptional_extraordinary': prev_profit_before_exceptional,
            'exceptional_items': exceptional_data,
            'profit_before_extraordinary': profit_before_extraordinary,
            'prev_profit_before_extraordinary': prev_profit_before_extraordinary,
            'extraordinary_items': extraordinary_data,
            'profit_before_tax': profit_before_tax,
            'prev_profit_before_tax': prev_profit_before_tax,
            'tax_expense': {
                'current_tax': tax_curr_data,
                'prior_period_tax': tax_prior_data,
                'deferred_tax': tax_def_data,
                'total': total_tax,
                'prev_total': prev_total_tax
            },
            'profit_continuing_operations': profit_continuing,
            'prev_profit_continuing_operations': prev_profit_continuing,
            'discontinuing_operations': {
                'profit_loss': discont_ops_data,
                'tax_expense': discont_tax_data,
                'total_after_tax': discont_after_tax,
                'prev_total_after_tax': prev_discont_after_tax
            },
            'net_profit_for_year': net_profit,
            'prev_net_profit_for_year': prev_net_profit
        }
    }