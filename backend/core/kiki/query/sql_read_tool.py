import re
import time
from typing import Dict, List, Any, Tuple, Optional
from django.db import connection
from ..models.dto import QueryResultData
from ..exceptions.kiki_exceptions import SqlValidationException, SqlExecutionException
from ..config.settings import KikiSettings
from ..utils.logger import kiki_logger
from ..utils.helpers import Timer


class SqlReadTool:
    """
    Component 5 — SQL Read Tool
    Executes read-only SQL queries against MySQL database.
    Strictly validates SQL (allows SELECT and WITH only; forbids write/destructive statements and multi-statements).
    Attaches execution metadata (execution_time_ms, row_count, status, timestamp) to output.
    """

    FORBIDDEN_KEYWORDS = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
        "CREATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
        "CALL", "SET", "LOCK", "UNLOCK", "RENAME"
    ]

    @classmethod
    def validate_sql(cls, sql_query: str) -> str:
        """
        Validates that sql_query is a single, read-only SELECT or WITH statement.
        Raises SqlValidationException if safety rules are violated.
        Returns cleaned SQL query string.
        """
        if not sql_query or not isinstance(sql_query, str):
            raise SqlValidationException("SQL query must be a non-empty string.")

        clean_sql = sql_query.strip()

        # Check for multiple statements
        statements = [stmt.strip() for stmt in clean_sql.rstrip(';').split(';') if stmt.strip()]
        if len(statements) > 1:
            raise SqlValidationException("Multiple SQL statements in a single execution are strictly forbidden.")

        # Strip comments
        sql_no_comments = re.sub(r'--.*$', '', clean_sql, flags=re.MULTILINE)
        sql_no_comments = re.sub(r'/\*.*?\*/', '', sql_no_comments, flags=re.DOTALL).strip()

        # Must start with SELECT or WITH
        if not (re.match(r'^(SELECT|WITH)\b', sql_no_comments, re.IGNORECASE)):
            raise SqlValidationException("Only SELECT or WITH queries are permitted.")

        # Check for forbidden keywords as standalone words
        for kw in cls.FORBIDDEN_KEYWORDS:
            pattern = r'\b' + kw + r'\b'
            if re.search(pattern, sql_no_comments, re.IGNORECASE):
                raise SqlValidationException(
                    f"Forbidden keyword '{kw}' detected. Only read-only SELECT operations are permitted."
                )

        return clean_sql

    @classmethod
    def execute_query(
        cls,
        sql_query: str,
        params: tuple = None,
        max_rows: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> QueryResultData:
        """
        Executes a validated read-only SQL query and returns QueryResultData DTO.
        """
        cleaned_sql = cls.validate_sql(sql_query)

        row_limit = max_rows or KikiSettings.MAX_ROWS_PER_QUERY
        timeout = timeout_seconds or KikiSettings.QUERY_TIMEOUT_SECONDS

        # Ensure LIMIT is present
        final_sql = cleaned_sql.rstrip(';')
        if not re.search(r'\bLIMIT\b', final_sql, re.IGNORECASE):
            final_sql = f"{final_sql} LIMIT {row_limit}"

        results: List[Dict[str, Any]] = []
        execution_time_ms = 0.0

        try:
            with Timer() as timer:
                with connection.cursor() as cursor:
                    # Execute with read-only cursor
                    if params:
                        cursor.execute(final_sql, params)
                    else:
                        cursor.execute(final_sql)
                    if cursor.description is not None:

                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        for row in rows:
                            row_dict = {}
                            for col_name, val in zip(columns, row):
                                # Format non-serializable datatypes cleanly
                                if hasattr(val, 'isoformat'):
                                    val = val.isoformat()
                                elif hasattr(val, '__float__') and not isinstance(val, (int, float)):
                                    val = float(val)
                                row_dict[col_name] = val
                            results.append(row_dict)
            execution_time_ms = timer.interval_ms

        except SqlValidationException:
            raise
        except Exception as e:
            kiki_logger.error(f"MySQL execution error for query '{final_sql}': {e}")
            raise SqlExecutionException(f"SQL execution failed against MySQL: {str(e)}") from e

        kiki_logger.info(
            f"Executed query successfully. Rows returned: {len(results)}, Execution time: {execution_time_ms:.2f}ms"
        )

        return QueryResultData(
            rows=results,
            row_count=len(results),
            execution_time_ms=round(execution_time_ms, 2),
            status="SUCCESS",
            timestamp=str(time.time())
        )
