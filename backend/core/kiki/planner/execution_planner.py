"""
KIKI Execution Planner Module
===============================
Converts natural language user prompts, classified business domains, and 
metadata catalog topology into a complete Analytical Intermediate Representation (IR) DTO.
"""

import re
from typing import Dict, Any, List, Optional
from ..metadata.registry import metadata_registry
from ..ontology.graph import ontology_graph


class ExecutionPlanner:
    """Enterprise AI Execution Planner converting NL to Query IR."""

    # Aggregation keywords mapping
    AGGREGATION_KEYWORDS = {
        "SUM": ["total", "sum", "overall", "aggregate", "revenue", "valuation", "sales", "purchases", "collected", "payable"],
        "COUNT": ["how many", "count", "number of", "total count", "quantity of orders", "total orders", "total invoices"],
        "AVG": ["average", "avg", "mean", "average value", "average order"],
        "MAX": ["highest", "maximum", "max", "largest", "peak", "top selling"],
        "MIN": ["lowest", "minimum", "min", "smallest", "cheapest"]
    }

    # Date filter keywords mapping
    DATE_KEYWORDS = {
        "TODAY": ["today", "today's"],
        "YESTERDAY": ["yesterday", "yesterday's"],
        "LAST_WEEK": ["last week", "past week", "previous week", "last 7 days"],
        "LAST_MONTH": ["last month", "past month", "previous month", "last 30 days", "this month", "current month"],
        "LAST_QUARTER": ["last quarter", "this quarter", "current quarter"],
        "THIS_FINANCIAL_YEAR": ["this financial year", "fy", "this year", "financial year"]
    }

    # Common domain numerical measure columns in FINPIXE MySQL schema
    DOMAIN_MEASURE_COLUMNS = {
        "Sales": ["total_amount", "grand_total", "amount", "total", "taxable_amount", "net_amount", "order_amount"],
        "Purchase": ["total_amount", "grand_total", "purchase_amount", "credit_limit", "amount"],
        "Inventory": ["stock_quantity", "quantity", "unit_price", "valuation", "total_val", "item_quantity"],
        "GST": ["total_taxable_value", "igst_amount", "cgst_amount", "sgst_amount", "tax_amount", "total_gst"],
        "Finance": ["balance", "amount", "debit_amount", "credit_amount", "outstanding_amount", "opening_balance"]
    }

    # Dimension/Grouping column keywords
    DIMENSION_KEYWORDS = {
        "branch": ["branch", "location", "site", "office"],
        "customer": ["customer", "client", "buyer"],
        "vendor": ["vendor", "supplier", "seller"],
        "product": ["product", "item", "inventory"],
        "month": ["month", "monthly", "trend", "by month"]
    }

    def plan(
        self,
        user_message: str,
        domain: str,
        target_table: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive Analytical Query IR DTO.
        """
        msg_lower = user_message.lower()
        table_columns = metadata_registry.get_columns(target_table)
        column_names = [col["name"] for col in table_columns]

        # 1. Detect Aggregation
        aggregation = self._detect_aggregation(msg_lower)
        
        # 2. Resolve Measure Column (Numerical column to aggregate/sort)
        measure_column = self._resolve_measure_column(domain, column_names)

        # 3. Detect Group By Dimensions
        group_by = self._detect_group_by(msg_lower, column_names)

        # 4. Detect Date Range Filter
        date_filter = self._detect_date_filter(msg_lower, column_names)

        # 5. Detect Order By & Limit
        order_by, limit = self._detect_order_by_and_limit(msg_lower, measure_column, column_names)

        # 6. Resolve Select Columns
        select_fields = self._build_select_fields(
            aggregation=aggregation,
            measure_column=measure_column,
            group_by=group_by,
            column_names=column_names
        )

        # Build Execution Plan IR
        ir_payload = {
            "domain": domain,
            "table": target_table,
            "aggregation": aggregation,
            "measure": measure_column,
            "select": select_fields,
            "group_by": group_by,
            "order_by": order_by,
            "date_filter": date_filter,
            "limit": limit,
            "joins": [],
            "tenant_filter": True,
            "tenant_id": tenant_id,
            "planner_confidence": 0.95
        }

        return ir_payload

    def _detect_aggregation(self, msg_lower: str) -> Optional[str]:
        """Detects required SQL aggregation function."""
        for agg, kws in self.AGGREGATION_KEYWORDS.items():
            if any(kw in msg_lower for kw in kws):
                return agg
        return None

    def _resolve_measure_column(self, domain: str, column_names: List[str]) -> Optional[str]:
        """Finds the best numerical measure column for the target domain."""
        preferred_measures = self.DOMAIN_MEASURE_COLUMNS.get(domain, [])
        for pref in preferred_measures:
            for col in column_names:
                if pref.lower() in col.lower():
                    return col
        
        # Fallback: Find any column containing 'amount', 'total', 'val', or 'qty'
        for col in column_names:
            c_lower = col.lower()
            if any(k in c_lower for k in ["amount", "total", "value", "price", "quantity", "val", "qty", "balance"]):
                return col
        return None

    def _detect_group_by(self, msg_lower: str, column_names: List[str]) -> List[str]:
        """Detects grouping dimension columns based on business keywords."""
        group_cols = []
        if "by " in msg_lower or "trend" in msg_lower or "monthly" in msg_lower:
            for dim_name, kws in self.DIMENSION_KEYWORDS.items():
                if any(kw in msg_lower for kw in kws):
                    # Find matching column in schema
                    for col in column_names:
                        if dim_name in col.lower() or any(kw in col.lower() for kw in kws):
                            if col not in group_cols:
                                group_cols.append(col)
                            break
        return group_cols

    def _detect_date_filter(self, msg_lower: str, column_names: List[str]) -> Optional[Dict[str, Any]]:
        """Detects relative date filtering keywords and target date column."""
        # Find date column in table
        date_col = None
        for col in column_names:
            c_lower = col.lower()
            if any(k in c_lower for k in ["date", "created_at", "updated_at", "time", "timestamp"]):
                date_col = col
                break

        if not date_col and column_names:
            date_col = "created_at"

        for filter_type, kws in self.DATE_KEYWORDS.items():
            if any(kw in msg_lower for kw in kws):
                return {
                    "type": filter_type,
                    "column": date_col
                }
        return None

    def _detect_order_by_and_limit(
        self,
        msg_lower: str,
        measure_column: Optional[str],
        column_names: List[str]
    ) -> tuple[Optional[Dict[str, str]], int]:
        """Detects ORDER BY column, direction, and LIMIT."""
        order_by = None
        limit = 10  # Default limit

        # Check for top N (e.g., 'top 10', 'top 5', 'highest 3')
        top_match = re.search(r'\btop\s+(\d+)\b', msg_lower)
        if top_match:
            limit = int(top_match.group(1))

        if any(k in msg_lower for k in ["top", "highest", "largest", "most", "best"]):
            sort_col = measure_column or (column_names[0] if column_names else "id")
            order_by = {"column": sort_col, "direction": "DESC"}
        elif any(k in msg_lower for k in ["lowest", "smallest", "least", "bottom"]):
            sort_col = measure_column or (column_names[0] if column_names else "id")
            order_by = {"column": sort_col, "direction": "ASC"}

        return order_by, limit

    def _build_select_fields(
        self,
        aggregation: Optional[str],
        measure_column: Optional[str],
        group_by: List[str],
        column_names: List[str]
    ) -> List[str]:
        """Builds explicit SELECT field expressions for the IR."""
        selects = []
        if group_by:
            selects.extend(group_by)
        
        if aggregation and measure_column:
            selects.append(f"{aggregation}({measure_column}) AS aggregated_value")
        elif measure_column and not selects:
            selects.append(measure_column)
        
        if not selects:
            descriptive_cols = [c for c in column_names if any(k in c.lower() for k in ["name", "title", "code", "status", "number", "id", "amount", "total"])][:5]
            selects = descriptive_cols if descriptive_cols else column_names[:5]

        return selects

execution_planner = ExecutionPlanner()
