from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

class BranchQuerysetMixin:
    """
    Mixin to filter querysets by tenant_id automatically.
    Enforces isolation between Master Admin and Company domains.
    """
    def get_queryset(self):
        try:
            qs = super().get_queryset()
            user = self.request.user
            
            # 1. Domain Separation Guard
            MasterUser = apps.get_model('core', 'MasterUser')
            if user and isinstance(user, MasterUser):
                # SECURITY POLICY: Master Admins must NOT access company APIs directly.
                # Use dedicated reporting endpoints instead.
                raise PermissionDenied("Master Admin cannot access company-domain APIs directly.")

            # 2. Standard Business User isolation
            tid = getattr(user, 'tenant_id', None)
            
            # Fallback to request.tenant_id or default tenant for active session
            if not tid:
                tid = getattr(self.request, 'tenant_id', None)
            if not tid and user and user.is_authenticated:
                tid = '6d114c1e-647d-4884-b385-f3d806547476'
            
            if tid:
                return qs.filter(tenant_id=tid)
                
            return qs.all()
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error(f"TenantQuerysetMixin error: {str(e)}", exc_info=True)
            return qs.none()

# CompanyQuerysetMixin removed - use BranchQuerysetMixin instead


class IsBranchMember(permissions.BasePermission):
    """
    Permission to check if the user is a valid member of a tenant.
    Requirement #7: Multi-tenant safety.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
            
        # Allow Master Admin (Platform Level) to access views
        MasterUser = apps.get_model('core', 'MasterUser')
        if isinstance(request.user, MasterUser) or getattr(request.user, 'is_superuser', False):
            return True
            
        tenant_id = getattr(request.user, 'tenant_id', None)
        if tenant_id is None:
            tenant_id = getattr(request, 'tenant_id', None)
        if tenant_id is None:
            return False
            
        return True

class BranchModelSerializerMixin:
    """
    Mixin to automatically inject tenant_id during create and update operations.
    """
    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and hasattr(user, 'tenant_id') and user.tenant_id:
            validated_data['tenant_id'] = user.tenant_id
        else:
            raise PermissionDenied("Authentication with a valid Branch ID is required.")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and hasattr(user, 'tenant_id') and user.tenant_id:
            validated_data['tenant_id'] = user.tenant_id
        else:
            raise PermissionDenied("Authentication with a valid Branch ID is required to update.")
        return super().update(instance, validated_data)
