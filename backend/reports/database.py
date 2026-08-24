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

_last_posted_cache = {}

def _ensure_vouchers_posted(tenant_id):
    """
    Fast, targeted auto-resync for tenant_id:
    1. Patches MasterLedger category/group from MasterHierarchyRaw if generic/missing.
    2. Resolves unlinked JournalVoucherEntry records and posts missing JournalEntry rows.
    3. Resolves unlinked ExpenseLineItem records.
    Runs efficiently without looping over existing posted sales/purchase vouchers.
    """
    import time
    now = time.time()
    if tenant_id in _last_posted_cache and (now - _last_posted_cache[tenant_id]) < 60:
        return
    _last_posted_cache[tenant_id] = now

    # 1. Patch MasterLedger categories from MasterHierarchyRaw if generic or missing
    try:
        from accounting.models import MasterLedger, MasterHierarchyRaw
        ledgers_to_patch = MasterLedger.objects.filter(
            tenant_id=tenant_id
        ).filter(
            Q(sub_group_1__in=['', '-', None]) |
            Q(category__in=['Other', 'Expense', 'Liability', 'Asset', '', None])
        )
        for l in ledgers_to_patch:
            if not l.name:
                continue
            hier = MasterHierarchyRaw.objects.filter(ledger_1__iexact=l.name.strip()).first()
            if hier and hier.major_group_1 and hier.major_group_1.strip().lower() not in ('other', ''):
                update_fields = []
                if l.category != hier.major_group_1:
                    l.category = hier.major_group_1
                    l.major_group = hier.major_group_1
                    update_fields += ['category', 'major_group']
                if hier.group_1 and l.group != hier.group_1:
                    l.group = hier.group_1
                    update_fields.append('group')
                if hier.sub_group_1_1 and not l.sub_group_1:
                    l.sub_group_1 = hier.sub_group_1_1
                    update_fields.append('sub_group_1')
                if hier.sub_group_2_1 and not l.sub_group_2:
                    l.sub_group_2 = hier.sub_group_2_1
                    update_fields.append('sub_group_2')
                if hier.sub_group_3_1 and not l.sub_group_3:
                    l.sub_group_3 = hier.sub_group_3_1
                    update_fields.append('sub_group_3')
                if update_fields:
                    l.save(update_fields=update_fields)
    except Exception as patch_err:
        logger.error(f"Error patching master ledger categories: {patch_err}")

    # 2. Resync Journal Vouchers with missing/unresolved ledger_ids
    try:
        from accounting.models_voucher_journal import VoucherJournal, JournalVoucherEntry
        from accounting.models import Voucher
        from accounting.services.ledger_service import _resolve_ledger, post_transaction

        orphan_entries = list(JournalVoucherEntry.objects.filter(
            tenant_id=tenant_id,
            ledger_id__isnull=True
        ).exclude(ledger_name='').exclude(ledger_name__isnull=True))

        touched_vouchers = set()
        for entry in orphan_entries:
            if not entry.ledger_name:
                continue
            ledger_obj = _resolve_ledger(entry.ledger_name, tenant_id)
            if ledger_obj:
                try:
                    JournalVoucherEntry.objects.filter(pk=entry.pk).update(ledger_id=ledger_obj.id)
                    touched_vouchers.add(entry.voucher_id)
                except Exception as upd_err:
                    logger.error(f"Error updating JournalVoucherEntry {entry.pk}: {upd_err}")

        for jv_id in touched_vouchers:
            try:
                jv_entries = list(JournalVoucherEntry.objects.filter(voucher_id=jv_id, tenant_id=tenant_id))
                entries_to_post = []
                for e in jv_entries:
                    l_id = e.ledger_id
                    if not l_id and e.ledger_name:
                        lo = _resolve_ledger(e.ledger_name, tenant_id)
                        if lo:
                            l_id = lo.id
                    if not l_id:
                        continue
                    dr = float(e.debit_amount or 0)
                    cr = float(e.credit_amount or 0)
                    if dr > 0:
                        entries_to_post.append({"ledger_id": l_id, "debit": dr, "credit": 0.0})
                    if cr > 0:
                        entries_to_post.append({"ledger_id": l_id, "debit": 0.0, "credit": cr})

                if len(entries_to_post) >= 2:
                    generic_v = Voucher.objects.filter(source='journal_voucher', reference_id=jv_id).first()
                    jv = VoucherJournal.objects.filter(pk=jv_id).first()
                    if jv:
                        v_id_to_use = generic_v.id if generic_v else jv.id
                        post_transaction(
                            voucher_type="JOURNAL",
                            voucher_id=v_id_to_use,
                            tenant_id=tenant_id,
                            entries=entries_to_post,
                            transaction_date=jv.date,
                            voucher_number=jv.voucher_number,
                        )
            except Exception as post_err:
                logger.error(f"Error reposting journal voucher {jv_id}: {post_err}")
    except Exception as e:
        logger.error(f"Error resyncing journal vouchers: {e}")

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
        try:
            if entry.ledger and entry.ledger.name:
                l_name = entry.ledger.name.strip()
        except Exception:
            pass
        if not l_name and entry.ledger_name:
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
    """Get all ledger balances as of a specific date.
    Includes all MasterLedgers for tenant so opening balances are preserved across date filters.
    """
    from accounting.models import MasterLedger, JournalEntry
    from django.db.models import Sum

    ledgers = MasterLedger.objects.filter(tenant_id=tenant_id)
    norm_date = parse_date(as_of_date)

    entries = JournalEntry.objects.filter(tenant_id=tenant_id)
    if norm_date:
        entries = entries.filter(transaction_date__lte=norm_date)

    entry_map = {
        e['ledger__id']: e for e in entries.values('ledger__id').annotate(
            total_debit=Sum('debit'), total_credit=Sum('credit')
        ) if e.get('ledger__id')
    }

    result = []
    for l in ledgers:
        if not l.name:
            continue
        e = entry_map.get(l.id, {})
        result.append({
            'ledger__id': l.id,
            'ledger__name': l.name,
            'ledger__category': l.category,
            'ledger__group': l.group,
            'ledger__opening_balance': l.opening_balance,
            'ledger__opening_balance_type': l.opening_balance_type,
            'total_debit': e.get('total_debit', 0.0) or 0.0,
            'total_credit': e.get('total_credit', 0.0) or 0.0,
        })
    return result

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