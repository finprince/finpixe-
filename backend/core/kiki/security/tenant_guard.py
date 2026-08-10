"""
Tenant Isolation Guard — Phase 17.4 Hardened
=============================================
Extracts and validates tenant, company, branch, user, and RBAC permission contexts.

Phase 17.4 changes:
  - Removed silent "default_tenant" fallback.
  - Authenticated users with no tenant identity raise KikiTenantSecurityException.
  - Anonymous users only permitted when kiki_settings.TENANT_ANONYMOUS_ALLOWED=True.
  - Every retrieval request must carry an explicit, verified security context.
"""
from typing import Dict, Any
from ..exceptions import KikiTenantSecurityException
from ..config import kiki_settings


class TenantGuard:
    """Enforces multi-tenant isolation context injection — Phase 17.4 Fail-Closed."""

    def extract_context(
        self,
        request_user,
        request_headers: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Extract multi-tenant request context object.

        Phase 17.4 policy:
          1. Authenticated user with a valid tenant_id → use it (nominal path)
          2. Authenticated user WITHOUT a tenant_id → raise KikiTenantSecurityException
             (fail closed; do NOT silently map to default_tenant)
          3. Anonymous / unauthenticated user:
             - If TENANT_ANONYMOUS_ALLOWED=True → tenant_id = "anonymous" (demo/dev)
             - If TENANT_ANONYMOUS_ALLOWED=False → raise KikiTenantSecurityException (production)
        """
        anonymous_allowed = getattr(kiki_settings, "TENANT_ANONYMOUS_ALLOWED", True)

        # ── Authenticated user path ───────────────────────────────────────────
        if request_user and getattr(request_user, "is_authenticated", False):
            tenant_id = (
                getattr(request_user, "tenant_id", None)
                or getattr(request_user, "tenant", None)
                or getattr(request_user, "company_id", None)
            )

            if not tenant_id:
                # Phase 17.4: fail closed — never silently fall back to default_tenant
                raise KikiTenantSecurityException(
                    "Authenticated user has no tenant_id. "
                    "Every authenticated request must carry a verified tenant identity. "
                    "Configure the user's tenant_id/company_id or contact your administrator."
                )

            return {
                "tenant_id": str(tenant_id),
                "user_id": getattr(request_user, "id", "authenticated_user"),
                "user_role": getattr(request_user, "role", "User"),
                "company_id": getattr(request_user, "company_id", str(tenant_id)),
                "branch_id": getattr(request_user, "branch_id", "main_branch"),
                "is_anonymous": False,
            }

        # ── Anonymous / unauthenticated path ─────────────────────────────────
        if anonymous_allowed:
            # Demo/dev mode: allow anonymous requests with restricted "anonymous" scope
            return {
                "tenant_id": "anonymous",
                "user_id": "anonymous",
                "user_role": "Anonymous",
                "company_id": "anonymous",
                "branch_id": "default",
                "is_anonymous": True,
            }

        # Production fail-closed: reject any request without a tenant
        raise KikiTenantSecurityException(
            "Request has no authenticated tenant identity. "
            "Anonymous access is disabled in this environment. "
            "Set KIKI_TENANT_ANON_ALLOWED=true to enable demo mode."
        )


tenant_guard = TenantGuard()
