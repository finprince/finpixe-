import re
from typing import Dict, Any
from ..utils.logger import kiki_logger


class HelpHandler:
    """
    Component — Help Handler
    Provides instant, evidence-backed application feature guides and documentation explanations
    for questions such as "How do I create a vendor?", "How do I upload invoices?", etc.
    Bypasses SQL execution and database queries.
    """

    HELP_GUIDES = [
        (
            r"\b(vendor|create vendor|add vendor)\b",
            "### How to Create a Vendor\n\n"
            "1. Navigate to **Vendor Portal** (`/vendor-portal`).\n"
            "2. Click the **+ Create Vendor** button.\n"
            "3. Fill in basic details (Vendor Name, PAN Number, Contact Details, Currency).\n"
            "4. Add GSTIN details and Bank Account numbers if applicable.\n"
            "5. Click **Save Vendor** to add the vendor to the Accounting Master."
        ),
        (
            r"\b(invoice|upload invoice|upload|scan)\b",
            "### How to Upload & Scan Invoices\n\n"
            "1. Go to **Pending Purchases** (`/pending-purchase`).\n"
            "2. Drag and drop your scanned invoice PDF or image into the upload area.\n"
            "3. Click **Process OCR** to run automated line-item extraction.\n"
            "4. Review extracted totals, GST tax splits, and item lines.\n"
            "5. Click **Post Voucher** to save into the purchase ledger."
        ),
        (
            r"\b(gstr|gstr-1|gstr-3b|gst reconcile|gst)\b",
            "### How to Generate & Reconcile GST Reports\n\n"
            "1. Open **Reports & Analytics** -> **GSTR-1 Report** (`/reports/gstr1`).\n"
            "2. Select the active financial month or date range.\n"
            "3. Review B2B Invoices, B2CL Sales, and Tax Summaries (CGST, SGST, IGST).\n"
            "4. Export JSON/Excel for GST Portal filing."
        ),
    ]

    @classmethod
    def handle_help(cls, question: str) -> Dict[str, Any]:
        clean_q = question.strip().lower()

        for pattern, guide_md in cls.HELP_GUIDES:
            if re.search(pattern, clean_q):
                kiki_logger.info(f"[HELP HANDLER] Matched help guide for query '{question}'")
                return {
                    "question": question,
                    "intent": "HELP",
                    "final_response": guide_md,
                    "reply": guide_md,
                    "investigation_steps": [],
                    "evidences": []
                }

        # Default help text
        default_help = (
            "### Kiki ERP Assistant Guide\n\n"
            "I can assist you with:\n"
            "- **Navigation**: e.g., *'Open Vendor Portal'*, *'Go to Reports'*\n"
            "- **Instant KPIs**: e.g., *'Total sales'*, *'Total purchases'*\n"
            "- **ERP Investigations**: e.g., *'Why did sales decrease?'*, *'Latest purchase for muthu'*\n"
            "- **Application Help**: e.g., *'How do I create a vendor?'*"
        )
        return {
            "question": question,
            "intent": "HELP",
            "final_response": default_help,
            "reply": default_help,
            "investigation_steps": [],
            "evidences": []
        }
