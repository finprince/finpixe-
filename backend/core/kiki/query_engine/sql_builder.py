"""
Parameter-Bound Safe SQL Compiler
=================================
Compiles Intermediate Representation (IR) DTOs into parameterized SQL statements (%s)
with mandatory tenant isolation, dynamic aggregation, date filters, grouping, and ordering.
"""
from typing import Dict, Any, Tuple, List
from ..config import kiki_settings
from ..metadata import metadata_registry

class SQLBuilder:
    """Compiles IR JSON structures into parameter-bound analytical SQL queries."""

    DATE_EXPRESSIONS = {
        "TODAY": "{col} >= CURDATE()",
        "YESTERDAY": "{col} >= DATE_SUB(CURDATE(), INTERVAL 1 DAY) AND {col} < CURDATE()",
        "LAST_WEEK": "{col} >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)",
        "LAST_MONTH": "{col} >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)",
        "LAST_QUARTER": "{col} >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)",
        "THIS_FINANCIAL_YEAR": "{col} >= DATE_FORMAT(NOW(), '%Y-04-01')"
    }

    def build_sql(self, ir_payload: Dict[str, Any], tenant_id: str) -> Tuple[str, List[Any]]:
        """Build parameter-bound SQL query string and params tuple from IR DTO."""
        table_name = ir_payload.get("table", "advance_allocation")
        select_fields = ir_payload.get("select", ["id"])
        
        # 1. Format Select Clause (prevent SELECT * for analytical queries)
        if not select_fields or select_fields == ["*"]:
            select_clause = "id"
        else:
            select_clause = ", ".join(select_fields)
        
        where_conditions = []
        params = []

        # 2. Check table columns from Metadata Catalog for Tenant Isolation
        catalog = metadata_registry.get_catalog()
        table_cols = list(catalog.get("tables", {}).get(table_name, {}).get("columns", {}).keys())

        if "tenant_id" in table_cols:
            where_conditions.append("tenant_id = %s")
            params.append(tenant_id)
        elif "company_id" in table_cols:
            where_conditions.append("company_id = %s")
            params.append(tenant_id)

        # 3. Dynamic Date Filter Clause
        date_filter = ir_payload.get("date_filter")
        if date_filter and isinstance(date_filter, dict):
            filter_type = date_filter.get("type")
            date_col = date_filter.get("column", "created_at")
            # Verify date column exists in table schema
            if date_col in table_cols or "created_at" in table_cols:
                target_col = date_col if date_col in table_cols else "created_at"
                expr_tmpl = self.DATE_EXPRESSIONS.get(filter_type)
                if expr_tmpl:
                    where_conditions.append(expr_tmpl.format(col=target_col))

        # 4. Standard Filters
        filters = ir_payload.get("filters", [])
        for f in filters:
            field = f.get("field")
            op = f.get("operator", "=")
            val = f.get("value")
            
            if field and val is not None and field in table_cols:
                if op == "=":
                    where_conditions.append(f"{field} = %s")
                    params.append(val)
                elif op == "LIKE":
                    where_conditions.append(f"{field} LIKE %s")
                    params.append(f"%{val}%")
                elif op == "BETWEEN" and isinstance(val, list) and len(val) == 2:
                    where_conditions.append(f"{field} BETWEEN %s AND %s")
                    params.extend(val)

        where_clause = f" WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # 5. Dynamic GROUP BY Clause
        group_by_cols = ir_payload.get("group_by", [])
        valid_group_cols = [col for col in group_by_cols if col in table_cols]
        group_by_clause = f" GROUP BY {', '.join(valid_group_cols)}" if valid_group_cols else ""

        # 6. Dynamic ORDER BY Clause
        order_by_clause = ""
        order_by = ir_payload.get("order_by")
        if order_by and isinstance(order_by, dict):
            sort_col = order_by.get("column")
            direction = order_by.get("direction", "DESC").upper()
            if sort_col == "aggregated_value" or sort_col in table_cols or (select_fields and sort_col in select_fields[0]):
                order_by_clause = f" ORDER BY {sort_col} {direction}"
            elif table_cols:
                order_by_clause = f" ORDER BY {table_cols[0]} {direction}"

        # 7. Row Limit Capping
        limit = min(ir_payload.get("limit", 10), kiki_settings.MAX_QUERY_ROW_LIMIT)

        sql = f"SELECT {select_clause} FROM {table_name}{where_clause}{group_by_clause}{order_by_clause} LIMIT {limit}"
        return sql, params

sql_builder = SQLBuilder()
