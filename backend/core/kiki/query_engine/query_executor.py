"""
Deterministic MySQL Query Executor
==================================
Executes validated, parameter-bound SQL queries against MySQL database with Django connection pooling.
"""
from typing import List, Dict, Any, Tuple
from django.db import connection
from ..security import sql_validator
from ..logging import get_kiki_logger

logger = get_kiki_logger("query_executor")

class QueryExecutor:
    """Executes safe SQL statements against system of record MySQL DB."""

    def execute_query(self, sql_query: str, params: List[Any], tenant_id: str) -> List[Dict[str, Any]]:
        """Validate and execute query against MySQL database."""
        # 1. Validate SQL against safety shield
        sql_validator.validate(sql_query, tenant_id)

        logger.info(f"Executing Query for Tenant '{tenant_id}': {sql_query} | Params: {params}")

        results = []
        with connection.cursor() as cursor:
            cursor.execute(sql_query, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            for row in rows:
                results.append(dict(zip(columns, row)))

        logger.info(f"Query returned {len(results)} records.")
        return results

query_executor = QueryExecutor()
