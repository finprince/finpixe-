from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction as db_transaction
from .models import Voucher
from .models_voucher_purchase import VoucherPurchaseSupplierDetails
from .serializers_voucher_purchase import VoucherPurchaseSupplierDetailsSerializer



class VoucherPurchaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling Purchase Vouchers with all details tables.
    """
    serializer_class = VoucherPurchaseSupplierDetailsSerializer

    def get_queryset(self):
        from core.tenant import get_tenant_from_request
        from django.db.models import Q
        tenant_id = get_tenant_from_request(self.request) or getattr(self.request.user, 'tenant_id', None) or getattr(self.request.user, 'branch_id', None)

        queryset = VoucherPurchaseSupplierDetails.objects.all().select_related(
            'due_details', 'transit_details', 'supply_foreign_details', 'supply_inr_details'
        )

        if tenant_id:
            tenant_qs = queryset.filter(
                Q(tenant_id=tenant_id) | Q(tenant_id='default-tenant') | Q(tenant_id__isnull=True) | Q(tenant_id='')
            )
            if tenant_qs.exists() or self.action in ('retrieve', 'update', 'partial_update'):
                queryset = tenant_qs

        # For detail (retrieve/update/partial_update) actions, always return all records.
        if self.action in ('retrieve', 'update', 'partial_update'):
            return queryset.order_by('-date', '-created_at')

        # Optional: show_all=true to skip 'to_pay' and 'payment' exclusion
        show_all = self.request.query_params.get('show_all') == 'true'

        if not show_all:
            queryset = queryset.filter(
                due_details__to_pay__isnull=False,
                due_details__to_pay__gt=0
            )

        vendor_name = self.request.query_params.get('vendor_name')
        if vendor_name and vendor_name.strip():
            queryset = queryset.filter(vendor_name__iexact=vendor_name.strip())

        branch = self.request.query_params.get('branch')
        if branch and branch.strip():
            queryset = queryset.filter(branch__iexact=branch.strip())

        return queryset.order_by('-date', '-created_at')

    def get_object(self):
        """
        Resolve Purchase Voucher by primary key, or generic Voucher reference_id.
        """
        from django.http import Http404
        pk = self.kwargs.get('pk')
        
        # 1. Direct PK match on VoucherPurchaseSupplierDetails
        direct_instance = VoucherPurchaseSupplierDetails.objects.filter(pk=pk).select_related(
            'due_details', 'transit_details', 'supply_foreign_details', 'supply_inr_details'
        ).first()
        if direct_instance:
            self.check_object_permissions(self.request, direct_instance)
            return direct_instance

        # 2. Try to find via the generic Voucher table using reference_id
        generic_voucher = Voucher.objects.filter(id=pk, type='purchase').first()
        if generic_voucher and generic_voucher.reference_id:
            ref_instance = VoucherPurchaseSupplierDetails.objects.filter(pk=generic_voucher.reference_id).first()
            if ref_instance:
                self.check_object_permissions(self.request, ref_instance)
                return ref_instance

        # 3. Match by voucher_id string
        instance = VoucherPurchaseSupplierDetails.objects.filter(voucher_id=pk).first()
        if instance:
            self.check_object_permissions(self.request, instance)
            return instance

        raise Http404("Purchase voucher not found.")

    def update(self, request, *args, **kwargs):
        """
        Override to wrap update in atomic transaction and return 200.
        Supports both PUT and PATCH (partial update).
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            with db_transaction.atomic():
                updated_instance = serializer.save()
            return Response(self.get_serializer(updated_instance).data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            print(f"!!! Error in PurchaseVoucher update: {str(e)}\n{traceback.format_exc()}")
            return Response(
                {"message": f"Failed to update purchase voucher: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        from core.tenant import get_tenant_from_request
        tenant_id = get_tenant_from_request(self.request) or getattr(self.request.user, 'tenant_id', None) or getattr(self.request.user, 'branch_id', None)
        serializer.save(tenant_id=tenant_id)

    @action(detail=False, methods=['post'], url_path='validate-voucher')
    def validate_voucher(self, request):
        """
        Strict check for duplicate vouchers.
        """
        from core.tenant import get_tenant_from_request
        tenant_id = get_tenant_from_request(request) or getattr(request.user, 'tenant_id', None) or getattr(request.user, 'branch_id', None)

        supplier_invoice_no = request.data.get('supplier_invoice_no', '').strip()
        gstin = request.data.get('gstin', '').strip()
        branch = request.data.get('branch', '').strip()
        vendor_name = request.data.get('vendor_name', '').strip()

        exists = VoucherPurchaseSupplierDetails.objects.filter(
            tenant_id=tenant_id,
            supplier_invoice_no__iexact=supplier_invoice_no,
            gstin__iexact=gstin,
            branch__iexact=branch
        ).exists()

        # Shadow Check
        from vendors.vendor_validation_logic import normalize_invoice_number, append_shadow_evidence
        import logging
        norm_inv_no = normalize_invoice_number(supplier_invoice_no)
        new_match = False
        if norm_inv_no:
            new_match = VoucherPurchaseSupplierDetails.objects.filter(
                tenant_id=tenant_id,
                normalized_invoice_no=norm_inv_no,
                gstin__iexact=gstin,
                branch__iexact=branch
            ).exists()
        
        old_match = exists
        
        logging.getLogger(__name__).info(
            f"[DUPLICATE_SHADOW_CHECK] "
            f"record_id=None "
            f"invoice_no='{supplier_invoice_no}' "
            f"normalized_invoice_no='{norm_inv_no}' "
            f"old_match={old_match} "
            f"new_match={new_match}"
        )
        append_shadow_evidence(None, supplier_invoice_no, norm_inv_no, old_match, new_match)


        if exists:
            return Response({
                "status": "DUPLICATE",
                "voucher_status": "Duplicate Voucher"
            })
        else:
            return Response({
                "status": "UNIQUE",
                "voucher_status": "Unique Voucher"
            })

    @action(detail=True, methods=['post'], url_path='send-email')
    def send_email(self, request, pk=None):
        """
        Manually trigger email dispatch for a specific Purchase Voucher.
        Accepts optional `recipient_email` in request data to override default vendor email.
        """
        voucher_obj = self.get_object()
        recipient_email = request.data.get('recipient_email')
        
        # Fallback to vendor basic detail email if not present
        if not recipient_email and hasattr(voucher_obj, 'vendor_basic_detail') and voucher_obj.vendor_basic_detail:
            recipient_email = getattr(voucher_obj.vendor_basic_detail, 'email', None)

        if not recipient_email:
            return Response(
                {'success': False, 'message': 'No recipient email provided. Please enter a valid vendor email.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from .services.purchase_voucher_mail_service import send_purchase_voucher_email
            result = send_purchase_voucher_email(
                voucher_obj=voucher_obj,
                recipient_email=recipient_email
            )
            if result.get('success'):

                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(
                {'success': False, 'message': f'Failed to send email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )






