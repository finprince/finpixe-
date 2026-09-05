from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction as db_transaction
from .models_voucher_sales import VoucherSalesInvoiceDetails
from .serializers_voucher_sales import VoucherSalesInvoiceDetailsSerializer
from .models import Voucher, JournalEntry, MasterLedger
from .models_voucher_receipt import VoucherReceiptSingle
from core.mixins import BranchQuerysetMixin
from decimal import Decimal
import datetime

class VoucherSalesViewSet(BranchQuerysetMixin, viewsets.ModelViewSet):
    queryset = VoucherSalesInvoiceDetails.objects.all().order_by('-date', '-created_at')
    serializer_class = VoucherSalesInvoiceDetailsSerializer
    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('items')
        # Filter for the current tenant
        user = self.request.user
        tenant_id = getattr(user, 'tenant_id', None)
        
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        # For detail (retrieve/update/partial_update/destroy) actions, always return all records.
        if self.action in ('retrieve', 'update', 'partial_update', 'destroy'):
            return queryset

        # Support for showing all OR filtering for Pending/Due ones
        show_all = self.request.query_params.get('show_all') == 'true'
        status_param = self.request.query_params.get('status')
        
        if not show_all and status_param != 'all':
            from django.db.models import Q
            # EXCLUDE FULLY PAID INVOICES
            queryset = queryset.exclude(status='received')

            # MANDATORY: Only show vouchers with positive outstanding balance OR fresh ones without details
            queryset = queryset.filter(
                Q(payment_details__payment_balance__gt=0) | 
                Q(payment_details__isnull=True)
            ).select_related('payment_details')
        
        # Optional: Filter by customer ID/name/branch if provided
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
            
        customer_name = self.request.query_params.get('customer_name')
        if customer_name:
            queryset = queryset.filter(customer_name=customer_name)
        
        branch = self.request.query_params.get('branch')
        if branch:
            queryset = queryset.filter(customer_branch__iexact=branch.strip())

        # Filter by specific invoice number (for fetching full item details)
        sales_invoice_no = self.request.query_params.get('sales_invoice_no')
        if sales_invoice_no:
            queryset = queryset.filter(sales_invoice_no=sales_invoice_no)
        
        return queryset

    def get_object(self):
        """
        Override to resolve a generic Voucher ID to VoucherSalesInvoiceDetails.
        Handles cases where frontend or reports pass generic voucher ID instead of sales details ID.
        """
        from django.http import Http404
        try:
            return super().get_object()
        except Http404:
            pk = self.kwargs.get('pk')
            generic_voucher = Voucher.objects.filter(id=pk, type='sales').first()
            if generic_voucher and generic_voucher.reference_id:
                self.kwargs['pk'] = generic_voucher.reference_id
                return super().get_object()
            user = self.request.user
            tenant_id = getattr(user, 'tenant_id', None)
            instance = VoucherSalesInvoiceDetails.objects.filter(
                tenant_id=tenant_id,
                id=pk
            ).first()
            if instance:
                return instance
            raise

    def perform_create(self, serializer):
        super().perform_create(serializer)

    @action(detail=True, methods=['post'], url_path='post-receipt')
    def post_receipt(self, request, pk=None):
        invoice = self.get_object()
        tenant_id = invoice.tenant_id
        data = request.data
        
        # Required fields from request
        receipt_date = data.get('dateOfReceipt')
        method = data.get('methodOfReceipt') # 'Cash' or 'Bank'
        ledger_id = data.get('ledger_id') or data.get('bankAccount') # ID of Bank/Cash ledger
        amount = data.get('amount', 0)
        reference_no = data.get('bankReferenceNo', '')
        narration = data.get('narration') or f"Receipt against Invoice {invoice.sales_invoice_no}"

        if not receipt_date or not method:
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        if method == 'Bank' and not ledger_id:
             return Response({"error": "Bank account selection is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with db_transaction.atomic():
                # 1. Resolve Ledgers
                # receive_in_ledger (Bank/Cash)
                if method == 'Cash' and not ledger_id:
                     receive_in_ledger = MasterLedger.objects.filter(
                        tenant_id=tenant_id, 
                        group__icontains='Cash',
                        category='Asset'
                    ).first()
                     if not receive_in_ledger:
                         return Response({"error": "No default Cash ledger found."}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    receive_in_ledger = MasterLedger.objects.get(id=ledger_id, tenant_id=tenant_id)
                
                # receive_from_ledger (Customer)
                # We need to find the ledger associated with this customer
                # Assuming customer name matches ledger name or linked via customer_id
                if invoice.customer_id:
                    # Try to find by customer_id if we have a way, else by name
                    receive_from_ledger = MasterLedger.objects.filter(name=invoice.customer_name, tenant_id=tenant_id).first()
                else:
                    receive_from_ledger = MasterLedger.objects.filter(name=invoice.customer_name, tenant_id=tenant_id).first()

                if not receive_from_ledger:
                    return Response({"error": f"Customer ledger '{invoice.customer_name}' not found"}, status=status.HTTP_400_BAD_REQUEST)

                # 2. Create Unified Voucher
                voucher_no = f"REC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                voucher = Voucher.objects.create(
                    tenant_id=tenant_id,
                    type='receipt',
                    voucher_number=voucher_no,
                    date=receipt_date,
                    party=invoice.customer_name,
                    account=receive_in_ledger.name,
                    amount=amount,
                    total=amount,
                    narration=narration,
                    reference_id=invoice.id,
                    source='customer_portal'
                )

                # 3. Create VoucherReceiptSingle (alias for Transaction)
                receipt_transaction = VoucherReceiptSingle.objects.create(
                    tenant_id=tenant_id,
                    date=receipt_date,
                    transaction_type='RECEIPT',
                    voucher_number=voucher_no,
                    total_amount=amount,
                    amount=amount,
                    pay_to_ledger=receive_in_ledger,
                    pay_from_ledger=receive_from_ledger,
                    bank_reference_number=reference_no
                )

                # 4. Create Journal Entries
                # NEW: Populating denormalized columns
                
                # Debit: Bank/Cash
                JournalEntry.objects.create(
                    tenant_id=tenant_id,
                    voucher_type='receipt',
                    voucher_id=voucher.id,
                    voucher_number=voucher_no,
                    transaction_date=receipt_date,
                    narration=narration,
                    ledger=receive_in_ledger,
                    ledger_name=receive_in_ledger.name,
                    debit=amount,
                    credit=0
                )
                
                # Credit: Customer
                JournalEntry.objects.create(
                    tenant_id=tenant_id,
                    voucher_type='receipt',
                    voucher_id=voucher.id,
                    voucher_number=voucher_no,
                    transaction_date=receipt_date,
                    narration=narration,
                    ledger=receive_from_ledger,
                    ledger_name=receive_from_ledger.name,
                    debit=0,
                    credit=amount
                )


                # 5. Create Allocation record so the system tracks this payment centrally
                from .models import PendingTransaction
                PendingTransaction.objects.create(
                    tenant_id=tenant_id,
                    transaction=receipt_transaction,
                    reference_id=str(invoice.id),
                    reference_number=invoice.sales_invoice_no,
                    reference_type='INVOICE',
                    pay_from_ledger=receive_from_ledger,
                    pay_to_ledger=receive_in_ledger,
                    allocated_amount=amount,
                    amount=amount
                )

                # 6. Mirror to Customer Portal so the receipt shows up in transaction history
                try:
                    from customerportal.models import CustomerTransaction, CustomerMasterCustomer
                    portal_customer = CustomerMasterCustomer.objects.filter(ledger_id=receive_from_ledger.id, tenant_id=tenant_id).first()
                    if portal_customer:
                        CustomerTransaction.objects.update_or_create(
                            tenant_id=tenant_id,
                            transaction_number=voucher_no,
                            transaction_type='receipt',
                            customer_id=portal_customer.id,
                            defaults={
                                'transaction_date': receipt_date,
                                'total_amount': amount,
                                'amount': amount,
                                'reference_number': invoice.sales_invoice_no,
                                'notes': narration
                            }
                        )
                except Exception as e:
                    print(f"!!! Mirroring Error in post-receipt: {str(e)}")

                # 7. Recalculate Invoice Status using the central service
                try:
                    from .services.sales_status_service import update_sales_invoice_payment_status
                    update_sales_invoice_payment_status(tenant_id, str(invoice.id))
                except Exception as e:
                    print(f"!!! Status Sync Error in post-receipt: {str(e)}")
                
                return Response({"message": "Receipt posted successfully", "voucher_no": voucher_no}, status=status.HTTP_201_CREATED)

        except MasterLedger.DoesNotExist:
            return Response({"error": "Selected ledger not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
        from core.utils import nested_multipart_to_nested_dict
        
        # Check if it's multipart
        content_type = request.content_type or ''
        if 'multipart/form-data' in content_type:
            # Manually expand nested keys from FormData
            data = nested_multipart_to_nested_dict(request.data)
            
            # SANITIZATION: Remove empty strings for file fields which cause validation errors
            if data.get('supporting_document') == '':
                data['supporting_document'] = None
            if isinstance(data.get('dispatch_details'), dict):
                if data['dispatch_details'].get('dispatch_document') == '':
                    data['dispatch_details']['dispatch_document'] = None

            # Re-initialize the serializer with the expanded data
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        from .models import Voucher, VoucherSalesInvoiceDetails
        tenant_id = getattr(request.user, 'tenant_id', None)
        
        try:
            # Look up directly to bypass get_queryset filters (e.g. show_all)
            invoice = VoucherSalesInvoiceDetails.objects.get(id=pk, tenant_id=tenant_id)
        except VoucherSalesInvoiceDetails.DoesNotExist:
            # Fallback: pk might be the generic Voucher ID instead of the VoucherSalesInvoiceDetails ID
            try:
                voucher = Voucher.objects.get(id=pk, type="sales", tenant_id=tenant_id)
                invoice = VoucherSalesInvoiceDetails.objects.get(id=voucher.reference_id, tenant_id=tenant_id)
            except (Voucher.DoesNotExist, VoucherSalesInvoiceDetails.DoesNotExist, ValueError):
                return Response({"error": "Invoice not found"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"error": f"DEBUG: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if invoice.status == 'cancelled':
            return Response({"error": "Invoice is already cancelled"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with db_transaction.atomic():
                # 1. Update status
                invoice.status = 'cancelled'
                invoice.save()

                # 2. Delete or reverse Journal Entries for the sales invoice
                from .models import JournalEntry, Voucher
                try:
                    voucher = Voucher.objects.get(
                        type="sales",
                        reference_id=invoice.id,
                        tenant_id=invoice.tenant_id
                    )
                    # Clear JEs
                    JournalEntry.objects.filter(
                        voucher_id=voucher.id,
                        tenant_id=invoice.tenant_id
                    ).delete()
                    
                    # Update Voucher total to 0 as it is cancelled
                    voucher.total = Decimal('0.00')
                    voucher.total_taxable_amount = Decimal('0.00')
                    voucher.total_cgst = Decimal('0.00')
                    voucher.total_sgst = Decimal('0.00')
                    voucher.total_igst = Decimal('0.00')
                    voucher.save()
                except Voucher.DoesNotExist:
                    pass

                # 3. If there are payment details, clear balance/totals
                if hasattr(invoice, 'payment_details') and invoice.payment_details:
                    pay = invoice.payment_details
                    pay.payment_invoice_value = Decimal('0.00')
                    pay.payment_taxable_value = Decimal('0.00')
                    pay.payment_cgst = Decimal('0.00')
                    pay.payment_sgst = Decimal('0.00')
                    pay.payment_igst = Decimal('0.00')
                    pay.payment_cess = Decimal('0.00')
                    pay.payment_balance = Decimal('0.00')
                    pay.payment_received = Decimal('0.00')
                    pay.payment_payable = Decimal('0.00')
                    pay.save()

                return Response({"message": "Invoice cancelled successfully", "status": invoice.status})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='send-email')
    def send_email(self, request, pk=None):
        invoice = self.get_object()
        recipient_email = request.data.get('recipient_email') or invoice.customer_email
        from .services.sales_invoice_mail_service import send_sales_invoice_email
        result = send_sales_invoice_email(
            invoice_id=invoice.id,
            recipient_email=recipient_email,
            sender_user=request.user
        )
        if result.get('success'):
            return Response(result, status=status.HTTP_200_OK)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
