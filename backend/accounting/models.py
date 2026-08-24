from django.db import models
from django.utils import timezone
from core.models import BaseModel
from .models_transaction import TransactionFile
from .models_transaction import TransactionFile
from .models_voucher_expense import VoucherExpense
from .models_voucher_contra import VoucherContra
from .models_voucher_journal import VoucherJournal
from .models_voucher_purchase import VoucherPurchaseSupplierDetails, VoucherPurchaseSupplyForeignDetails, VoucherPurchaseSupplyINRDetails, VoucherPurchaseDueDetails, VoucherPurchaseTransitDetails
from .models_voucher_credit_note import VoucherCreditNoteInvoiceDetails, VoucherCreditNoteItemDetails, VoucherCreditNoteDueDetails, VoucherCreditNoteTransitDetails
from .models_voucher_sales import VoucherSalesInvoiceDetails, VoucherSalesItems, VoucherSalesItemsForeign, VoucherSalesPaymentDetails, VoucherSalesDispatchDetails, VoucherSalesEwayBill

class MasterChartOfAccounts(models.Model):
    """
    Global read-only master hierarchy for Chart of Accounts.
    Standardized across all tenants.
    """
    type_of_business = models.CharField(max_length=255)
    financial_reporting = models.CharField(max_length=255)
    major_group = models.CharField(max_length=255)
    group = models.CharField(max_length=255)
    sub_group_1 = models.CharField(max_length=255, null=True, blank=True)
    sub_group_2 = models.CharField(max_length=255, null=True, blank=True)
    sub_group_3 = models.CharField(max_length=255, null=True, blank=True)
    ledger_name = models.CharField(max_length=255, null=True, blank=True)
    ledger_code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    level_depth = models.IntegerField(default=1)
    import_version = models.CharField(max_length=20, default='1.0')
    imported_at = models.DateTimeField(auto_now_add=True)
    is_leaf = models.BooleanField(default=False)

    class Meta:
        db_table = 'master_chart_of_accounts'
        verbose_name_plural = 'Master Chart of Accounts'

    def __str__(self):
        return f'{self.ledger_name} ({self.ledger_code})' if self.ledger_name else self.group

class TenantLedger(BaseModel):
    """
    Branch-specific selection of ledgers from the master.
    """
    master_ledger = models.ForeignKey(MasterChartOfAccounts, on_delete=models.RESTRICT)
    custom_alias = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'tenant_ledgers'
        unique_together = ('tenant_id', 'master_ledger')

    def __str__(self):
        return self.custom_alias or self.master_ledger.ledger_name

class MasterLedgerGroup(BaseModel):
    name = models.CharField(max_length=255)
    parent = models.CharField(max_length=255, null=True, blank=True, help_text='Parent group name')
    parent_id = models.ForeignKey('self', on_delete=models.RESTRICT, null=True, blank=True, related_name='subgroups', db_column='parent_id')
    group_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'master_ledger_groups'
        unique_together = ('name', 'tenant_id')

    def __str__(self):
        return self.name

class MasterLedger(BaseModel):
    REG_TYPE_CHOICES = [('Registered', 'Registered'), ('Unregistered', 'Unregistered'), ('Composition', 'Composition')]
    name = models.CharField(max_length=255, null=True, blank=True, db_column='ledger_type')
    group = models.CharField(max_length=255, null=True, blank=True, help_text='Ledger group name')
    group_id = models.ForeignKey(MasterLedgerGroup, on_delete=models.RESTRICT, null=True, blank=True, related_name='ledgers', db_column='group_id')
    category = models.CharField(max_length=255, null=False, blank=True, default='', help_text='Major group / category (e.g. Asset, Liability)')
    sub_group_1 = models.CharField(max_length=255, null=True, blank=True)
    sub_group_2 = models.CharField(max_length=255, null=True, blank=True)
    sub_group_3 = models.CharField(max_length=255, null=True, blank=True)
    gstin = models.CharField(max_length=15, null=True, blank=True)
    registration_type = models.CharField(max_length=20, choices=REG_TYPE_CHOICES, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    extended_data = models.JSONField(null=True, blank=True, help_text='Group-specific fields (e.g., cashLocation, loanAccountNumber)')
    parent_ledger_id = models.IntegerField(null=True, blank=True, help_text='ID of parent custom ledger for nested structure')
    code = models.CharField(max_length=50, null=True, blank=True, unique=False, db_column='ledger_code', help_text='Auto-generated code based on hierarchy position')
    additional_data = models.JSONField(null=True, blank=True, help_text='Stores answers to dynamic questions (e.g., opening balance, GSTIN, credit limit)')
    opening_balance = models.DecimalField(max_digits=25, decimal_places=2, default=0.0, help_text='Opening balance amount for this ledger')
    opening_balance_type = models.CharField(max_length=2, default='Dr', blank=True, help_text="Opening balance type: 'Dr' or 'Cr'")
    major_group = models.CharField(max_length=255, null=True, blank=True)
    financial_reporting = models.CharField(max_length=255, null=True, blank=True)
    type_of_business = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'master_ledgers'
        unique_together = ('name', 'tenant_id')

    def __str__(self):
        return f'{self.name or '-'} ({self.group})'

    @property
    def ledger_type(self):
        """Compatibility alias: logical ledger_type maps to canonical `name`."""
        return self.name

    @ledger_type.setter
    def ledger_type(self, value):
        self.name = value

class Voucher(BaseModel):
    VOUCHER_TYPES = [('sales', 'Sales'), ('purchase', 'Purchase'), ('payment', 'Payment'), ('receipt', 'Receipt'), ('contra', 'Contra'), ('journal', 'Journal'), ('debit_note', 'Debit Note'), ('credit_note', 'Credit Note')]
    type = models.CharField(max_length=20, choices=VOUCHER_TYPES)
    voucher_number = models.CharField(max_length=50)
    date = models.DateField(default=timezone.now)
    party = models.CharField(max_length=255, null=True, blank=True)
    account = models.CharField(max_length=255, null=True, blank=True, help_text='Payment/Receipt account (Cash/Bank)')
    amount = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True)
    total = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    narration = models.TextField(null=True, blank=True)
    ref_no = models.CharField(max_length=150, null=True, blank=True, help_text='Reference Number (Cheque, NEFT, etc)')
    source = models.CharField(max_length=100, default='manual', help_text='Source of voucher (e.g., manual, ocr)')
    invoice_no = models.CharField(max_length=50, null=True, blank=True)
    is_inter_state = models.BooleanField(default=False, null=True, blank=True)
    total_taxable_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    total_cgst = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    total_sgst = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    total_igst = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    total_debit = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    total_credit = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    from_account = models.CharField(max_length=255, null=True, blank=True)
    to_account = models.CharField(max_length=255, null=True, blank=True)
    reference_id = models.BigIntegerField(null=True, blank=True, help_text='ID of the source document (Invoice/Order)')
    dummy_force = models.IntegerField(null=True, blank=True)
    ledger_id_val = models.BigIntegerField(null=True, blank=True)
    party_customer_id = models.BigIntegerField(null=True, blank=True)
    party_vendor_id = models.BigIntegerField(null=True, blank=True)

    @property
    def pay_from(self):
        return self.account

    @property
    def receive_in(self):
        return self.account

    @property
    def items_data(self):
        """Dynamic fetching of items for backward compatibility with frontend JSON expectation"""
        if self.type == 'sales':
            from .models_voucher_sales import VoucherSalesItems
            items = VoucherSalesItems.objects.filter(invoice__voucher_id=self.id)
            return [{'itemCode': item.item_code, 'itemName': item.item_name, 'hsnSac': item.hsn_sac, 'qty': float(item.qty), 'uom': item.uom, 'itemRate': float(item.item_rate), 'taxableValue': float(item.taxable_value), 'igst': float(item.igst), 'cgst': float(item.cgst), 'sgst': float(item.sgst), 'cess': float(item.cess), 'invoiceValue': float(item.invoice_value), 'salesLedger': item.sales_ledger, 'description': item.description} for item in items]
        elif self.type == 'purchase':
            from .models_voucher_purchase import VoucherPurchaseItem
            items = VoucherPurchaseItem.objects.filter(supplier_details__purchase_voucher_no=self.voucher_number, tenant_id=self.tenant_id)
            return [{'itemCode': item.item_code, 'itemName': item.item_name, 'hsnSac': item.hsn_sac, 'qty': float(item.quantity), 'uom': item.uom, 'itemRate': float(item.rate), 'taxableValue': float(item.taxable_value), 'igst': float(item.igst_amount), 'cgst': float(item.cgst_amount), 'sgst': float(item.sgst_amount), 'cess': float(item.cess_amount), 'invoiceValue': float(item.invoice_value)} for item in items]
        return []

    class Meta:
        db_table = 'vouchers'
        unique_together = ('tenant_id', 'type', 'voucher_number')
        ordering = ['-date']
        indexes = [models.Index(fields=['type', 'tenant_id', 'date']), models.Index(fields=['tenant_id', 'date'])]

class VoucherAdvanceAdjustment(BaseModel):
    """
    Dedicated table for tracking adjustments between an Advance and a Voucher (Invoice/Bill).
    """
    tenant_id = models.CharField(max_length=50, db_index=True)
    advance_voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='adjustments_out')
    target_voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='adjustments_in')
    ref_no = models.CharField(max_length=150, db_index=True)
    amount = models.DecimalField(max_digits=25, decimal_places=2)
    adjustment_date = models.DateField()
    customer_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    vendor_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    type = models.CharField(max_length=20, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'voucher_advance_adjustments'
        unique_together = ('tenant_id', 'advance_voucher', 'target_voucher', 'ref_no')

    def __str__(self):
        return f'{self.ref_no}: {self.amount} ({self.advance_voucher.voucher_number} -> {self.target_voucher.voucher_number})'

class JournalEntry(BaseModel):
    voucher_type = models.CharField(max_length=50)
    voucher_id = models.BigIntegerField()
    voucher_number = models.CharField(max_length=50, null=True, blank=True)
    transaction_date = models.DateField(null=True, blank=True)
    narration = models.TextField(null=True, blank=True)
    reference_number = models.CharField(max_length=100, null=True, blank=True)
    allocation_status = models.CharField(max_length=20, default='Unutilized')
    ledger = models.ForeignKey(MasterLedger, on_delete=models.RESTRICT, related_name='journal_entries', db_column='ledger_id', null=True, blank=True)
    ledger_name = models.CharField(max_length=255, null=True, blank=True)
    debit = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    customer = models.ForeignKey('customerportal.CustomerMasterCustomerBasicDetails', null=True, blank=True, on_delete=models.SET_NULL, db_column='customer_id')
    vendor = models.ForeignKey('vendors.VendorMasterBasicDetail', null=True, blank=True, on_delete=models.SET_NULL, db_column='vendor_id')
    ledger_id_val = models.BigIntegerField(null=True, blank=True)
    party_customer_id = models.BigIntegerField(null=True, blank=True)
    party_vendor_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'entries'
        indexes = [models.Index(fields=['tenant_id', 'voucher_type', 'voucher_id']), models.Index(fields=['tenant_id', 'ledger'])]

    def save(self, *args, **kwargs):
        from customerportal.database import CustomerMasterCustomerBasicDetails
        from vendors.models import VendorMasterBasicDetail
        from django.core.exceptions import ValidationError
        if self.customer and self.vendor:
            raise ValidationError('A journal entry cannot belong to both a customer and a vendor.')
        if not self.customer and (not self.vendor) and self.ledger_name:
            v_type = (self.voucher_type or '').lower()
            if 'sale' in v_type or 'receipt' in v_type or (self.ledger and self.ledger.group == 'Sundry Debtors'):
                mapped_customer = CustomerMasterCustomerBasicDetails.objects.filter(tenant_id=self.tenant_id, customer_name=self.ledger_name).first()
                if mapped_customer:
                    self.customer = mapped_customer
            elif 'purchase' in v_type or 'payment' in v_type or (self.ledger and self.ledger.group == 'Sundry Creditors'):
                mapped_vendor = VendorMasterBasicDetail.objects.filter(tenant_id=self.tenant_id, vendor_name=self.ledger_name).first()
                if mapped_vendor:
                    self.vendor = mapped_vendor
        super().save(*args, **kwargs)

class AmountTransaction(BaseModel):
    """
    Stores transaction amounts for Cash and Bank ledgers from Asset category.
    Tracks opening balances and transaction history with separate debit/credit columns.
    """
    TRANSACTION_TYPE_CHOICES = [('opening_balance', 'Opening Balance'), ('transaction', 'Transaction')]
    ledger = models.ForeignKey(MasterLedger, on_delete=models.CASCADE, related_name='amount_transactions', help_text='Reference to the Cash/Bank ledger')
    ledger_name = models.CharField(max_length=255, null=True, blank=True, help_text="Ledger name (e.g., 'bank2', 'Cash', 'HDFC Bank')")
    sub_group_1 = models.CharField(max_length=255, null=True, blank=True, help_text="Sub group 1 from ledger (e.g., 'Current Assets')")
    code = models.CharField(max_length=50, null=True, blank=True, help_text='Ledger code from master_ledgers table')
    transaction_date = models.DateField(help_text='Date of transaction')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='transaction', help_text='Type of transaction')
    debit = models.DecimalField(max_digits=25, decimal_places=2, default=0, help_text='Debit amount (money coming in)')
    credit = models.DecimalField(max_digits=25, decimal_places=2, default=0, help_text='Credit amount (money going out)')
    voucher = models.ForeignKey(Voucher, on_delete=models.SET_NULL, null=True, blank=True, related_name='amount_transactions', help_text='Reference to voucher if transaction is from a voucher')
    balance = models.DecimalField(max_digits=25, decimal_places=2, default=0, help_text='Running balance after this transaction')
    narration = models.TextField(null=True, blank=True, help_text='Transaction description or narration')

    class Meta:
        db_table = 'amount_transactions'
        ordering = ['-transaction_date', '-created_at']
        indexes = [models.Index(fields=['tenant_id', 'ledger', 'transaction_date']), models.Index(fields=['tenant_id', 'transaction_type']), models.Index(fields=['transaction_date'])]

    def clean(self):
        """
        Strict validation: Only allow ledgers from specific hierarchy.
        Assets -> Cash and Bank Balances -> Cash or Bank
        """
        if not self.ledger:
            return

        def match(val, expected):
            return str(val).lower().strip() == expected
        is_valid = False
        if self.ledger.category and str(self.ledger.category).lower().strip() in {'asset', 'assets'}:
            if self.ledger.group and match(self.ledger.group, 'cash and bank balances'):
                if self.ledger.sub_group_1:
                    sg1 = str(self.ledger.sub_group_1).lower().strip()
                    if sg1 in {'cash', 'bank'}:
                        is_valid = True
        if not is_valid:
            from django.core.exceptions import ValidationError
            raise ValidationError({'ledger_name': f"Invalid Ledger '{self.ledger.name}'. Transactions allowed only for 'Assets -> Cash and Bank Balances -> Cash or Bank'."})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.ledger.name} - Dr:{self.debit} Cr:{self.credit} - {self.transaction_date}'

class MasterHierarchyRaw(models.Model):
    """
    Global hierarchy data (unmanaged, maps to existing table).
    This represents the complete COA from the original project source.
    """
    id = models.AutoField(primary_key=True)
    major_group_1 = models.TextField(db_column='major_group_1', null=True, blank=True)
    group_1 = models.TextField(db_column='group_1', null=True, blank=True)
    sub_group_1_1 = models.TextField(db_column='sub_group_1_1', null=True, blank=True)
    sub_group_2_1 = models.TextField(db_column='sub_group_2_1', null=True, blank=True)
    sub_group_3_1 = models.TextField(db_column='sub_group_3_1', null=True, blank=True)
    ledger_1 = models.TextField(db_column='ledger_1', null=True, blank=True)
    code = models.TextField(db_column='code', null=True, blank=True)
    major_group_2 = models.CharField(max_length=255, null=True, blank=True)
    sub_group_3_2 = models.CharField(max_length=255, null=True, blank=True)
    type_of_business_2 = models.CharField(max_length=255, null=True, blank=True)
    sub_group_2_2 = models.CharField(max_length=255, null=True, blank=True)
    financial_reporting_1 = models.CharField(max_length=255, null=True, blank=True)
    sub_group_1_2 = models.CharField(max_length=255, null=True, blank=True)
    type_of_business_1 = models.CharField(max_length=255, null=True, blank=True)
    ledger_2 = models.CharField(max_length=255, null=True, blank=True)
    financial_reporting_2 = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'master_hierarchy_raw'

class ExtractedInvoice(BaseModel):
    """
    Stores data extracted from invoices via OCR.
    Supports 109 fields mapping to the Excel export specification.
    """
    voucher_date = models.CharField(max_length=20, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    po_number = models.CharField(max_length=100, null=True, blank=True)
    po_date = models.CharField(max_length=20, null=True, blank=True)
    supplier_name = models.CharField(max_length=255, null=True, blank=True)
    bill_from_address = models.TextField(null=True, blank=True)
    ship_from_address = models.TextField(null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    sales_person = models.CharField(max_length=255, null=True, blank=True)
    gstin = models.CharField(max_length=15, null=True, blank=True)
    pan = models.CharField(max_length=10, null=True, blank=True)
    msme_number = models.CharField(max_length=50, null=True, blank=True)
    payment_terms = models.CharField(max_length=255, null=True, blank=True)
    delivery_terms = models.CharField(max_length=255, null=True, blank=True)
    ledger_amount = models.CharField(max_length=50, null=True, blank=True)
    ledger_rate = models.CharField(max_length=50, null=True, blank=True)
    ledger_dr_cr = models.CharField(max_length=10, null=True, blank=True, db_column='ledger_amount_dr_cr')
    ledger_narration = models.TextField(null=True, blank=True)
    ledger_description = models.TextField(null=True, blank=True, db_column='description_of_ledger')
    tax_payment_type = models.CharField(max_length=100, null=True, blank=True, db_column='type_of_tax_payment')
    item_code = models.CharField(max_length=100, null=True, blank=True)
    item_description = models.TextField(null=True, blank=True, db_column='item_description')
    quantity = models.CharField(max_length=50, null=True, blank=True)
    uom = models.CharField(max_length=50, null=True, blank=True, db_column='quantity_uom')
    item_rate = models.CharField(max_length=50, null=True, blank=True)
    discount_pct = models.CharField(max_length=50, null=True, blank=True, db_column='disc_pct')
    item_amount = models.CharField(max_length=50, null=True, blank=True)
    marks = models.CharField(max_length=255, null=True, blank=True)
    num_packages = models.CharField(max_length=50, null=True, blank=True, db_column='no_of_packages')
    freight_charges = models.CharField(max_length=50, null=True, blank=True)
    hsn_sac = models.CharField(max_length=20, null=True, blank=True, db_column='hsn_sac_details')
    gst_rate = models.CharField(max_length=50, null=True, blank=True)
    igst_amount = models.CharField(max_length=50, null=True, blank=True)
    cgst_amount = models.CharField(max_length=50, null=True, blank=True)
    sgst_amount = models.CharField(max_length=50, null=True, blank=True, db_column='sgst_utgst_amount')
    cess_rate = models.CharField(max_length=50, null=True, blank=True)
    cess_amount = models.CharField(max_length=50, null=True, blank=True)
    state_cess_rate = models.CharField(max_length=50, null=True, blank=True)
    state_cess_amount = models.CharField(max_length=50, null=True, blank=True)
    reverse_charge = models.CharField(max_length=10, null=True, blank=True, db_column='applicable_for_reverse_charge')
    taxable_value = models.CharField(max_length=50, null=True, blank=True)
    invoice_value = models.CharField(max_length=50, null=True, blank=True)
    additional_fields = models.JSONField(null=True, blank=True, help_text='Stores the remaining 60+ fields dynamically')

    class Meta:
        db_table = 'extracted_invoices'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invoice_number} - {self.supplier_name}'
from .models_voucher_sales import VoucherSalesInvoiceDetails as SalesVoucher, VoucherSalesItems as SalesVoucherItem, VoucherSalesDispatchDetails, VoucherSalesEwayBill, VoucherSalesPaymentDetails

class SalesInvoice(BaseModel):
    """
    Sales Invoice - Invoice Details Only (Phase 1)
    Separate from SalesVoucher for cleaner architecture.
    """
    TAX_TYPE_CHOICES = [('within_state', 'Within State'), ('other_state', 'Other State'), ('export', 'Export')]
    STATUS_CHOICES = [('draft', 'Draft'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    invoice_number = models.CharField(max_length=50, help_text='Auto-generated, sequential')
    invoice_date = models.DateField(help_text='Must be today or past date')
    voucher_type = models.ForeignKey('masters.MasterVoucherReceipts', on_delete=models.PROTECT, related_name='sales_invoices', help_text='Sales voucher type')
    customer = models.ForeignKey(MasterLedger, on_delete=models.PROTECT, related_name='invoices', help_text='Customer from ledgers')
    bill_to_address = models.TextField(help_text='Auto-fetched from customer')
    bill_to_gstin = models.CharField(max_length=15, null=True, blank=True)
    bill_to_contact = models.CharField(max_length=255, null=True, blank=True)
    bill_to_state = models.CharField(max_length=100, null=True, blank=True)
    bill_to_country = models.CharField(max_length=100, default='India')
    ship_to_address = models.TextField(help_text='Auto-fetched but editable')
    ship_to_state = models.CharField(max_length=100, null=True, blank=True)
    ship_to_country = models.CharField(max_length=100, default='India')
    tax_type = models.CharField(max_length=20, choices=TAX_TYPE_CHOICES, help_text='Auto-determined from addresses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    current_step = models.IntegerField(default=1, help_text='Current workflow step (1-5)')

    class Meta:
        db_table = 'sales_invoices'
        unique_together = ('tenant_id', 'invoice_number')
        ordering = ['-invoice_date', '-created_at']
        indexes = [models.Index(fields=['tenant_id', 'invoice_date']), models.Index(fields=['customer', 'tenant_id']), models.Index(fields=['voucher_type'])]

    def __str__(self):
        return f'{self.invoice_number} - {self.customer.name}'

    def clean(self):
        """Validate invoice date"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.invoice_date and self.invoice_date > timezone.now().date():
            raise ValidationError({'invoice_date': 'Future dates not allowed'})

class Transaction(BaseModel):
    """
    Unified transaction model for Payment and Receipt vouchers.
    """
    TRANSACTION_TYPE_CHOICES = [('PAYMENT', 'Payment'), ('RECEIPT', 'Receipt')]
    voucher_number = models.CharField(max_length=100, db_index=True)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, db_index=True)
    date = models.DateField(db_index=True)
    total_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    vouch_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, help_text='Amount entered in the voucher header')
    narration = models.TextField(null=True, blank=True)
    posting_note = models.TextField(null=True, blank=True, help_text='Header-level posting note from the voucher form')
    ref_no = models.CharField(max_length=150, null=True, blank=True, help_text='Reference Number (Cheque, NEFT, etc)')
    bank_reconciled = models.BooleanField(default=False)
    bank_reconcile_date = models.DateField(null=True, blank=True)
    bank_statement_id = models.BigIntegerField(null=True, blank=True)
    bank_reference_number = models.CharField(max_length=100, null=True, blank=True)
    pay_from_ledger = models.ForeignKey('MasterLedger', on_delete=models.RESTRICT, related_name='transactions_from', null=True, blank=True)
    pay_to_ledger = models.ForeignKey('MasterLedger', on_delete=models.RESTRICT, related_name='transactions_to', null=True, blank=True)
    debit = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    ledger_id_val = models.BigIntegerField(null=True, blank=True)
    party_customer_id = models.BigIntegerField(null=True, blank=True)
    party_vendor_id = models.BigIntegerField(null=True, blank=True)
    pay_from_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    pay_from_customer_id_val = models.BigIntegerField(null=True, blank=True)
    pay_from_vendor_id_val = models.BigIntegerField(null=True, blank=True)
    pay_to_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    pay_to_customer_id_val = models.BigIntegerField(null=True, blank=True)
    pay_to_vendor_id_val = models.BigIntegerField(null=True, blank=True)
    receive_from_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    receive_from_customer_id_val = models.BigIntegerField(null=True, blank=True)
    receive_from_vendor_id_val = models.BigIntegerField(null=True, blank=True)
    receive_in_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    receive_in_customer_id_val = models.BigIntegerField(null=True, blank=True)
    receive_in_vendor_id_val = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'transactions'
        unique_together = ('tenant_id', 'voucher_number')
        ordering = ['-date', '-created_at']
        indexes = [models.Index(fields=['tenant_id', 'date']), models.Index(fields=['transaction_type'])]

    def __str__(self):
        return f'{self.transaction_type}: {self.voucher_number} ({self.date})'

    @property
    def type(self):
        """Alias transaction_type -> type for Voucher-serializer compatibility"""
        tt = (self.transaction_type or '').upper()
        if tt == 'RECEIPT':
            return 'receipt'
        if tt == 'PAYMENT':
            return 'payment'
        return (self.transaction_type or '').lower()

    @type.setter
    def type(self, value):
        self.transaction_type = (value or '').upper()

    @property
    def notes(self):
        """Alias narration -> notes for serializer compatibility"""
        return self.narration

    @notes.setter
    def notes(self, value):
        self.narration = value

    @property
    def receive_in(self):
        """Alias pay_to_ledger -> receive_in for receipt serializer compatibility"""
        return self.pay_to_ledger

    def get_items(self):
        """Unified access to all allocation sub-items for mirroring/POST-logic"""
        return list(self.advanceallocation_items.all()) + list(self.pendingtransaction_items.all()) + list(self.transactionallocation_items.all())

    def delete_items(self):
        """Delete all allocation sub-items"""
        self.advanceallocation_items.all().delete()
        self.pendingtransaction_items.all().delete()
        self.transactionallocation_items.all().delete()

class AllocationBase(BaseModel):
    """
    Sub-details for Transaction (Header) relating to bill-wise apps.
    Shared by AdvanceAllocation and PendingTransaction.
    """
    ALLOCATION_TYPE_CHOICES = [('INVOICE', 'Invoice'), ('ADVANCE', 'Advance'), ('ON_ACCOUNT', 'On Account')]
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='%(class)s_items')
    type = models.CharField(max_length=50, null=True, blank=True)
    reference_id = models.CharField(max_length=150, null=True, blank=True, db_index=True)
    reference_number = models.CharField(max_length=150, null=True, blank=True, db_index=True)
    ref_no = models.CharField(max_length=150, null=True, blank=True, help_text='Reference Number (Cheque, NEFT, etc)')
    reference_type = models.CharField(max_length=20, choices=ALLOCATION_TYPE_CHOICES, default='INVOICE')
    pay_to_ledger = models.ForeignKey('MasterLedger', on_delete=models.RESTRICT, related_name='%(class)s_to', null=True, blank=True)
    pay_from_ledger = models.ForeignKey('MasterLedger', on_delete=models.RESTRICT, related_name='%(class)s_from', null=True, blank=True)
    allocated_amount = models.DecimalField(max_digits=25, decimal_places=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, null=True, blank=True)
    vouch_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0, help_text='Amount entered in the voucher header')
    due_date = models.DateField(null=True, blank=True)
    due_status = models.CharField(max_length=50, null=True, blank=True)
    original_amount = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    invoice_date = models.DateField(null=True, blank=True)
    pending_before = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=25, decimal_places=2, default=0)
    ledger_id_val = models.BigIntegerField(null=True, blank=True)
    party_customer_id = models.BigIntegerField(null=True, blank=True)
    party_vendor_id = models.BigIntegerField(null=True, blank=True)
    pay_from_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    pay_from_customer_id_val = models.BigIntegerField(null=True, blank=True)
    pay_from_vendor_id_val = models.BigIntegerField(null=True, blank=True)
    pay_to_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    pay_to_customer_id_val = models.BigIntegerField(null=True, blank=True)
    pay_to_vendor_id_val = models.BigIntegerField(null=True, blank=True)
    receive_from_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    receive_from_customer_id_val = models.BigIntegerField(null=True, blank=True)
    receive_from_vendor_id_val = models.BigIntegerField(null=True, blank=True)
    receive_in_ledger_id_val = models.BigIntegerField(null=True, blank=True)
    receive_in_customer_id_val = models.BigIntegerField(null=True, blank=True)
    receive_in_vendor_id_val = models.BigIntegerField(null=True, blank=True)
    is_advance = models.BooleanField(default=False)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='GST Rate (e.g. 18.00) for Advance Tax (AT) reporting')
    advance_ref_no = models.CharField(max_length=150, null=True, blank=True)
    posting_note = models.TextField(null=True, blank=True, help_text='Per-row posting note entered in the allocation table')
    narration = models.TextField(null=True, blank=True, help_text='Original narration from bank upload or source')
    gst_registered = models.CharField(max_length=3, default='', blank=True, help_text="'Yes' if this advance has been filed in GST, empty otherwise")
    amendment_date = models.DateField(null=True, blank=True, help_text='Date when the advance was amended')
    original_voucher_snapshot = models.JSONField(null=True, blank=True, help_text='Snapshot of the original filed AT values')
    amendment_filed = models.BooleanField(default=False, help_text='True once this ATA amendment has been filed in GST')

    @property
    def amount_applied(self):
        return self.allocated_amount

    @amount_applied.setter
    def amount_applied(self, value):
        self.allocated_amount = value

    @property
    def received_amount(self):
        return self.allocated_amount

    @received_amount.setter
    def received_amount(self, value):
        self.allocated_amount = value

    @property
    def pending_amount(self):
        return self.pending_before

    @pending_amount.setter
    def pending_amount(self, value):
        self.pending_before = value

    @property
    def total_amount(self):
        return self.pending_before

    @total_amount.setter
    def total_amount(self, value):
        self.pending_before = value

    @property
    def voucher(self):
        return self.transaction

    @voucher.setter
    def voucher(self, value):
        self.transaction = value

    class Meta:
        abstract = True

class AdvanceAllocation(AllocationBase):

    class Meta:
        db_table = 'advance_allocation'

class PendingTransaction(AllocationBase):

    class Meta:
        db_table = 'pending_transaction'

class TransactionAllocation(AllocationBase):
    """Legacy unified table - keeping as alias/shim if needed"""

    class Meta:
        db_table = 'transaction_allocations'
        indexes = [models.Index(fields=['tenant_id', 'reference_number']), models.Index(fields=['reference_type'])]
TransactionAllocationItem = TransactionAllocation
PaymentVoucher = Transaction
PaymentVoucherItem = TransactionAllocation
ReceiptVoucher = Transaction
ReceiptVoucherItem = TransactionAllocation
VoucherAllocation = TransactionAllocation
AllocationLink = TransactionAllocation
VoucherPendingTransaction = TransactionAllocation
VoucherPaymentSingle = Transaction
VoucherPaymentBulk = Transaction
VoucherReceiptSingle = Transaction
VoucherReceiptBulk = Transaction