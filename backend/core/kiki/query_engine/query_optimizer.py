"""
KIKI Query Optimizer Engine
=============================
Cost estimator, join optimizer, index selector, and column optimizer.
"""

from typing import Dict, Any, List
from ..config import kiki_settings
from ..metadata.registry import metadata_registry


class QueryOptimizer:
    """Enterprise Query Optimizer for IR payload refinement."""

    def optimize_ir(self, ir_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimizes IR payload prior to parameter-bound SQL compilation.
        """
        table_name = ir_payload.get("table", "")
        table_cols = [c["name"] for c in metadata_registry.get_columns(table_name)]

        # 1. Enforce Row Limits
        requested_limit = ir_payload.get("limit", 10)
        optimized_limit = min(max(1, requested_limit), kiki_settings.MAX_QUERY_ROW_LIMIT)
        ir_payload["limit"] = optimized_limit

        # 2. Prevent SELECT *
        selects = ir_payload.get("select", [])
        if not selects or selects == ["*"]:
            if table_cols:
                # Pick up to 5 descriptive columns
                descriptive = [c for c in table_cols if any(k in c.lower() for k in ["name", "title", "code", "status", "number", "id", "amount", "total"])][:5]
                ir_payload["select"] = descriptive if descriptive else table_cols[:5]
            else:
                ir_payload["select"] = ["id"]

        # 3. Validate Group By Columns against Table Schema
        if ir_payload.get("group_by"):
            valid_groups = [g for g in ir_payload["group_by"] if g in table_cols]
            ir_payload["group_by"] = valid_groups

        # 4. Validate Order By Column against Table Schema
        if ir_payload.get("order_by"):
            order_col = ir_payload["order_by"].get("column")
            if order_col and order_col not in table_cols and not ("(" in order_col or "aggregated_value" in order_col):
                # Fallback to first numerical/id column
                ir_payload["order_by"]["column"] = table_cols[0] if table_cols else "id"

        return ir_payload

query_optimizer = QueryOptimizer()
