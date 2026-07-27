import re
from typing import List, Dict, Any, Optional, Set
from ..models.dto import QueryIntent, SchemaMatch
from ..exceptions.kiki_exceptions import QueryBuilderException
from ..config.settings import KikiSettings
from ..query.entity_resolver import EntityResolver, EntityResolution
from ..query.business_object_resolver import BusinessObjectResolver, BusinessObjectReference
from ..utils.logger import kiki_logger


class QueryBuilder:
    """
    Component 4 — Schema-Aware & Business Graph Query Builder
    Translates QueryIntent into valid, single-path ANSI SELECT SQL.
    Uses Business Object Resolution and explicit Business Relationship Graphs.
    Does NOT produce random or illegal multi-table LEFT JOINs.
    """

    DATE_COLUMN_PRIORITY = [
        "transaction_date",
        "voucher_date",
        "document_date",
        "date",
        "invoice_date",
        "bill_date",
        "created_at",
        "updated_at",
        "id"
    ]

    TEXT_ENTITY_COLUMN_NAMES = [
        "party",
        "vendor_name",
        "customer_name",
        "voucher_name",
        "name",
        "party_name",
        "account",
        "narration"
    ]

    ID_COLUMN_NAMES = [
        "party_customer_id",
        "party_vendor_id",
        "customer_id",
        "vendor_id",
        "ledger_id_val",
        "reference_id"
    ]

    @classmethod
    def build_sql(cls, intent: QueryIntent, schemas: List[SchemaMatch]) -> str:
        """
        Translates QueryIntent into a strictly validated ANSI SQL SELECT statement.
        """
        if not intent or not intent.target_tables:
            raise QueryBuilderException("QueryIntent must specify at least one target_table.")

        if not schemas:
            raise QueryBuilderException("Schema metadata is empty. Cannot build SQL without schema context.")

        schema_map: Dict[str, SchemaMatch] = {s.table_name: s for s in schemas}

        # 1. Business Relationship Graph: Prioritize unified transaction table 'vouchers' if present
        primary_table = None
        if "vouchers" in schema_map:
            primary_table = "vouchers"
        else:
            # Match first valid table
            for t_name in intent.target_tables:
                if t_name in schema_map:
                    primary_table = t_name
                    break

        if not primary_table and schemas:
            primary_table = schemas[0].table_name

        if not primary_table:
            raise QueryBuilderException(
                f"None of the target tables {intent.target_tables} exist in schema metadata."
            )

        primary_schema = schema_map[primary_table]
        primary_col_map: Dict[str, str] = {c["name"].lower(): c["name"] for c in primary_schema.columns}

        # 2. SELECT Clause Construction
        select_expressions: List[str] = []
        is_record_lookup = any(w in intent.objective.lower() for w in ["last", "latest", "recent", "newest", "transaction", "invoice", "voucher", "order", "detail"])

        if intent.metrics and not is_record_lookup:
            for m in intent.metrics:
                m_clean = m.strip().lower()
                matched_col = cls._find_matching_column(m_clean, primary_col_map)

                if matched_col:
                    real_col = primary_col_map[matched_col]
                    if any(agg in m_clean for agg in ["sum", "total", "amount"]):
                        select_expressions.append(f"SUM({primary_table}.{real_col}) AS total_{real_col}")
                    elif any(agg in m_clean for agg in ["count", "number"]):
                        select_expressions.append(f"COUNT({primary_table}.{real_col}) AS count_{real_col}")
                    elif any(agg in m_clean for agg in ["avg", "average"]):
                        select_expressions.append(f"AVG({primary_table}.{real_col}) AS avg_{real_col}")
                    else:
                        select_expressions.append(f"{primary_table}.{real_col}")

        # Fallback to valid columns from primary table if no metric matched or if record lookup
        if not select_expressions:
            for c in primary_schema.columns[:6]:
                select_expressions.append(f"{primary_table}.{c['name']}")


        select_clause = "SELECT " + ", ".join(select_expressions)

        # 3. FROM Clause (Clean Single-Table or Strict FK Path ONLY)
        from_clause = f"FROM {primary_table}"
        joins_str = ""  # Zero random joins

        # 4. Schema-Aware WHERE Clause & Business Object Resolution
        where_conditions: List[str] = []

        # Check transaction type filter (purchase, sales, etc.)
        obj_lower = intent.objective.lower()
        if "vouchers" in primary_table:
            if any(w in obj_lower for w in ["purchase", "vendor", "supplier", "buy"]):
                where_conditions.append(f"{primary_table}.type = 'purchase'")
            elif any(w in obj_lower for w in ["sale", "sales", "revenue", "customer", "invoice"]):
                where_conditions.append(f"{primary_table}.type = 'sales'")

        if intent.entity:
            # Business Object Resolution
            bo_ref = BusinessObjectResolver.resolve(intent.objective, entity_name=intent.entity)
            search_name = bo_ref.resolved_name or intent.entity
            entity_val = search_name.replace("'", "''")

            text_col = cls._find_text_entity_column(primary_col_map)
            if text_col:
                real_text_col = primary_col_map[text_col]
                where_conditions.append(f"{primary_table}.{real_text_col} LIKE '%%{entity_val}%%'")
            elif bo_ref.resolved_id is not None and bo_ref.id_column in primary_col_map:
                real_id_col = primary_col_map[bo_ref.id_column]
                where_conditions.append(f"{primary_table}.{real_id_col} = {bo_ref.resolved_id}")

        where_clause = f" WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # 5. Build GROUP BY Clause
        group_clause = ""
        if intent.group_by and any(expr.startswith("SUM(") or expr.startswith("COUNT(") or expr.startswith("AVG(") for expr in select_expressions):
            non_agg_cols = [expr for expr in select_expressions if not any(expr.startswith(agg) for agg in ["SUM(", "COUNT(", "AVG("])]
            if non_agg_cols:
                group_clause = " GROUP BY " + ", ".join([c.split(" AS ")[0] for c in non_agg_cols])

        # 6. Schema-Aware ORDER BY Clause
        order_clause = ""
        valid_orders: List[str] = []

        if intent.order_by:
            for ob in intent.order_by:
                ob_clean = ob.strip()
                tokens = ob_clean.split()
                col_part = tokens[0].lower()
                dir_part = tokens[1].upper() if len(tokens) > 1 else "ASC"

                if col_part in primary_col_map:
                    real_col = primary_col_map[col_part]
                    valid_orders.append(f"{primary_table}.{real_col} {dir_part}")
                else:
                    resolved_date_col = cls._resolve_date_column(primary_col_map)
                    if resolved_date_col:
                        real_date_col = primary_col_map[resolved_date_col]
                        valid_orders.append(f"{primary_table}.{real_date_col} {dir_part}")

        # If user asked for latest/last transaction and no order clause built yet
        if not valid_orders and any(w in intent.objective.lower() for w in ["last", "latest", "newest", "recent"]):
            resolved_date_col = cls._resolve_date_column(primary_col_map)
            if resolved_date_col:
                real_date_col = primary_col_map[resolved_date_col]
                valid_orders.append(f"{primary_table}.{real_date_col} DESC")

        if valid_orders:
            order_clause = " ORDER BY " + ", ".join(valid_orders)

        # 7. Build LIMIT Clause
        row_limit = min(intent.limit or 100, KikiSettings.MAX_ROWS_PER_QUERY)
        limit_clause = f" LIMIT {row_limit}"

        sql = f"{select_clause} {from_clause}{joins_str}{where_clause}{group_clause}{order_clause}{limit_clause};"
        
        cls._validate_final_sql(sql, schema_map)
        kiki_logger.info(f"QueryBuilder generated SQL: {sql}")
        return sql

    @classmethod
    def _find_matching_column(cls, metric: str, col_map: Dict[str, str]) -> Optional[str]:
        for col_name in col_map:
            if col_name in metric or metric in col_name:
                return col_name
        return None

    @classmethod
    def _find_text_entity_column(cls, col_map: Dict[str, str]) -> Optional[str]:
        for candidate in cls.TEXT_ENTITY_COLUMN_NAMES:
            if candidate in col_map:
                return candidate
        for col_name in col_map:
            if "name" in col_name or "party" in col_name:
                return col_name
        return None

    @classmethod
    def _resolve_date_column(cls, col_map: Dict[str, str]) -> Optional[str]:
        for date_col in cls.DATE_COLUMN_PRIORITY:
            if date_col in col_map:
                return date_col
        return None

    @classmethod
    def _validate_final_sql(cls, sql: str, schema_map: Dict[str, SchemaMatch]):
        clean_sql = sql.strip().upper()
        if not (clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")):
            raise QueryBuilderException(f"Invalid SQL structure generated: {sql}")
