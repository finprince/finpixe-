from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.tenant import get_tenant_from_request
from .models import VendorMasterCategory
from .vendorcategory_serializers import VendorMasterCategorySerializer

class VendorMasterCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vendor Master Category
    Provides CRUD operations for vendor categories
    """
    serializer_class = VendorMasterCategorySerializer

    def get_queryset(self):
        """Filter by tenant_id from request. Only filter is_active for list/tree."""
        tenant_id = get_tenant_from_request(self.request)
        qs = VendorMasterCategory.objects.filter(tenant_id=tenant_id) if tenant_id else VendorMasterCategory.objects.all()
        if self.action in {'list', 'tree'}:
            return qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        """Set tenant_id from request"""
        tenant_id = get_tenant_from_request(self.request)
        serializer.save(tenant_id=tenant_id)

    def destroy(self, request, *args, **kwargs):
        """
        Hard delete if possible. If record is referenced by other data (IntegrityError),
        soft delete (deactivate) and rename to allow immediate reuse of the name.
        """
        from django.db import IntegrityError, transaction
        from django.db.models.deletion import ProtectedError
        import time
        instance = self.get_object()
        try:
            with transaction.atomic():
                instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            if not instance.is_active:
                return Response(status=status.HTTP_204_NO_CONTENT)
            timestamp = int(time.time())
            if instance.subgroup:
                instance.subgroup = f'{instance.subgroup}_rem_{timestamp}'
            elif instance.group:
                instance.group = f'{instance.group}_rem_{timestamp}'
            else:
                instance.category = f'{instance.category}_rem_{timestamp}'
            instance.is_active = False
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        """
        Create a new category with idempotency and reactivation logic.
        If a duplicate is found:
        - If is_active=False, reactivate and return 200 OK.
        - If is_active=True, just return 200 OK (exists).
        """
        tenant_id = get_tenant_from_request(request)
        category = request.data.get('category')
        group = request.data.get('group', '')
        subgroup = request.data.get('subgroup', '')
        existing = VendorMasterCategory.objects.filter(tenant_id=tenant_id, category=category, group=group, subgroup=subgroup).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.save()
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Get categories in a tree structure.
        Always includes standard defaults merged with tenant-specific DB records.
        """
        tenant_id = get_tenant_from_request(request)
        queryset = VendorMasterCategory.objects.filter(tenant_id=tenant_id, is_active=True)
        defaults = ['Raw Material', 'Stores and Spares', 'Packing Material', 'Stock in Trade', 'Fixed Assets', 'Capital Goods', 'Consumables', 'Service']
        tree = {}
        for def_cat in defaults:
            tree[def_cat] = {'groups': {}, 'id': f"default_{def_cat.lower().replace(' ', '_')}"}
        for item in queryset:
            cat_name = item.category
            grp_name = item.group
            sub_name = item.subgroup
            if cat_name not in tree:
                tree[cat_name] = {'groups': {}, 'id': None}
            if not grp_name and (not sub_name):
                tree[cat_name]['id'] = item.id
            if grp_name:
                cat_node = tree[cat_name]
                if grp_name not in cat_node['groups']:
                    cat_node['groups'][grp_name] = {'subgroups': {}, 'id': item.id if not sub_name else None}
                if sub_name:
                    grp_node = cat_node['groups'][grp_name]
                    if sub_name not in grp_node['subgroups']:
                        grp_node['subgroups'][sub_name] = {'items': [], 'id': item.id}
        return Response(tree)