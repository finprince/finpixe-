"""
API endpoints for Vendor Transactions.
This handles the PROCUREMENT ledger and all vendor portal transaction data.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import logging
import re
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
from django.utils import timezone
from django.db.models import Sum
from .models import VendorTransaction, VendorMasterTerms
from .vendortransaction_serializers import VendorTransactionSerializer
logger = logging.getLogger(__name__)

class VendorTransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vendor Transactions.
    Handles fetching and managing vendor transactions with tenant isolation.
    """
    queryset = VendorTransaction.objects.all()
    serializer_class = VendorTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_tenant_id(self):
        """Extract tenant_id from the authenticated user"""
        user = self.request.user
        return getattr(user, 'tenant_id', None) or getattr(user, 'branch_id', None) or getattr(user, 'id', 'default_tenant')

    def get_queryset(self):
        """Filter queryset by tenant"""
        tenant_id = self.get_tenant_id()
        return VendorTransaction.objects.filter(tenant_id=tenant_id).order_by('transaction_date', 'id')

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            from accounting.services.portal_mirror_service import sync_portal_allocation_to_main_ledger
            sync_portal_allocation_to_main_ledger(instance)
        except Exception as e:
            logger.error(f'Failed to reverse-sync vendor portal allocation: {e}')

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        details = request.data.get('transaction_details')
        tenant_id = self.get_tenant_id()
        if details and isinstance(details, list):
            for d in details:
                ref_no = d.get('reference_no')
                amt = Decimal(str(d.get('payment') or 0))
                if ref_no and amt > 0:
                    VendorTransaction.objects.create(tenant_id=tenant_id, vendor_id=instance.vendor_id, transaction_type='payment', transaction_number=f'ALC-{uuid.uuid4().hex[:6].upper()}', transaction_date=timezone.now().date(), amount=amt, total_amount=amt, status='Paid', reference_number=instance.reference_number or instance.transaction_number, notes=f'Allocated from {ref_no}')
            return Response({'success': True})
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def by_vendor(self, request):
        """
        Get all transactions for a specific vendor.
        
        GET /api/vendors/transactions/by_vendor/?vendor_id={id}
        """
        logger.info(f'=== Vendor Transactions BY VENDOR Request ===')
        vendor_id = request.query_params.get('vendor_id')
        if not vendor_id:
            return Response({'error': 'vendor_id query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        tenant_id = self.get_tenant_id()
        logger.info(f'Branch: {tenant_id}, Vendor ID: {vendor_id}')
        if not str(vendor_id).isdigit():
            match = re.search('(\\d+)', str(vendor_id))
            if match:
                vendor_id = match.group(1)
                logger.info(f"Extracted numeric vendor_id {vendor_id} from {request.query_params.get('vendor_id')}")
            else:
                logger.warning(f'Invalid non-numeric vendor_id: {vendor_id}')
                return Response([])
        transactions = self.get_queryset().filter(vendor_id=vendor_id)
        count_vendor = transactions.count()
        logger.info(f'Transactions found for vendor {vendor_id}: {count_vendor}')
        from datetime import date, timedelta, datetime
        from .models import VendorMasterTerms
        import re
        credit_period_days = 0
        try:
            from .models import VendorMasterTerms
            import re
            terms = VendorMasterTerms.objects.filter(tenant_id=tenant_id, vendor_basic_detail_id=vendor_id).first()
            if terms and terms.credit_period:
                raw = str(terms.credit_period).strip()
                if raw.isdigit():
                    credit_period_days = int(raw)
                else:
                    m = re.search('(\\d+)', raw)
                    if m:
                        credit_period_days = int(m.group(1))
        except Exception as e:
            logger.warning(f'Could not fetch credit period for vendor {vendor_id}: {e}')

        def calculate_due_status(transaction_date, credit_days):
            if not transaction_date:
                return ('Not Due', None)
            due_dt = transaction_date + timedelta(days=credit_days)
            status = 'Due' if date.today() > due_dt else 'Not Due'
            return (status, due_dt.strftime('%Y-%m-%d'))
        serializer = self.get_serializer(transactions, many=True)
        data = serializer.data
        for item in data:
            tx_type = (item.get('transaction_type') or '').lower()
            if tx_type == 'purchase':
                tx_status = (item.get('status') or '').lower()
                tx_date = item.get('transaction_date')
                ref_no = item.get('reference_number')
                total_amt = Decimal(str(item.get('total_amount') or 0))
                paid_sum = Decimal('0')
                total_purchase_amt = total_amt
                if ref_no:
                    other_purchases = VendorTransaction.objects.filter(tenant_id=tenant_id, vendor_id=vendor_id, reference_number=ref_no, transaction_type__iexact='purchase').exclude(id=item.get('id'))
                    for op in other_purchases:
                        total_purchase_amt += Decimal(str(op.total_amount or op.amount or 0))
                    linking_txs = VendorTransaction.objects.filter(tenant_id=tenant_id, vendor_id=vendor_id, reference_number=ref_no).exclude(id=item.get('id'))
                    for ltx in linking_txs:
                        ltype = ltx.transaction_type.lower()
                        if ltype in {'payment', 'debit_note'}:
                            paid_sum += Decimal(str(ltx.total_amount or ltx.amount or 0))
                        elif ltype == 'receipt':
                            paid_sum -= Decimal(str(ltx.total_amount or ltx.amount or 0))
                item['paid_amount'] = float(paid_sum)
                item['payment_balance'] = float(total_amt - paid_sum)
                is_fully_paid = total_purchase_amt > 0 and paid_sum >= total_purchase_amt
                is_partially_paid = paid_sum > 0 and paid_sum < total_purchase_amt
                due_status = 'Not Due'
                due_date_str = None
                if tx_date:
                    try:
                        parsed_date = datetime.strptime(str(tx_date), '%Y-%m-%d').date()
                        due_status, due_date_str = calculate_due_status(parsed_date, credit_period_days)
                    except (ValueError, TypeError):
                        pass
                if is_fully_paid:
                    item['due_status'] = 'Paid'
                elif is_partially_paid:
                    item['due_status'] = 'Partially Paid'
                elif due_status == 'Not Due':
                    item['due_status'] = 'Not Due'
                else:
                    item['due_status'] = 'Due'
                item['due_date'] = due_date_str
                item['credit_period_days'] = credit_period_days
            else:
                item['due_status'] = None
                item['due_date'] = None
                item['credit_period_days'] = 0
            is_generic = item.get('transaction_number') and item.get('reference_number') and item.get('transaction_number').startswith(item.get('reference_number') + '-')
            is_adv = item.get('reference_number') == 'ADVANCE' or is_generic
            if (tx_type == 'payment' or tx_type == 'receipt') and is_adv:
                v_num = item.get('transaction_number')
                used = VendorTransaction.objects.filter(tenant_id=tenant_id, vendor_id=vendor_id, notes__icontains=f'Allocated from {v_num}').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
                item['used_amount'] = float(used)
                item['paid_amount'] = float(used)
        return Response(data)

    @action(detail=False, methods=['post'])
    def remove_seed_data(self, request):
        """
        Remove dummy/seed records for a specific vendor.
        """
        vendor_id = request.data.get('vendor_id')
        tenant_id = self.get_tenant_id()
        if not vendor_id:
            return Response({'error': 'vendor_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        deleted_count, _ = VendorTransaction.objects.filter(tenant_id=tenant_id, vendor_id=vendor_id, notes__icontains='seed').delete()
        return Response({'success': True, 'message': f'Removed {deleted_count} seed records.'})