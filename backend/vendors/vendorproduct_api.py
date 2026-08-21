"""
API ViewSet for Vendor Master Products and Services.
New design: one-record-per-vendor with a JSON items array.
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
import logging

from .vendorproduct_serializers import (
    VendorProductServiceCreateSerializer,
    VendorProductServiceUpdateSerializer,
)
from .vendorproduct_database import VendorProductServiceDatabase

logger = logging.getLogger(__name__)


class VendorProductServiceViewSet(viewsets.ViewSet):
    """
    ViewSet for Vendor Products & Services (JSON-array design).

    Endpoints:
      POST   /api/vendors/product-services/
             Body: { vendor_basic_detail: <id>, items: [{...}, ...] }
             → Upserts the JSON items array for that vendor.

      GET    /api/vendors/product-services/
             ?vendor_basic_detail=<id>  → single vendor record
             (no param)                 → all records for tenant

      PATCH  /api/vendors/product-services/<vendor_id>/
             Body: { items: [{...}, ...] }
             → Replaces the items array for that vendor.

      DELETE /api/vendors/product-services/<vendor_id>/
             → Soft-deletes the record.
    """

    permission_classes = [IsAuthenticated]

    # ── helpers ────────────────────────────────────────────────────────────────

    def _tenant_id(self):
        user = self.request.user
        if user.is_anonymous:
            return 'default_tenant'
        if hasattr(user, 'tenant_id') and user.branch_id:
            return user.branch_id
        if hasattr(user, 'tenant') and hasattr(user.tenant, 'tenant_id'):
            return user.tenant.tenant_id
        return str(getattr(user, 'id', 'default_tenant'))

    # ── CREATE / UPSERT ────────────────────────────────────────────────────────

    def create(self, request, *args, **kwargs):
        """
        POST /api/vendors/product-services/
        Body: { vendor_basic_detail: <id>, items: [{item_name, ...}, ...] }
        """
        serializer = VendorProductServiceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Product service serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        vd = serializer.validated_data
        tenant_id = self._tenant_id()
        vendor_id = vd['vendor_basic_detail']
        items = vd['items']

        logger.info(
            f"POST product-services: tenant={tenant_id}, vendor={vendor_id}, "
            f"item_count={len(items)}"
        )

        try:
            record = VendorProductServiceDatabase.upsert_product_services(
                tenant_id=tenant_id,
                vendor_basic_detail_id=vendor_id,
                items=items,
                created_by=request.user.username,
            )
            return Response(record, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error saving product services: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='match-existing')
    def match_existing(self, request):
        """
        POST /api/vendors/product-services/match-existing/
        Matches selected Item Code + Item Name against Inventory Item Master and creates vendor-product link.
        """
        data = request.data
        item_code = str(data.get('item_code') or '').strip()
        item_name = str(data.get('item_name') or '').strip()
        hsn_sac_code = str(data.get('hsn_sac_code') or data.get('hsn_code') or '').strip()
        supplier_item_code = str(data.get('supplier_item_code') or '').strip()
        supplier_item_name = str(data.get('supplier_item_name') or '').strip()
        vendor_id = data.get('vendor_basic_detail') or data.get('vendor_id')

        if not item_code or not item_name:
            return Response(
                {"error": "Both Item Code and Item Name are required to match an existing item."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from inventory.models import InventoryItem
        tenant_id = self._tenant_id()

        # Query existing item from InventoryItem with normalized comparison
        matched_item = None
        qs = InventoryItem.objects.filter(
            item_code__iexact=item_code,
            item_name__iexact=item_name,
            is_active=True
        )
        if tenant_id and tenant_id != 'default_tenant':
            matched_item = qs.filter(tenant_id=tenant_id).first()
        if not matched_item:
            matched_item = qs.first()

        if not matched_item:
            return Response(
                {
                    "error": f"No matching existing item found in Item Master with Item Code '{item_code}' and Item Name '{item_name}'."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        vendor_mapped = False
        if vendor_id:
            try:
                VendorProductServiceDatabase.link_single_item(
                    tenant_id=tenant_id,
                    vendor_basic_detail_id=int(vendor_id),
                    item_code=matched_item.item_code,
                    item_name=matched_item.item_name,
                    hsn_sac_code=matched_item.hsn_code or hsn_sac_code,
                    supplier_item_code=supplier_item_code,
                    supplier_item_name=supplier_item_name,
                    created_by=request.user.username if request.user and hasattr(request.user, 'username') else 'system'
                )
                vendor_mapped = True
            except Exception as e:
                logger.error(f"Error mapping vendor product: {e}", exc_info=True)

        return Response({
            "success": True,
            "matched": True,
            "vendor_mapped": vendor_mapped,
            "item": {
                "id": matched_item.id,
                "item_code": matched_item.item_code,
                "item_name": matched_item.item_name,
                "hsn_code": matched_item.hsn_code or hsn_sac_code,
                "uom": matched_item.uom,
                "rate": str(matched_item.rate),
                "gst_rate": str(matched_item.gst_rate) if matched_item.gst_rate is not None else None,
            },
            "message": f"Successfully matched with Item Master: \"{matched_item.item_name}\" ({matched_item.item_code})."
        }, status=status.HTTP_200_OK)

    # ── LIST / RETRIEVE ────────────────────────────────────────────────────────

    def list(self, request, *args, **kwargs):
        """
        GET /api/vendors/product-services/?vendor_basic_detail=<id>
        """
        tenant_id = self._tenant_id()
        vendor_id = request.query_params.get('vendor_basic_detail') or request.query_params.get('vendor_id')

        try:
            if vendor_id:
                record = VendorProductServiceDatabase.get_by_vendor(int(vendor_id))
                if not record:
                    return Response({'vendor_basic_detail': vendor_id, 'items': []})
                return Response(record)
            else:
                records = VendorProductServiceDatabase.get_by_tenant(tenant_id)
                return Response(records)
        except Exception as e:
            logger.error(f"Error fetching product services: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None, *args, **kwargs):
        """GET /api/vendors/product-services/<vendor_id>/"""
        try:
            record = VendorProductServiceDatabase.get_by_vendor(int(pk))
            if not record:
                return Response({'vendor_basic_detail': pk, 'items': []})
            return Response(record)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── UPDATE ─────────────────────────────────────────────────────────────────

    def partial_update(self, request, pk=None, *args, **kwargs):
        """PATCH /api/vendors/product-services/<vendor_id>/"""
        serializer = VendorProductServiceUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        tenant_id = self._tenant_id()
        vendor_id = int(pk)
        items = serializer.validated_data['items']

        try:
            record = VendorProductServiceDatabase.upsert_product_services(
                tenant_id=tenant_id,
                vendor_basic_detail_id=vendor_id,
                items=items,
                created_by=request.user.username,
            )
            return Response(record)
        except Exception as e:
            logger.error(f"Error updating product services: {e}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ── DELETE ─────────────────────────────────────────────────────────────────

    def destroy(self, request, pk=None, *args, **kwargs):
        """DELETE /api/vendors/product-services/<vendor_id>/"""
        try:
            VendorProductServiceDatabase.delete_by_vendor(int(pk))
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
