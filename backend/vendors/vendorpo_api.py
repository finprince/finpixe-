"""
API endpoints for Vendor Purchase Order Transactions
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import PermissionDenied

from .models import VendorTransactionPO, VendorTransactionPOItem
from .vendorpo_serializers import VendorPOSerializer, VendorPOCreateSerializer, VendorPOItemSerializer
from . import vendorpo_database as db


class VendorPOViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vendor Purchase Orders
    
    Endpoints:
    - GET /api/vendors/purchase-orders/ - List all POs
    - POST /api/vendors/purchase-orders/ - Create new PO
    - GET /api/vendors/purchase-orders/{id}/ - Get specific PO
    - PUT /api/vendors/purchase-orders/{id}/ - Update PO
    - DELETE /api/vendors/purchase-orders/{id}/ - Delete PO
    - POST /api/vendors/purchase-orders/{id}/update_status/ - Update PO status
    """
    
    queryset = VendorTransactionPO.objects.all()
    serializer_class = VendorPOSerializer
    permission_classes = [IsAuthenticated]
    
    def get_tenant_id(self, request):
        """Extract tenant_id from the authenticated user"""
        user = request.user
        tid = getattr(user, 'tenant_id', None) or getattr(user, 'branch_id', None)
        
        if tid:
            return str(tid)
        
        # If not, raise an error
        raise PermissionDenied("User has no associated tenant")
    
    def list(self, request):
        """
        List all purchase orders for the tenant
        """
        try:
            tenant_id = self.get_tenant_id(request)
            status_filter = request.query_params.get('status')
            vendor_name = request.query_params.get('vendor_name')
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[VendorPOViewSet] Listing POs. tenant_id={tenant_id}, status={status_filter}, vendor_name={vendor_name}")
            
            po_list = db.get_all_purchase_orders(tenant_id, status_filter, vendor_name)
            logger.info(f"[VendorPOViewSet] Found {len(po_list)} POs")
            
            return Response({
                'success': True,
                'data': po_list,
                'count': len(po_list)
            }, status=status.HTTP_200_OK)
           
        except PermissionDenied as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def create(self, request):
        """
        Create new purchase order with items
        """
        try:
            tenant_id = self.get_tenant_id(request)
            data = request.data
            
            # Validate using serializer
            serializer = VendorPOCreateSerializer(data=data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            validated_data = serializer.validated_data
            
            # Extract PO data and items
            items_data = validated_data.pop('items', [])
            
            # Create PO
            try:


                
                po_id = db.create_purchase_order(
                    tenant_id=tenant_id,
                    po_data=validated_data,
                    items_data=items_data,
                    created_by=request.user.username if hasattr(request.user, 'username') else None
                )
                

                
            except Exception as e:
                import traceback


                raise
            
            # Fetch the created PO
            created_po = db.get_purchase_order_by_id(po_id)
            
            return Response({
                'success': True,
                'message': 'Purchase Order created successfully',
                'data': created_po
            }, status=status.HTTP_201_CREATED)
            
        except PermissionDenied as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            import traceback
            traceback.print_exc()
            with open('err.txt', 'w') as f2: f2.write(str(e) + '\n' + traceback.format_exc())
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def update(self, request, pk=None):
        """
        Update an existing purchase order
        """
        try:
            tenant_id = self.get_tenant_id(request)
            data = request.data
            
            serializer = VendorPOCreateSerializer(data=data)
            if not serializer.is_valid():
                return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
            validated_data = serializer.validated_data
            items_data = validated_data.pop('items', [])
            
            try:
                db.update_purchase_order(
                    po_id=pk,
                    tenant_id=tenant_id,
                    po_data=validated_data,
                    items_data=items_data,
                    updated_by=request.user.username if hasattr(request.user, 'username') else None
                )
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise
                
            updated_po = db.get_purchase_order_by_id(pk)
            
            return Response({
                'success': True,
                'message': 'Purchase Order updated successfully',
                'data': updated_po
            }, status=status.HTTP_200_OK)
            
        except PermissionDenied as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """
        Get specific purchase order by ID
        """
        try:
            po = db.get_purchase_order_by_id(pk)
            
            if not po:
                return Response({
                    'success': False,
                    'error': 'Purchase Order not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'data': po
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update PO status.
        For cancel actions, automatically resolves 'Cancelled' vs 'Executed Cancelled'
        based on whether the PO was used in any GRN or Purchase Voucher.
        If new_status is 'Mailed' (Approve & Mail), sends the PO email to recipients.
        """
        try:
            from .po_mail_service import send_purchase_order_email

            new_status = request.data.get('status')
            
            if not new_status:
                return Response({
                    'success': False,
                    'error': 'Status is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Smart cancellation: check GRN/Voucher usage to decide final status
            if new_status in ('Cancelled', 'Executed Cancelled'):
                new_status = db.resolve_cancellation_status(pk)
            
            recipient_email = request.data.get('recipient_email') or request.data.get('email') or request.data.get('email_address')

            success = db.update_po_status(
                po_id=pk,
                status=new_status,
                updated_by=request.user.username if hasattr(request.user, 'username') else None,
                email_address=recipient_email
            )
            
            if not success:
                return Response({
                    'success': False,
                    'error': 'Purchase Order not found or update failed'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Fetch updated PO
            updated_po = db.get_purchase_order_by_id(pk)

            # If status is Mailed or send_email requested, dispatch the PO email
            email_result = None
            if new_status == 'Mailed' or request.data.get('send_email'):
                email_result = send_purchase_order_email(
                    po_id=pk,
                    sender_user=request.user,
                    recipient_email=recipient_email
                )
            
            msg = f'PO status updated to {new_status}'
            if email_result:
                if email_result.get('success'):
                    msg += f" and emailed to {', '.join(email_result.get('recipients', []))}"
                elif email_result.get('error'):
                    msg += f" (Email note: {email_result.get('error')})"

            return Response({
                'success': True,
                'message': msg,
                'data': updated_po,
                'email_result': email_result
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def send_mail(self, request, pk=None):
        """
        Dedicated endpoint to send / re-send purchase order email.
        """
        try:
            from .po_mail_service import send_purchase_order_email

            recipient_email = request.data.get('recipient_email') or request.data.get('email')
            email_result = send_purchase_order_email(
                po_id=pk,
                sender_user=request.user,
                recipient_email=recipient_email
            )

            if email_result.get('success'):
                # Also update status to Mailed if currently Approved or Draft
                po = db.get_purchase_order_by_id(pk)
                if po and po.get('status') in ('Draft', 'Pending Approval', 'Approved'):
                    db.update_po_status(
                        po_id=pk,
                        status='Mailed',
                        updated_by=request.user.username if hasattr(request.user, 'username') else None
                    )
                    po = db.get_purchase_order_by_id(pk)

                return Response({
                    'success': True,
                    'message': email_result.get('message'),
                    'data': po,
                    'recipients': email_result.get('recipients')
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'success': False,
                    'error': email_result.get('error', 'Failed to send email')
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """
        Download Purchase Order as a PDF document.
        """
        try:
            from django.http import HttpResponse
            from .po_pdf_service import generate_po_pdf
            from .po_mail_service import get_company_details

            po_data = db.get_purchase_order_by_id(pk)
            if not po_data:
                return Response({'error': 'Purchase Order not found'}, status=status.HTTP_404_NOT_FOUND)

            tenant_id = po_data.get('tenant_id', '')
            company_info = get_company_details(tenant_id)

            pdf_bytes = generate_po_pdf(po_data, company_info)
            po_number = po_data.get('po_number', f'PO_{pk}').replace(' ', '_').replace('/', '_')

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="Purchase_Order_{po_number}.pdf"'
            return response

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pending_pos(request):
    """
    Get all pending purchase orders for a specific vendor
    Query Parameter: vendor_id
    """
    try:
        user = request.user
        tenant_id = getattr(user, 'tenant_id', None) or getattr(user, 'branch_id', None)
        
        if not tenant_id:
            return Response({'error': 'User has no tenant'}, status=status.HTTP_403_FORBIDDEN)
            
        tenant_id = str(tenant_id)
        vendor_id = request.query_params.get('vendor_id')
        vendor_name = request.query_params.get('vendor_name')
        
        if not vendor_id and not vendor_name:
            return Response([], status=status.HTTP_200_OK)
            
        po_list = db.get_pending_pos_for_vendor(tenant_id, vendor_id, vendor_name)
        
        # Return in the format requested by user: [{"id": 1, "po_number": "PO000001"}]
        # No extra fields as requested.
        return Response(po_list, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
