"""
Indian Accounting Financial Date Resolver
==========================================
Resolves natural language time periods into exact (start_date, end_date) strings (YYYY-MM-DD)
with full support for Indian Financial Years (April 1 -> March 31), calendar months, quarters,
relative dates, and custom date ranges.
"""
import re
import datetime
import calendar
from typing import Optional, Tuple, Dict, Any


class DateResolver:
    """Enterprise Date Resolver for Indian Accounting and ERP Systems."""

    MONTHS = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12
    }

    @classmethod
    def get_current_fy_start_year(cls, ref_date: datetime.date) -> int:
        """Indian FY starts on April 1. If month >= 4, FY start year is current year, else year-1."""
        return ref_date.year if ref_date.month >= 4 else ref_date.year - 1

    @classmethod
    def resolve_date_range(cls, text: str, ref_date: Optional[datetime.date] = None) -> Optional[Dict[str, Any]]:
        """
        Parses text for date signals and returns a dict:
        {
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "label": "Human readable label",
            "filter_type": "TODAY|YESTERDAY|THIS_MONTH|LAST_MONTH|FY|CUSTOM|..."
        }
        """
        if not text:
            return None

        today = ref_date or datetime.date.today()
        text_lower = text.lower().strip()

        # ── 1. Explicit ISO Date Ranges (e.g. 2026-08-01 to 2026-08-15) ─────────────
        iso_range = re.search(r'(\d{4}-\d{2}-\d{2})\s+(?:to|and|-|until)\s+(\d{4}-\d{2}-\d{2})', text_lower)
        if iso_range:
            d1, d2 = iso_range.group(1), iso_range.group(2)
            return {
                "start_date": min(d1, d2),
                "end_date": max(d1, d2),
                "label": f"Between {d1} and {d2}",
                "filter_type": "CUSTOM_RANGE"
            }

        # ── 2. Explicit Indian Financial Year (e.g. FY 2025-26, FY 2024-25, 2025-2026) ─
        fy_match = re.search(r'\bfy\s*(\d{4})[-/](\d{2,4})\b|\bfinancial\s+year\s*(\d{4})[-/](\d{2,4})\b', text_lower)
        if fy_match:
            y1_str = fy_match.group(1) or fy_match.group(3)
            y2_str = fy_match.group(2) or fy_match.group(4)
            y1 = int(y1_str)
            y2 = int(y2_str) if len(y2_str) == 4 else (y1 // 100) * 100 + int(y2_str)
            start_date = f"{y1}-04-01"
            end_date = f"{y2}-03-31"
            return {
                "start_date": start_date,
                "end_date": end_date,
                "label": f"FY {y1}-{str(y2)[-2:]}",
                "filter_type": "FINANCIAL_YEAR"
            }

        # ── 3. Relative Financial Years ("this financial year", "last financial year") ──
        if any(k in text_lower for k in ["this financial year", "this fy", "current financial year", "current fy"]):
            fy_start_y = cls.get_current_fy_start_year(today)
            start_date = f"{fy_start_y}-04-01"
            end_date = f"{fy_start_y + 1}-03-31"
            return {
                "start_date": start_date,
                "end_date": end_date,
                "label": f"FY {fy_start_y}-{str(fy_start_y + 1)[-2:]}",
                "filter_type": "THIS_FINANCIAL_YEAR"
            }

        if any(k in text_lower for k in ["last financial year", "last fy", "previous financial year", "previous fy", "past fy"]):
            fy_start_y = cls.get_current_fy_start_year(today) - 1
            start_date = f"{fy_start_y}-04-01"
            end_date = f"{fy_start_y + 1}-03-31"
            return {
                "start_date": start_date,
                "end_date": end_date,
                "label": f"FY {fy_start_y}-{str(fy_start_y + 1)[-2:]}",
                "filter_type": "LAST_FINANCIAL_YEAR"
            }

        if "this year" in text_lower or "current year" in text_lower:
            # For Indian business accounting, default "this year" to the active Financial Year
            fy_start_y = cls.get_current_fy_start_year(today)
            start_date = f"{fy_start_y}-04-01"
            end_date = f"{fy_start_y + 1}-03-31"
            return {
                "start_date": start_date,
                "end_date": end_date,
                "label": f"FY {fy_start_y}-{str(fy_start_y + 1)[-2:]}",
                "filter_type": "THIS_FINANCIAL_YEAR"
            }

        if "last year" in text_lower or "previous year" in text_lower:
            fy_start_y = cls.get_current_fy_start_year(today) - 1
            start_date = f"{fy_start_y}-04-01"
            end_date = f"{fy_start_y + 1}-03-31"
            return {
                "start_date": start_date,
                "end_date": end_date,
                "label": f"FY {fy_start_y}-{str(fy_start_y + 1)[-2:]}",
                "filter_type": "LAST_FINANCIAL_YEAR"
            }

        # ── 4. Today / Yesterday ──────────────────────────────────────────────────
        if "today" in text_lower:
            d_str = today.strftime("%Y-%m-%d")
            return {
                "start_date": d_str,
                "end_date": d_str,
                "label": f"Today ({d_str})",
                "filter_type": "TODAY"
            }

        if "yesterday" in text_lower:
            yest = today - datetime.timedelta(days=1)
            d_str = yest.strftime("%Y-%m-%d")
            return {
                "start_date": d_str,
                "end_date": d_str,
                "label": f"Yesterday ({d_str})",
                "filter_type": "YESTERDAY"
            }

        # ── 5. Weeks (This Week, Last Week, Last 7 days) ──────────────────────────
        if any(k in text_lower for k in ["this week", "current week"]):
            start_w = today - datetime.timedelta(days=today.weekday())  # Monday
            return {
                "start_date": start_w.strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d"),
                "label": "This Week",
                "filter_type": "THIS_WEEK"
            }

        if any(k in text_lower for k in ["last week", "previous week", "past week"]):
            start_last_w = today - datetime.timedelta(days=today.weekday() + 7)
            end_last_w = start_last_w + datetime.timedelta(days=6)
            return {
                "start_date": start_last_w.strftime("%Y-%m-%d"),
                "end_date": end_last_w.strftime("%Y-%m-%d"),
                "label": "Last Week",
                "filter_type": "LAST_WEEK"
            }

        if "last 7 days" in text_lower:
            start_7 = today - datetime.timedelta(days=7)
            return {
                "start_date": start_7.strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d"),
                "label": "Last 7 Days",
                "filter_type": "LAST_7_DAYS"
            }

        # ── 6. Months (This Month, Last Month, Specific Month) ───────────────────
        if any(k in text_lower for k in ["this month", "current month"]):
            start_m = today.replace(day=1)
            # End of current month or today
            _, last_day = calendar.monthrange(today.year, today.month)
            end_m = today.replace(day=last_day)
            return {
                "start_date": start_m.strftime("%Y-%m-%d"),
                "end_date": end_m.strftime("%Y-%m-%d"),
                "label": today.strftime("%B %Y"),
                "filter_type": "THIS_MONTH"
            }

        if any(k in text_lower for k in ["last month", "previous month", "past month"]):
            first_of_this = today.replace(day=1)
            last_of_prev = first_of_this - datetime.timedelta(days=1)
            first_of_prev = last_of_prev.replace(day=1)
            return {
                "start_date": first_of_prev.strftime("%Y-%m-%d"),
                "end_date": last_of_prev.strftime("%Y-%m-%d"),
                "label": first_of_prev.strftime("%B %Y"),
                "filter_type": "LAST_MONTH"
            }

        if "last 30 days" in text_lower:
            start_30 = today - datetime.timedelta(days=30)
            return {
                "start_date": start_30.strftime("%Y-%m-%d"),
                "end_date": today.strftime("%Y-%m-%d"),
                "label": "Last 30 Days",
                "filter_type": "LAST_30_DAYS"
            }

        # ── 6. Natural Custom Range (e.g. from 1 august to 15 august) ────────────
        range_match = re.search(r'(?:from|between)\s+(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?\s+(?:to|and|-)\s+(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?', text_lower)
        if range_match:
            d1 = int(range_match.group(1))
            m1_name = range_match.group(2)
            y1 = int(range_match.group(3)) if range_match.group(3) else today.year
            d2 = int(range_match.group(4))
            m2_name = range_match.group(5)
            y2 = int(range_match.group(6)) if range_match.group(6) else y1

            if m1_name in cls.MONTHS and m2_name in cls.MONTHS:
                m1 = cls.MONTHS[m1_name]
                m2 = cls.MONTHS[m2_name]
                start_date = f"{y1}-{m1:02d}-{d1:02d}"
                end_date = f"{y2}-{m2:02d}-{d2:02d}"
                return {
                    "start_date": start_date,
                    "end_date": end_date,
                    "label": f"{d1} {m1_name.title()} to {d2} {m2_name.title()} {y2}",
                    "filter_type": "CUSTOM_RANGE"
                }

        # Check for specific named months (e.g. "August", "in August 2026", "June 2026")
        for m_name, m_num in cls.MONTHS.items():
            pattern = rf'\b(?:in\s+|for\s+)?{m_name}(?:\s+(\d{{4}}))?\b'
            m_match = re.search(pattern, text_lower)
            if m_match:
                year_str = m_match.group(1)
                target_year = int(year_str) if year_str else today.year
                _, last_d = calendar.monthrange(target_year, m_num)
                start_date = f"{target_year}-{m_num:02d}-01"
                end_date = f"{target_year}-{m_num:02d}-{last_d:02d}"
                m_label = datetime.date(target_year, m_num, 1).strftime("%B %Y")
                return {
                    "start_date": start_date,
                    "end_date": end_date,
                    "label": m_label,
                    "filter_type": "SPECIFIC_MONTH"
                }

        # ── 7. Quarters (Q1, Q2, Q3, Q4) ──────────────────────────────────────────
        q_match = re.search(r'\b(q[1-4])(?:\s+(\d{4}))?\b', text_lower)
        if q_match:
            q_str = q_match.group(1).upper()
            target_year = int(q_match.group(2)) if q_match.group(2) else today.year
            # Indian Accounting Quarters:
            # Q1: Apr-Jun, Q2: Jul-Sep, Q3: Oct-Dec, Q4: Jan-Mar (next year)
            quarter_map = {
                "Q1": (f"{target_year}-04-01", f"{target_year}-06-30", f"Q1 FY {target_year}-{str(target_year+1)[-2:]}"),
                "Q2": (f"{target_year}-07-01", f"{target_year}-09-30", f"Q2 FY {target_year}-{str(target_year+1)[-2:]}"),
                "Q3": (f"{target_year}-10-01", f"{target_year}-12-31", f"Q3 FY {target_year}-{str(target_year+1)[-2:]}"),
                "Q4": (f"{target_year+1}-01-01", f"{target_year+1}-03-31", f"Q4 FY {target_year}-{str(target_year+1)[-2:]}"),
            }
            s_d, e_d, lbl = quarter_map[q_str]
            return {
                "start_date": s_d,
                "end_date": e_d,
                "label": lbl,
                "filter_type": "QUARTER"
            }


        return None


date_resolver = DateResolver()
