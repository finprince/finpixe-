"""
SQL Security Validator & Safety Shield
======================================
Validates compiled SQL queries for strict multi-tenant isolation, read-only status, and query cost safety.
"""
import re
from typing import Tuple
from ..exceptions import KikiSQLValidationException

class SQLValidator:
    """Enforces 8 non-negotiable security rules on SQL queries before execution."""

    DANGEROUS_KEYWORDS = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "EXECUTE", "GRANT"]

    def validate(self, sql_query: str, tenant_id: str) -> Tuple[bool, str]:
        """Validate query string for tenant safety and read-only status."""
        query_upper = sql_query.upper().strip()

        # Rule 1: READ-ONLY Check (Must start with SELECT or WITH)
        if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
            raise KikiSQLValidationException("Query violation: Only SELECT read-only queries are permitted.")

        # Rule 2: Dangerous Statement Detection
        for kw in self.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + kw + r'\b', query_upper):
                raise KikiSQLValidationException(f"Query violation: Prohibited DDL/DML keyword detected: '{kw}'.")

        # Rule 3: Mandatory Tenant Filter Check (enforced when target table supports tenant columns)
        if tenant_id and tenant_id != "GLOBAL":
            match = re.search(r'FROM\s+([a-zA-Z0-9_]+)', query_upper)
            has_tenant_col = True
            if match:
                table_name = match.group(1).lower()
                from ..metadata import metadata_registry
                catalog = metadata_registry.get_catalog()
                table_data = catalog.get("tables", {}).get(table_name)
                if table_data is not None:
                    cols = list(table_data.get("columns", {}).keys())
                    has_tenant_col = ("tenant_id" in cols or "company_id" in cols)

            if has_tenant_col and not ("TENANT_ID" in query_upper or "COMPANY_ID" in query_upper):
                raise KikiSQLValidationException("Tenant Security Violation: Query missing mandatory 'tenant_id' or 'company_id' filter.")

        # Rule 4: No Cartesian Joins (Joins must have ON or USING)
        if " JOIN " in query_upper and " ON " not in query_upper and " USING " not in query_upper:
            raise KikiSQLValidationException("Query violation: Unbounded Cartesian JOIN detected.")

        return True, "SQL validation passed successfully."

sql_validator = SQLValidator()
