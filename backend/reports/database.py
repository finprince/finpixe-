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

def parse_date(date_val):
    """Normalize date strings (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD) into YYYY-MM-DD for standard database filtering and comparisons."""
    if not date_val:
        return None
    s = str(date_val).strip()
    if not s or s == '-' or s.lower() == 'none' or s.lower() == 'null':
        return None
    # Handle YYYY-MM-DD
    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
        return s[:10]
    # Handle DD-MM-YYYY or DD/MM/YYYY
    parts = s.split('-') if '-' in s else s.split('/')
    if len(parts) == 3:
        if len(parts[2]) == 4:  # DD-MM-YYYY
            day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
            return f"{year}-{month}-{day}"
        elif len(parts[0]) == 4:  # YYYY-MM-DD
            return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    return s

def get_vouchers_for_daybook(tenant_id, start_date=None, end_date=None):
    """Get all vouchers for day book report."""
    vouchers = Voucher.objects.filter(tenant_id=tenant_id)
    sd = parse_date(start_date)
    ed = parse_date(end_date)
    if sd:
        vouchers = vouchers.filter(date__gte=sd)
    if ed:
        vouchers = vouchers.filter(date__lte=ed)
    return vouchers.order_by('date', 'id')

def get_vouchers_for_ledger(tenant_id, ledger_name, start_date=None, end_date=None):
    """Get all vouchers involving a specific ledger."""
    vouchers = Voucher.objects.filter(tenant_id=tenant_id)
    sd = parse_date(start_date)
    ed = parse_date(end_date)
    if sd:
        vouchers = vouchers.filter(date__gte=sd)
    if ed:
        vouchers = vouchers.filter(date__lte=ed)
    q_party = Q(party=ledger_name)
    q_account = Q(account=ledger_name)
    q_contra = Q(from_account=ledger_name) | Q(to_account=ledger_name)
    from django.db.models import Exists, OuterRef
    journal_vouchers = JournalEntry.objects.filter(Q(ledger_name=ledger_name) | Q(ledger__name=ledger_name), tenant_id=tenant_id, voucher_id=OuterRef('id'))
    return vouchers.filter(q_party | q_account | q_contra | Exists(journal_vouchers)).distinct().order_by('date', 'id')

def _ensure_vouchers_posted(tenant_id):
    """
    Auto-resyncs journal postings for Sales and Purchase vouchers for tenant_id 
    so that selected sales/purchase ledgers reflect accurately in reports.
    """
    try:
        from accounting.models_voucher_sales import VoucherSalesInvoiceDetails
        from accounting.serializers_voucher_sales import VoucherSalesInvoiceDetailsSerializer
        from accounting.models_voucher_purchase import VoucherPurchaseSupplierDetails
        from accounting.serializers_voucher_purchase import VoucherPurchaseSupplierDetailsSerializer

        # 1. Sync Sales Vouchers
        sales_vouchers = VoucherSalesInvoiceDetails.objects.filter(tenant_id=tenant_id)
        s_serializer = VoucherSalesInvoiceDetailsSerializer()
        for inv in sales_vouchers:
            try:
                if inv.items.exists() or inv.foreign_items.exists():
                    s_serializer._post_journal_entries(inv)
            except Exception:
                pass

        # 2. Sync Purchase Vouchers
        purch_vouchers = VoucherPurchaseSupplierDetails.objects.filter(tenant_id=tenant_id)
        p_serializer = VoucherPurchaseSupplierDetailsSerializer()
        for pur in purch_vouchers:
            try:
                v_id = pur.voucher_id
                if not v_id:
                    from accounting.models import Voucher
                    v_obj = Voucher.objects.filter(tenant_id=tenant_id, type='purchase', reference_id=pur.id).first()
                    if v_obj:
                        v_id = v_obj.id
                if v_id:
                    due_data = None
                    if hasattr(pur, 'due_details') and pur.due_details:
                        due_data = {'tds_it': pur.due_details.tds_it, 'advance_paid': pur.due_details.advance_paid, 'to_pay': pur.due_details.to_pay}
                    net_val = float(pur.due_details.to_pay or 0) if hasattr(pur, 'due_details') and pur.due_details else 0.0
                    adv_val = float(pur.due_details.advance_paid or 0) if hasattr(pur, 'due_details') and pur.due_details else 0.0
                    p_serializer._post_journal_entries(pur, v_id, net_val + adv_val, None, None, due_data)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error ensuring vouchers posted: {e}")

def get_trial_balance_data(tenant_id, start_date=None, end_date=None):
    """Get aggregated ledger balances for trial balance with date filtering.
    Calculates Opening Balance, Period Debits/Credits, and Closing Balance per ledger.
    Ordered according to Accounting Master Hierarchy Tree position.
    """
    _ensure_vouchers_posted(tenant_id)
    from accounting.models import MasterLedger, JournalEntry, MasterHierarchyRaw
    
    # 1. Initialize map from MasterLedgers for tenant
    ledgers = MasterLedger.objects.filter(tenant_id=tenant_id)
    ledger_map = {}
    master_ledger_map = {}
    
    total_op_net = 0.0
    for l in ledgers:
        name = (l.name or '').strip()
        if not name:
            continue
        master_ledger_map[name.lower()] = l
        op_bal = float(l.opening_balance or 0.0)
        op_type = (l.opening_balance_type or 'Dr').strip().capitalize()
        initial_net = op_bal if op_type == 'Dr' else -op_bal
        total_op_net += initial_net
        ledger_map[name] = {
            'ledger': name,
            'initial_net': initial_net,
            'prior_debit': 0.0,
            'prior_credit': 0.0,
            'period_debit': 0.0,
            'period_credit': 0.0,
        }
        
    # Auto-balance opening balances if imbalanced (Standard Tally / SAP behavior)
    if abs(total_op_net) > 0.01:
        diff_name = "Difference in Opening Balances"
        ledger_map[diff_name] = {
            'ledger': diff_name,
            'initial_net': -total_op_net,
            'prior_debit': 0.0,
            'prior_credit': 0.0,
            'period_debit': 0.0,
            'period_credit': 0.0,
        }
        
    # Build hierarchy code lookup map by ledger name, sub_group, and group
    hierarchy_code_map = {}
    for h in MasterHierarchyRaw.objects.all().order_by('id'):
        code = (h.code or '').strip()
        if not code:
            continue
        names = [h.ledger_1, h.sub_group_3_1, h.sub_group_2_1, h.sub_group_1_1, h.group_1, h.major_group_1]
        for n in names:
            if n and n.strip() and n.strip() != '-':
                key = n.strip().lower()
                if key not in hierarchy_code_map:
                    hierarchy_code_map[key] = code
        
    # 2. Fetch JournalEntries for tenant (exclude supplementary breakdown detail rows)
    all_entries = JournalEntry.objects.filter(tenant_id=tenant_id).exclude(voucher_type__endswith='_DETAIL')
    
    for entry in all_entries:
        l_name = None
        if entry.ledger and entry.ledger.name:
            l_name = entry.ledger.name.strip()
        elif entry.ledger_name:
            l_name = entry.ledger_name.strip()
            
        if not l_name:
            l_name = '(Unknown)'
            
        if l_name not in ledger_map:
            ledger_map[l_name] = {
                'ledger': l_name,
                'initial_net': 0.0,
                'prior_debit': 0.0,
                'prior_credit': 0.0,
                'period_debit': 0.0,
                'period_credit': 0.0,
            }
            
        dr = float(entry.debit or 0.0)
        cr = float(entry.credit or 0.0)
        norm_start = parse_date(start_date)
        norm_end = parse_date(end_date)
        t_date = parse_date(entry.transaction_date) or ''
        
        if norm_start and t_date < norm_start:
            ledger_map[l_name]['prior_debit'] += dr
            ledger_map[l_name]['prior_credit'] += cr
        elif norm_end and t_date > norm_end:
            pass
        else:
            ledger_map[l_name]['period_debit'] += dr
            ledger_map[l_name]['period_credit'] += cr
            
    def get_ledger_sort_code(ledger_name):
        l_key = ledger_name.strip().lower()
        if l_key == "difference in opening balances":
            return (9, "9999999999999999", 999999)
        ml = master_ledger_map.get(l_key)
        
        # 1. MasterLedger code if present and numeric/hierarchical
        if ml and ml.code and ml.code.strip() and not ml.code.startswith(('CUST-', 'VEN-', 'PORTAL-')):
            return (0, ml.code.strip(), ml.id)
            
        # 2. Match by ledger name in hierarchy map
        if l_key in hierarchy_code_map:
            return (0, hierarchy_code_map[l_key], getattr(ml, 'id', 0))
            
        # 3. Match by MasterLedger group / sub_group in hierarchy map
        if ml:
            for g_field in [ml.group, ml.sub_group_1, ml.sub_group_2, ml.sub_group_3, ml.major_group, ml.category]:
                if g_field and g_field.strip() and g_field.strip().lower() in hierarchy_code_map:
                    return (0, hierarchy_code_map[g_field.strip().lower()], ml.id)
            # Custom user ledger: sort by creation ID in Accounting Master
            return (1, f"ML-{ml.id:08d}", ml.id)
            
        # 4. Fallback for unlinked ledgers
        return (2, ledger_name, 0)
            
    result = []
    for name, data in ledger_map.items():
        opening_net = data['initial_net'] + data['prior_debit'] - data['prior_credit']
        op_dr = opening_net if opening_net > 0 else 0.0
        op_cr = abs(opening_net) if opening_net < 0 else 0.0
        
        p_dr = data['period_debit']
        p_cr = data['period_credit']
        
        closing_net = opening_net + p_dr - p_cr
        cl_dr = closing_net if closing_net > 0 else 0.0
        cl_cr = abs(closing_net) if closing_net < 0 else 0.0
        
        # Hide ledgers with zero activity and balance
        if op_dr == 0 and op_cr == 0 and p_dr == 0 and p_cr == 0 and cl_dr == 0 and cl_cr == 0:
            continue
            
        ml = master_ledger_map.get(name.lower())
        cat = (ml.category if ml and ml.category else '') or ''
        grp = (ml.group if ml and ml.group else '') or ''
        sg1 = (ml.sub_group_1 if ml and ml.sub_group_1 else '') or ''
        sg2 = (ml.sub_group_2 if ml and ml.sub_group_2 else '') or ''
        sg3 = (ml.sub_group_3 if ml and ml.sub_group_3 else '') or ''
        maj = (ml.major_group if ml and ml.major_group else '') or ''

        result.append({
            'ledger': name,
            'category': cat,
            'group': grp,
            'sub_group_1': sg1,
            'sub_group_2': sg2,
            'sub_group_3': sg3,
            'major_group': maj,
            'opening_debit': float(round(op_dr, 2)),
            'opening_credit': float(round(op_cr, 2)),
            'period_debit': float(round(p_dr, 2)),
            'period_credit': float(round(p_cr, 2)),
            'closing_debit': float(round(cl_dr, 2)),
            'closing_credit': float(round(cl_cr, 2)),
            'debit': float(round(cl_dr, 2)),
            'credit': float(round(cl_cr, 2)),
        })
        
    result.sort(key=lambda item: get_ledger_sort_code(item['ledger']))
    return result

def get_ledger_balances(tenant_id, as_of_date=None):
    """Get all ledger balances as of a specific date."""
    entries = JournalEntry.objects.filter(tenant_id=tenant_id)
    norm_date = parse_date(as_of_date)
    if norm_date:
        entries = entries.filter(transaction_date__lte=norm_date)
    return entries.values('ledger__id', 'ledger__name', 'ledger__category', 'ledger__group', 'ledger__opening_balance', 'ledger__opening_balance_type').annotate(total_debit=Sum('debit'), total_credit=Sum('credit'))

def get_stock_items(tenant_id):
    """Get all stock items for stock summary."""
    return InventoryStockItem.objects.filter(tenant_id=tenant_id)

def get_stock_movements(tenant_id, start_date=None, end_date=None):
    """Get stock movements for stock summary."""
    movements = StockMovement.objects.filter(tenant_id=tenant_id)
    sd = parse_date(start_date)
    ed = parse_date(end_date)
    if sd:
        movements = movements.filter(date__gte=sd)
    if ed:
        movements = movements.filter(date__lte=ed)
    return movements.order_by('date')