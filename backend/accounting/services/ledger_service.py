from django.db import transaction
from decimal import Decimal
from accounting.models import JournalEntry, MasterLedger

def _resolve_ledger(value, tenant_id=None):
    """
    Resolve either a numeric ID, a ledger name (string), or a portal prefixed ID 
    (e.g., 'portal-cust-123' or 'portal-vend-456') to a MasterLedger instance.
    Returns the MasterLedger instance, or None if not found/invalid.
    """
    if value is None or value == '':
        return None

    # Handle portal prefixes
    if isinstance(value, str):
        val_str = value.strip()
        if val_str.startswith('portal-cust-'):
            try:
                cust_id = int(val_str.replace('portal-cust-', ''))
                from customerportal.database import CustomerMasterCustomerBasicDetails
                cust = CustomerMasterCustomerBasicDetails.objects.filter(id=cust_id).first()
                if cust and cust.ledger_id:
                    value = cust.ledger_id
            except Exception:
                pass
        elif val_str.startswith('portal-vend-'):
            try:
                vend_id = int(val_str.replace('portal-vend-', ''))
                from vendors.models import VendorMasterBasicDetail
                vend = VendorMasterBasicDetail.objects.filter(id=vend_id).first()
                if vend and vend.ledger_id:
                    value = vend.ledger_id
            except Exception:
                pass
        elif val_str.startswith('hierarchy-'):
            try:
                from accounting.models import MasterHierarchyRaw
                from django.db import transaction as _dbtx
                hier_id = int(val_str.replace('hierarchy-', ''))
                hier = MasterHierarchyRaw.objects.filter(id=hier_id).first()
                if hier and tenant_id:
                    # Resolve best available name from the hierarchy row
                    name = (hier.ledger_1 or hier.sub_group_3_1 or hier.sub_group_2_1 or hier.group_1 or '').strip()
                    # Skip placeholder '-' values
                    if name == '-':
                        name = (hier.sub_group_3_1 or hier.sub_group_2_1 or hier.sub_group_1_1 or hier.group_1 or '').strip()
                    if name and name != '-':
                        # First check if it already exists by exact name
                        existing = MasterLedger.objects.filter(tenant_id=tenant_id, name__iexact=name).first()
                        
                        if existing:
                            return existing
                        
                        # Create ledger from hierarchy blueprint using savepoint to avoid poisoning outer txn
                        try:
                            with _dbtx.atomic():
                                new_ledger, _ = MasterLedger.objects.get_or_create(
                                    tenant_id=tenant_id,
                                    name=name,
                                    defaults=dict(
                                        group=hier.group_1,
                                        sub_group_1=hier.sub_group_1_1,
                                        sub_group_2=hier.sub_group_2_1,
                                        sub_group_3=hier.sub_group_3_1,
                                        major_group=hier.major_group_1,
                                        financial_reporting=hier.financial_reporting_1,
                                        type_of_business=hier.type_of_business_1,
                                        code=hier.code,
                                        category=hier.major_group_1 or 'Other',
                                    )
                                )
                            return new_ledger
                        except Exception as e:
                            # Savepoint rolled back — try to fetch existing by name (race condition)
                            return MasterLedger.objects.filter(tenant_id=tenant_id, name__iexact=name).first()
                elif hier and not tenant_id:
                    # No tenant_id — resolve by name across any existing ledger
                    name = (hier.ledger_1 or hier.sub_group_3_1 or hier.sub_group_2_1 or hier.group_1 or '').strip()
                    if name and name != '-':
                        return MasterLedger.objects.filter(name__iexact=name).first()
            except Exception:
                pass
            return None  # hierarchy- prefix but couldn't resolve — don't fall through to int()

    # Already an integer ID
    try:
        pk = int(value)
        qs = MasterLedger.objects.filter(id=pk)
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs.first()
    except (ValueError, TypeError):
        pass

    # String name
    if isinstance(value, str):
        qs = MasterLedger.objects.filter(name__iexact=value.strip())
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs.first()

    # If already a model instance
    if hasattr(value, 'id'):
        return value

    return None

def _resolve_or_create_ledger(value, tenant_id=None, default_group='Other', default_category='Other'):
    """
    Resolves a ledger, and if it does not exist in MasterLedger for tenant_id,
    creates it automatically so double-entry journal postings use the exact chosen ledger.
    """
    if not value or (isinstance(value, str) and not value.strip()):
        return None
    l_obj = _resolve_ledger(value, tenant_id)
    if l_obj:
        return l_obj
    if isinstance(value, str) and value.strip() and tenant_id:
        name_clean = value.strip()
        if name_clean.startswith(('portal-cust-', 'portal-vend-', 'hierarchy-')):
            return None
        try:
            l_obj, _ = MasterLedger.objects.get_or_create(
                tenant_id=tenant_id,
                name=name_clean,
                defaults={
                    'group': default_group,
                    'category': default_category,
                    'major_group': default_category
                }
            )
            return l_obj
        except Exception:
            return MasterLedger.objects.filter(tenant_id=tenant_id, name__iexact=name_clean).first()
    return None

def post_transaction(voucher_type, voucher_id, tenant_id, entries, transaction_date=None, voucher_number=None):
    """
    Actual double-entry accounting posting.
    Validates:
    - At least 2 entries
    - Sum(debit) == Sum(credit)
    - No entry has both debit and credit > 0
    - No entry has both = 0
    Check duplicate by (voucher_type, voucher_id)
    """
    if len(entries) < 2:
        raise ValueError("At least 2 entries required for double-entry")

    total_debit = Decimal('0.00')
    total_credit = Decimal('0.00')

    for entry in entries:
        dr = Decimal(str(entry.get('debit', 0)))
        cr = Decimal(str(entry.get('credit', 0)))

        if dr > 0 and cr > 0:
            raise ValueError("Entry cannot have both debit and credit > 0")
        if dr == 0 and cr == 0:
            raise ValueError("Entry must have either debit or credit > 0")

        total_debit += dr
        total_credit += cr

    if total_debit != total_credit:
        raise ValueError(f"Accounting mismatch: Sum(debit)={total_debit} != Sum(credit)={total_credit}")

    with transaction.atomic():
        # Phase 3.1: Add SAFE CLEANUP before insert.
        # Delete by voucher_id (primary cleanup path).
        JournalEntry.objects.filter(
            tenant_id=tenant_id,
            voucher_type=voucher_type,
            voucher_id=voucher_id
        ).delete()
        # Safety net: also delete by voucher_number to catch entries that may have been
        # created with a different voucher_id (e.g., PaymentVoucher.id vs generic Voucher.id).
        # This prevents duplicate ledger entries after editing a voucher.
        if voucher_number:
            JournalEntry.objects.filter(
                tenant_id=tenant_id,
                voucher_type=voucher_type,
                voucher_number=voucher_number
            ).delete()

        # Phase 3.2: Create JournalEntry rows with STRICT ledger_id usage
        journal_objects = []
        for entry in entries:
            # Resolve ledger source
            l_id = entry.get('ledger_id')
            if not l_id:
                # Fallback check
                l_id = entry.get('ledger_id_val')

            if not l_id:
                continue

            journal_objects.append(JournalEntry(
                tenant_id=tenant_id,
                voucher_type=voucher_type,
                voucher_id=voucher_id,
                voucher_number=voucher_number,
                transaction_date=transaction_date,
                ledger_id=l_id,
                debit=Decimal(str(entry.get('debit', 0))),
                credit=Decimal(str(entry.get('credit', 0))),
                # Descriptive fields kept for backward compatibility but ignored for core logic
                ledger_name=getattr(_resolve_ledger(l_id, tenant_id), 'name', None),
                ledger_id_val=l_id
            ))
        
        if journal_objects:
            JournalEntry.objects.bulk_create(journal_objects)
        return True
