"""
KIKI ERP Analytics Capability Plugin
====================================
Plugin capability for deterministic, tenant-safe business queries against the MySQL System of Record.
Uses controlled BusinessToolsEngine and Indian DateResolver with multi-turn context preservation.
Encapsulates database results into standardized Evidence objects with rich Markdown presentation.
"""
import re
from typing import Dict, Any, List, Optional
from ..base import BaseCapability, CapabilityProbeResult
from ...evidence.model import Evidence
from ...tools.business_tools import business_tools, format_inr
from ...tools.date_resolver import date_resolver
from ...ontology import ontology_graph
from ...providers import ProviderFactory
from ...config import kiki_settings
from ...logging import get_kiki_logger

logger = get_kiki_logger("erp_plugin")


class ERPAnalyticsCapability(BaseCapability):
    """ERP Analytics Capability Plugin executing verified MySQL analytical business queries."""

    name = "ERPAnalyticsCapability"
    description = "Executes analytical accounting queries for sales, purchases, receivables, payables, stock, customers, suppliers, GST, and ledgers."
    priority = 85

    def probe(self, rewritten_question: str, context: Any) -> CapabilityProbeResult:
        """
        Evaluates ERP capability probe by resolving domain, entities, and date signals.
        """
        try:
            q_lower = rewritten_question.lower()
            detected_domain = ontology_graph.resolve_domain_for_term(rewritten_question)

            # Specific intent signals
            is_sales = any(k in q_lower for k in ["sale", "sales", "revenue", "invoice", "invoices", "sold", "billing"])
            is_purch = any(k in q_lower for k in ["purchase", "purchases", "procure", "bought", "supplier bill", "vendor bill"])
            is_rec = any(k in q_lower for k in ["receivable", "receivables", "owe me", "owes me", "customer due", "unpaid invoice", "debtor"])
            is_pay = any(k in q_lower for k in ["payable", "payables", "i owe", "we owe", "supplier due", "unpaid bill", "creditor"])
            is_inv = any(k in q_lower for k in ["inventory", "stock", "product", "item", "sku", "reorder", "goods"])
            is_cust = any(k in q_lower for k in ["customer", "customers", "client", "clients", "buyer"])
            is_supp = any(k in q_lower for k in ["supplier", "suppliers", "vendor", "vendors", "seller"])
            is_gst = any(k in q_lower for k in ["gst", "tax", "cgst", "sgst", "igst", "tax liability", "tax collected", "input tax", "output tax"])
            is_fin = any(k in q_lower for k in ["cash", "bank", "ledger", "balance", "profit", "loss", "p&l", "trial balance", "daybook"])

            is_erp = (
                detected_domain is not None
                or is_sales or is_purch or is_rec or is_pay or is_inv
                or is_cust or is_supp or is_gst or is_fin
            )

            if not is_erp:
                return CapabilityProbeResult(
                    capability_name=self.name,
                    is_match=False,
                    confidence=0.0,
                    estimated_latency_ms=2.0,
                    failure_reason="No ERP business terminology or domain concepts detected"
                )

            # Assign domain
            if not detected_domain:
                if is_sales: detected_domain = "Sales"
                elif is_purch: detected_domain = "Purchase"
                elif is_rec: detected_domain = "Receivables"
                elif is_pay: detected_domain = "Payables"
                elif is_inv: detected_domain = "Inventory"
                elif is_cust: detected_domain = "Customers"
                elif is_supp: detected_domain = "Suppliers"
                elif is_gst: detected_domain = "GST"
                elif is_fin: detected_domain = "Finance"
                else: detected_domain = "Sales"

            return CapabilityProbeResult(
                capability_name=self.name,
                is_match=True,
                confidence=0.90,
                estimated_latency_ms=8.0,
                supported_operations=["business_tools_query", "mysql_execution", "aggregate_analytics"],
                availability=True,
                priority=self.priority,
                execution_params={"domain": detected_domain}
            )

        except Exception as e:
            logger.warning(f"[ERP PROBE EXCEPTION] Probe failed: {str(e)}")
            return CapabilityProbeResult(
                capability_name=self.name,
                is_match=False,
                confidence=0.0,
                estimated_latency_ms=2.0,
                failure_reason=f"Probe exception: {str(e)}"
            )

    def execute(
        self,
        rewritten_question: str,
        context: Any,
        probe_result: CapabilityProbeResult,
        tenant_id: str
    ) -> Evidence:
        """
        Executes controlled business tool query, retrieves verified MySQL data,
        formats markdown results, and requests LLM explanation.
        """
        domain_name = probe_result.execution_params.get("domain") or "Sales"
        q_lower = rewritten_question.lower()

        logger.info(f"[ERP EXECUTE] Processing: '{rewritten_question}' | Domain: {domain_name} | Tenant: {tenant_id}")

        # ── 1. Resolve Multi-Turn Date Range ──────────────────────────────────
        resolved_date = date_resolver.resolve_date_range(rewritten_question)
        state = getattr(context, "conversation_state", None)

        if resolved_date:
            active_date_range = resolved_date
            if state:
                state.set_active_date_range(resolved_date)
        elif state and state.active_date_range:
            active_date_range = state.active_date_range
            logger.info(f"[ERP CONTEXT] Inherited date range from conversation state: {active_date_range.get('label')}")
        else:
            active_date_range = None

        # ── 2. Resolve Multi-Turn Entity Filter (Customer / Vendor / Item) ────
        party_name: Optional[str] = None
        # Extract party after 'for', 'from', 'by', 'customer', 'supplier', 'vendor'
        party_match = re.search(r'(?:for|from|by|customer|supplier|vendor)\s+([a-zA-Z0-9\s\.\-_]+?)(?:\s+in|\s+for|\s+during|\s*\?|\s*$)', rewritten_question, re.IGNORECASE)
        if party_match:
            candidate = party_match.group(1).strip()
            # Strip prefixes like 'supplier ', 'vendor ', 'customer ', 'party '
            candidate = re.sub(r'^(?:supplier|vendor|customer|party)\s+', '', candidate, flags=re.IGNORECASE).strip()
            # Exclude date words
            date_words = {"august", "january", "february", "march", "april", "may", "june", "july", "september", "october", "november", "december", "this month", "last month", "today", "yesterday", "this week", "last week", "this year", "last year", "fy", "q1", "q2", "q3", "q4"}
            if candidate.lower() not in date_words and len(candidate) > 1:
                party_name = candidate

        if party_name:
            if state:
                state.set_active_entity(party_name)
        elif state and state.active_entity:
            # If asking follow up regarding "his", "their", "unpaid", inherit entity
            if any(k in q_lower for k in ["his", "their", "this customer", "this vendor", "unpaid", "pending", "outstanding"]):
                party_name = state.active_entity
                logger.info(f"[ERP CONTEXT] Inherited party entity from conversation state: {party_name}")

        # ── 3. Execute Appropriate Business Tool ──────────────────────────────
        # ── 3. Query Intent Classification & Business Tool Execution ──────────
        is_count_query = any(k in q_lower for k in [
            "how many", "count of", "number of", "total number of", "how many items",
            "how many customers", "how many suppliers", "how many bills", "how many invoices",
            "how many accounts"
        ])
        is_list_query = any(k in q_lower for k in [
            "show", "list", "display", "view", "details", "detail", "breakdown", "itemized",
            "transactions", "records", "table", "all items", "all suppliers", "all customers",
            "all invoices", "all bills", "item list"
        ])
        is_value_query = any(k in q_lower for k in [
            "value", "valuation", "worth", "how much is", "what is the value", "total value"
        ])

        tool_data: Dict[str, Any] = {}
        summary_title = ""
        direct_answer = ""
        key_metrics_lines = []

        # Domain classification refinements
        if any(k in q_lower for k in ["receivable", "receivables", "owe me", "owes me", "customer due", "unpaid invoice"]):
            domain_name = "Receivables"
        elif any(k in q_lower for k in ["payable", "payables", "i owe", "we owe", "supplier due", "unpaid bill"]):
            domain_name = "Payables"
        elif any(k in q_lower for k in ["inventory", "stock", "low stock", "reorder"]):
            domain_name = "Inventory"
        elif any(k in q_lower for k in ["customer", "customers", "client", "clients"]) and not any(k in q_lower for k in ["sales", "invoice", "owe", "due"]):
            domain_name = "Customers"
        elif any(k in q_lower for k in ["supplier", "suppliers", "vendor", "vendors"]) and not any(k in q_lower for k in ["purchase", "bill", "owe", "due"]):
            domain_name = "Suppliers"
        elif any(k in q_lower for k in ["gst", "cgst", "sgst", "igst", "tax liability", "tax collected"]):
            domain_name = "GST"
        elif any(k in q_lower for k in ["profit", "loss", "p&l", "net income", "revenue and expense"]):
            domain_name = "ProfitLoss"
        elif any(k in q_lower for k in ["cash", "bank", "ledger balance", "daybook"]):
            domain_name = "Finance"

        if domain_name == "Sales":
            tool_data = business_tools.get_sales_summary(tenant_id, date_range=active_date_range, customer_name=party_name)
            summary_title = f"Sales Summary — {tool_data['period']}"
            if is_count_query:
                direct_answer = f"You have **{tool_data['count']}** sales invoice(s) recorded for {tool_data['period']} totaling **{tool_data['total_sales_formatted']}**."
            else:
                direct_answer = f"Your total sales for {tool_data['period']} is **{tool_data['total_sales_formatted']}** across {tool_data['count']} invoice(s)."

            key_metrics_lines = [
                f"- **Total Sales Amount**: {tool_data['total_sales_formatted']}",
                f"- **Total Invoices**: {tool_data['count']}",
                f"- **Total Taxable Amount**: {tool_data['total_taxable_formatted']}",
                f"- **Total Tax (GST)**: {tool_data['total_tax_formatted']}"
            ]

        elif domain_name == "Purchase":
            tool_data = business_tools.get_purchase_summary(tenant_id, date_range=active_date_range, vendor_name=party_name)
            summary_title = f"Purchase Summary — {tool_data['period']}"
            if is_count_query:
                direct_answer = f"You have **{tool_data['count']}** purchase bill(s) recorded for {tool_data['period']} totaling **{tool_data['total_purchases_formatted']}**."
            else:
                direct_answer = f"Your total purchases for {tool_data['period']} is **{tool_data['total_purchases_formatted']}** across {tool_data['count']} bill(s)."

            key_metrics_lines = [
                f"- **Total Purchases**: {tool_data['total_purchases_formatted']}",
                f"- **Total Bills**: {tool_data['count']}",
                f"- **Total Taxable Amount**: {tool_data['total_taxable_formatted']}",
                f"- **Total Input Tax**: {tool_data['total_tax_formatted']}"
            ]

        elif domain_name == "Receivables":
            tool_data = business_tools.get_receivables_summary(tenant_id, customer_name=party_name)
            summary_title = "Accounts Receivable & Outstanding Customer Dues"
            if is_count_query:
                direct_answer = f"There are **{tool_data['count']}** pending customer invoice(s) with outstanding balances."
            else:
                direct_answer = f"Total outstanding receivables from customers is **{tool_data['total_receivable_formatted']}** (across {tool_data['count']} pending invoices)."

            key_metrics_lines = [
                f"- **Total Outstanding Receivables**: {tool_data['total_receivable_formatted']}",
                f"- **Pending / Overdue Invoices**: {tool_data['count']}"
            ]

        elif domain_name == "Payables":
            tool_data = business_tools.get_payables_summary(tenant_id, vendor_name=party_name)
            summary_title = "Accounts Payable & Supplier Dues"
            if is_count_query:
                direct_answer = f"There are **{tool_data['count']}** supplier account(s) with pending or overdue bills."
            else:
                direct_answer = f"Total outstanding payables owed to suppliers is **{tool_data['total_payable_formatted']}** (across {tool_data['count']} supplier accounts)."

            key_metrics_lines = [
                f"- **Total Outstanding Payables**: {tool_data['total_payable_formatted']}",
                f"- **Pending / Overdue Bills**: {tool_data['count']}"
            ]

        elif domain_name == "Inventory":
            low_stock_only = "low" in q_lower or "reorder" in q_lower
            tool_data = business_tools.get_inventory_summary(tenant_id, low_stock_only=low_stock_only)
            summary_title = "Inventory & Stock Status" if not low_stock_only else "Low Stock Items Requiring Reorder"

            if is_count_query:
                direct_answer = f"There are **{tool_data['total_items']}** items in the inventory catalog (with **{tool_data['low_stock_count']}** item currently below its reorder level)."
            elif is_value_query:
                direct_answer = f"Your total inventory valuation is **{tool_data['total_valuation_formatted']}** across **{tool_data['total_items']}** active inventory items (total quantity: {tool_data['total_quantity']:g} units)."
            else:
                direct_answer = f"Inventory overview: **{tool_data['total_items']}** active items with a total stock valuation of **{tool_data['total_valuation_formatted']}**."

            key_metrics_lines = [
                f"- **Total Active SKUs / Items**: {tool_data['total_items']}",
                f"- **Total Stock Quantity**: {tool_data['total_quantity']:g}",
                f"- **Total Stock Valuation**: {tool_data['total_valuation_formatted']}",
                f"- **Low Stock Items (Below Reorder Level)**: {tool_data['low_stock_count']}"
            ]

        elif domain_name == "Customers":
            tool_data = business_tools.get_customers_summary(tenant_id, customer_name=party_name)
            summary_title = "Customer Directory & Sales Summary"
            direct_answer = f"There are **{tool_data['count']}** customer(s) registered in the system."
            key_metrics_lines = [
                f"- **Total Customers Found**: {tool_data['count']}"
            ]

        elif domain_name == "Suppliers":
            tool_data = business_tools.get_suppliers_summary(tenant_id, vendor_name=party_name)
            summary_title = "Supplier Directory & Procurement Summary"
            direct_answer = f"There are **{tool_data['count']}** supplier(s) registered in the system."
            key_metrics_lines = [
                f"- **Total Suppliers Found**: {tool_data['count']}"
            ]

        elif domain_name == "GST":
            tool_data = business_tools.get_gst_summary(tenant_id, date_range=active_date_range)
            summary_title = f"GST & Tax Summary — {tool_data['period']}"
            direct_answer = f"Your Net GST Liability for {tool_data['period']} is **{tool_data['net_liability_formatted']}** (Output GST: {tool_data['total_output_gst_formatted']}, Input Tax Credit: {tool_data['total_input_gst_formatted']})."
            key_metrics_lines = [
                f"- **Output GST (Collected on Sales)**: {tool_data['total_output_gst_formatted']}",
                f"- **Input Tax Credit (Paid on Purchases)**: {tool_data['total_input_gst_formatted']}",
                f"- **Net GST Liability / (Refundable)**: {tool_data['net_liability_formatted']}"
            ]

        elif domain_name == "ProfitLoss":
            tool_data = business_tools.get_profit_loss_summary(tenant_id, date_range=active_date_range)
            status_word = "Net Profit" if tool_data['is_profit'] else "Net Loss"
            summary_title = f"Profit & Loss Overview — {tool_data['period']}"
            direct_answer = f"For {tool_data['period']}, your business recorded a **{status_word}** of **{tool_data['net_profit_formatted']}** (Total Revenue: {tool_data['total_sales_formatted']}, Total Expenses: {tool_data['total_expenses_formatted']})."
            key_metrics_lines = [
                f"- **Total Revenue (Sales)**: {tool_data['total_sales_formatted']}",
                f"- **Cost of Goods Sold (incl. Closing Stock)**: {tool_data['total_purchases_formatted']}",
                f"- **Operational / Other Expenses**: {tool_data['other_expenses_formatted']}",
                f"- **Total Expenses**: {tool_data['total_expenses_formatted']}",
                f"- **{status_word}**: {tool_data['net_profit_formatted']}"
            ]

        else: # Finance / Ledgers / Cash / Bank
            grp_filter = "bank" if "bank" in q_lower else ("cash" if "cash" in q_lower else None)
            tool_data = business_tools.get_ledger_balances(tenant_id, group_filter=grp_filter)
            account_type = "Bank" if grp_filter == "bank" else ("Cash" if grp_filter == "cash" else "Ledger")
            summary_title = f"{account_type} Account Balances"
            direct_answer = f"Your total {account_type.lower()} balance is **{tool_data['total_balance_formatted']}** (across {tool_data['count']} account(s))."
            key_metrics_lines = [
                f"- **Total Combined Balance**: {tool_data['total_balance_formatted']}",
                f"- **Accounts / Ledgers Found**: {tool_data['count']}"
            ]

        # ── 4. Build Structured Markdown Table ────────────────────────────────
        formatted_records = tool_data.get("formatted_records", [])
        if formatted_records:
            headers = list(formatted_records[0].keys())
            table_lines = [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] * len(headers)) + " |"
            ]
            for r in formatted_records[:25]:
                row_vals = [str(r.get(h, "-")) for h in headers]
                table_lines.append("| " + " | ".join(row_vals) + " |")
            records_table_md = "\n".join(table_lines)
        else:
            records_table_md = "_No individual records found for the selected criteria._"

        key_metrics_block = "\n".join(key_metrics_lines)

        # ── 5. Compose Tailored Response Based on Intent ───────────────────────
        if is_count_query:
            # For count questions, answer with only the concise statement
            deterministic_reply = direct_answer
        elif is_list_query or domain_name in ["GST", "ProfitLoss"]:
            # For list questions or financial statement summaries, include table
            deterministic_reply = (
                f"{direct_answer}\n\n"
                f"### {summary_title}\n\n"
                f"{key_metrics_block}\n\n"
                f"### Details\n\n"
                f"{records_table_md}"
            )
        else:
            # For standard totals/summaries, include clean key metric bullets
            deterministic_reply = (
                f"{direct_answer}\n\n"
                f"### Key Metrics\n\n"
                f"{key_metrics_block}"
            )

        # ── 6. LLM Synthesis with Strict Grounding ───────────────────────────
        final_reply = deterministic_reply
        try:
            llm_provider = ProviderFactory.get_llm_provider()

            if is_count_query:
                guidance = (
                    "The user is asking ONLY for a count/quantity. "
                    "Respond with a single concise sentence stating the exact count directly. "
                    "Do NOT output any markdown tables or itemized lists."
                )
            elif is_list_query or domain_name in ["GST", "ProfitLoss"]:
                guidance = (
                    "Provide a brief direct answer followed by the structured markdown table below."
                )
            else:
                guidance = (
                    "Provide a clear, concise summary answering the question directly with key bullet points. "
                    "Do NOT output long itemized transaction tables unless explicitly requested."
                )

            prompt = (
                f"You are Kiki, an intelligent financial and accounting AI assistant for FINPIXE ERP.\n"
                f"The user asked: '{rewritten_question}'\n\n"
                f"VERIFIED DATABASE DATA:\n"
                f"{direct_answer}\n\n"
                f"KEY METRICS:\n"
                f"{key_metrics_block}\n\n"
                f"RECORDS TABLE:\n"
                f"{records_table_md}\n\n"
                f"STRICT INSTRUCTIONS:\n"
                f"1. {guidance}\n"
                f"2. Use Indian currency symbol (₹) for monetary amounts.\n"
                f"3. NEVER invent or hallucinate any numbers.\n"
                f"4. If there are 0 records or ₹0.00, clearly state that no records were found."
            )
            llm_text = llm_provider.generate(
                model=kiki_settings.REASONING_MODEL,
                prompt=prompt,
                temperature=0.1
            )
            if llm_text and len(llm_text.strip()) > 10:
                cleaned_llm = llm_text.strip()
                if is_count_query:
                    # Strip any accidental table generation from count queries
                    cleaned_llm = re.split(r'(\n\s*\||\n\s*###|\n\s*Detailed)', cleaned_llm)[0].strip()
                    final_reply = cleaned_llm if len(cleaned_llm) > 5 else direct_answer
                elif is_list_query and "| --- |" not in cleaned_llm and formatted_records:
                    final_reply = f"{cleaned_llm}\n\n### Detailed Breakdown\n\n{records_table_md}"
                else:
                    final_reply = cleaned_llm
        except Exception as e:
            logger.warning(f"Ollama LLM synthesis exception: {str(e)}. Using verified deterministic reply.")
            final_reply = deterministic_reply

        # ── 7. Build Evidence Payload ─────────────────────────────────────────
        if state:
            state.set_active_domain(domain_name)

        return Evidence(
            type="ERP_DATA",
            source="mysql_system_of_record",
            payload={
                "domain": domain_name,
                "tool_data": tool_data,
                "summary": summary_title,
                "reply": final_reply
            },
            summary=final_reply,
            confidence=0.95,
            citations=[],
            metadata={
                "domain": domain_name,
                "active_date_range": active_date_range,
                "active_entity": party_name,
                "record_count": len(formatted_records)
            }
        )
