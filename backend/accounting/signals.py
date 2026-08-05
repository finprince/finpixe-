from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction, VoucherPurchaseSupplierDetails, VoucherSalesInvoiceDetails, PendingTransaction, AdvanceAllocation
from .services.portal_mirror_service import mirror_purchase_to_portal, mirror_sales_to_portal, mirror_transaction_to_portal, delete_purchase_from_portal, delete_sales_from_portal, delete_transaction_from_portal
from django.db import transaction

@receiver(post_save, sender=VoucherPurchaseSupplierDetails)
def on_purchase_save(sender, instance, created, **kwargs):
    """Mirror purchase to portal whenever it's saved"""
    transaction.on_commit(lambda: mirror_purchase_to_portal(instance))

@receiver(post_delete, sender=VoucherPurchaseSupplierDetails)
def on_purchase_delete(sender, instance, **kwargs):
    """Cleanup portal when purchase deleted"""
    delete_purchase_from_portal(instance)

@receiver(post_save, sender=VoucherSalesInvoiceDetails)
def on_sales_save(sender, instance, created, **kwargs):
    """Mirror sales to portal whenever it's saved"""
    transaction.on_commit(lambda: mirror_sales_to_portal(instance))

@receiver(post_delete, sender=VoucherSalesInvoiceDetails)
def on_sales_delete(sender, instance, **kwargs):
    """Cleanup portal when sales deleted"""
    delete_sales_from_portal(instance)

@receiver(post_save, sender=Transaction)
def on_transaction_save(sender, instance, created, **kwargs):
    """Mirror payment/receipt to portal whenever it's saved"""
    if instance.transaction_type in {'PAYMENT', 'RECEIPT'}:
        transaction.on_commit(lambda: mirror_transaction_to_portal(instance))

@receiver(post_delete, sender=Transaction)
def on_transaction_delete(sender, instance, **kwargs):
    """Cleanup portal when transaction deleted"""
    if instance.transaction_type in {'PAYMENT', 'RECEIPT'}:
        delete_transaction_from_portal(instance)

@receiver(post_save, sender=PendingTransaction)
@receiver(post_save, sender=AdvanceAllocation)
def on_allocation_save(sender, instance, **kwargs):
    """Trigger mirror update for parent header when allocation changes"""
    if instance.transaction:
        transaction.on_commit(lambda: mirror_transaction_to_portal(instance.transaction))
    if instance.reference_number:
        try:
            from .models_voucher_sales import VoucherSalesInvoiceDetails
            inv = VoucherSalesInvoiceDetails.objects.filter(tenant_id=instance.tenant_id, sales_invoice_no=instance.reference_number).first()
            if inv:
                transaction.on_commit(lambda: mirror_sales_to_portal(inv))
            from .models_voucher_purchase import VoucherPurchaseSupplierDetails
            pur = VoucherPurchaseSupplierDetails.objects.filter(tenant_id=instance.tenant_id, purchase_voucher_no=instance.reference_number).first()
            if pur:
                transaction.on_commit(lambda: mirror_purchase_to_portal(pur))
        except:
            pass