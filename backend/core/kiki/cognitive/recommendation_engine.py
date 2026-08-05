from typing import List, Dict, Any, Optional
from ..models.dto import RecommendationItem
from ..utils.logger import kiki_logger


class RecommendationEngine:
    """
    Component — Recommendation Engine
    Generates intelligent follow-up suggestions and transforms direct navigation routes
    into recommended next actions rather than primary responses.
    """

    DEFAULT_RECOMMENDATIONS = [
        RecommendationItem(title="View Executive Dashboard", action_type="navigate", route="/dashboard", description="Open live workspace metrics"),
        RecommendationItem(title="Export Accounting Summary", action_type="export", description="Download financial report PDF/Excel")
    ]

    KEYWORD_RECOMMENDATION_MAP = {
        "sale": [
            RecommendationItem(title="View Sales Dashboard", action_type="navigate", route="/dashboard?page=sales", description="Analyze daily & monthly sales trends"),
            RecommendationItem(title="Compare Yesterday", action_type="query", description="Compare today's sales with yesterday"),
            RecommendationItem(title="Recent Invoices", action_type="navigate", route="/vouchers?type=sales", description="View recent sales vouchers"),
            RecommendationItem(title="Export Sales Report", action_type="export", description="Download sales report")
        ],
        "purchase": [
            RecommendationItem(title="View Purchase Analytics", action_type="navigate", route="/dashboard?page=purchases", description="Analyze vendor spending & purchase orders"),
            RecommendationItem(title="Review Vendor Spending", action_type="navigate", route="/vendors", description="Check top vendors by volume"),
            RecommendationItem(title="Pending Purchases", action_type="navigate", route="/pending-purchases", description="View unverified purchase vouchers"),
            RecommendationItem(title="Export Purchase Report", action_type="export", description="Download purchase summary")
        ],
        "gst": [
            RecommendationItem(title="Open GST Portal", action_type="navigate", route="/gst", description="Access GST reconciliation hub"),
            RecommendationItem(title="GSTR-1 Reconciliation", action_type="navigate", route="/gst-reconciliation", description="Reconcile filed returns"),
            RecommendationItem(title="Tax Ledger Breakdown", action_type="navigate", route="/vouchers?type=journal", description="View tax vouchers")
        ],
        "bank": [
            RecommendationItem(title="Bank Reconciliation", action_type="navigate", route="/bank-staging", description="Reconcile pending bank statement entries"),
            RecommendationItem(title="Cash & Bank Balance", action_type="navigate", route="/dashboard", description="View liquid assets overview")
        ],
        "vendor": [
            RecommendationItem(title="Vendor Master", action_type="navigate", route="/vendors", description="Manage supplier details and balances"),
            RecommendationItem(title="Outstanding Payables", action_type="navigate", route="/reports?type=payables", description="View aging payables report")
        ],
        "customer": [
            RecommendationItem(title="Customer Portal", action_type="navigate", route="/customerportal", description="View customer accounts and balances"),
            RecommendationItem(title="Outstanding Receivables", action_type="navigate", route="/reports?type=receivables", description="View aging receivables report")
        ],
        "inventory": [
            RecommendationItem(title="Stock Summary", action_type="navigate", route="/inventory", description="View current item stock levels"),
            RecommendationItem(title="Reorder Alerts", action_type="navigate", route="/inventory?view=low_stock", description="Check items near minimum threshold")
        ]
    }

    @classmethod
    def generate_recommendations(
        cls,
        question: str,
        intent: str,
        engine_output: Optional[Dict[str, Any]] = None,
        context_dict: Optional[Dict[str, Any]] = None
    ) -> List[RecommendationItem]:
        clean_q = question.strip().lower()
        recs: List[RecommendationItem] = []

        # 1. Check if engine output contains direct navigation route to convert into recommendation
        if engine_output:
            nav_target = engine_output.get("nav_target") or engine_output.get("route") or engine_output.get("target_route")
            page_title = engine_output.get("page_title") or engine_output.get("title") or "Target Page"
            if nav_target:
                recs.append(
                    RecommendationItem(
                        title=f"Open {page_title}",
                        action_type="navigate",
                        route=nav_target,
                        description=f"Navigate directly to {page_title}"
                    )
                )

        # 2. Match domain keywords
        for key, items in cls.KEYWORD_RECOMMENDATION_MAP.items():
            if key in clean_q:
                for item in items:
                    if not any(r.title == item.title for r in recs):
                        recs.append(item)

        # 3. Fallback defaults if list is too small
        if len(recs) < 2:
            for item in cls.DEFAULT_RECOMMENDATIONS:
                if not any(r.title == item.title for r in recs):
                    recs.append(item)

        return recs[:4]  # Maximum 4 clean recommendations
