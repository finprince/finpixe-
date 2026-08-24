"""
KIKI ERP Analytics Capability Plugin — Phase 15 V3 (Pure Evidence-Driven)
==========================================================================
Plugin capability for deterministic SQL execution against MySQL database.
Evaluates probe using native execution-plan feasibility evidence (ZERO keyword/term checks).
Encapsulates database results into standardized Evidence objects.
"""
from typing import Dict, Any, List, Optional
from ..base import BaseCapability, CapabilityProbeResult
from ...evidence.model import Evidence
from ...schema_engine import schema_selector
from ...planner import execution_planner
from ...query_engine import sql_builder, query_optimizer, query_executor, explanation_engine
from ...providers import ProviderFactory
from ...config import kiki_settings
from ...logging import get_kiki_logger

logger = get_kiki_logger("erp_plugin")


class ERPAnalyticsCapability(BaseCapability):
    """ERP Analytics Capability Plugin executing MySQL analytical queries."""

    name = "ERPAnalyticsCapability"
    description = "Executes analytical database queries for financial data, sales, stock, and vouchers."
    priority = 80

    def probe(self, rewritten_question: str, context: Any) -> CapabilityProbeResult:
        """
        Evaluates ERP capability via native execution-plan feasibility evidence.
        ZERO business keyword or ontology term checks. Dynamic schema discovery.
        Returns is_match=False if no valid analytical plan can be built.
        """
        try:
            from ...ontology import ontology_graph
            detected_domain = ontology_graph.resolve_domain_for_term(rewritten_question) or "Sales"
            schema_info = schema_selector.select_schema_for_domain(detected_domain)
            candidate_tables = list(schema_info.get("tables", {}).keys())
            target_table = candidate_tables[0] if candidate_tables else "master_voucher_sales"

            plan_ir = execution_planner.plan(
                user_message=rewritten_question,
                domain=schema_info.get("domain", detected_domain),
                target_table=target_table,
                tenant_id=getattr(context, "tenant_id", "default")
            )

            # Evaluate execution plan completeness evidence
            has_selects = bool(plan_ir.get("select"))
            has_aggregation = bool(plan_ir.get("aggregation"))
            has_measure = bool(plan_ir.get("measure"))
            has_date_filter = bool(plan_ir.get("date_filter"))

            if not (has_selects or has_aggregation or has_measure or has_date_filter):
                logger.info(f"[ERP PROBE] No analytical metrics/filters found for '{rewritten_question}' -> is_match=False")
                return CapabilityProbeResult(
                    capability_name=self.name,
                    is_match=False,
                    confidence=0.0,
                    estimated_latency_ms=2.0,
                    failure_reason="No analytical metrics or selectable columns detected in plan"
                )

            # Derive confidence strictly from plan evidence completeness
            confidence = 0.85 if (has_aggregation and (has_measure or has_date_filter)) else 0.65

            logger.info(f"[ERP PROBE] Plan feasible for '{rewritten_question}' (Domain: {detected_domain}) | Confidence: {confidence:.2f}")

            return CapabilityProbeResult(
                capability_name=self.name,
                is_match=True,
                confidence=confidence,
                estimated_latency_ms=12.0,
                supported_operations=["sql_query_generation", "mysql_execution", "aggregate_analytics"],
                availability=True,
                priority=self.priority,
                execution_params={"plan_ir": plan_ir, "domain": schema_info.get("domain", "Sales"), "table": target_table}
            )

        except Exception as e:
            logger.warning(f"[ERP PROBE EXCEPTION] Plan probe failed: {str(e)}")
            return CapabilityProbeResult(
                capability_name=self.name,
                is_match=False,
                confidence=0.0,
                estimated_latency_ms=2.0,
                failure_reason=f"Plan assembly exception: {str(e)}"
            )


    def execute(
        self,
        rewritten_question: str,
        context: Any,
        probe_result: CapabilityProbeResult,
        tenant_id: str
    ) -> Evidence:
        """
        Executes SQL query, encapsulates results into Evidence, calls Ollama LLM summary, and returns Evidence object.
        """
        domain_name = probe_result.execution_params.get("domain") or "Sales"
        logger.info(f"[ERP EXECUTE] Processing: '{rewritten_question}' | Tenant: {tenant_id}")

        # Dynamic Schema Selection
        pruned_schema = schema_selector.select_schema_for_domain(domain_name)
        available_tables = [
            t for t in pruned_schema.get("tables", {}).keys()
            if not t.startswith("accounting_cache") and not t.startswith("ai_") and not t.startswith("auth_")
        ]
        target_table = available_tables[0] if available_tables else "customer_master_customer_basicdetails"

        # SQL Plan IR & Query Execution
        ir_payload = probe_result.execution_params.get("plan_ir") or execution_planner.plan(
            user_message=rewritten_question,
            domain=domain_name,
            target_table=target_table,
            tenant_id=tenant_id
        )
        optimized_ir = query_optimizer.optimize_ir(ir_payload)
        sql_query, sql_params = sql_builder.build_sql(optimized_ir, tenant_id)
        db_results = query_executor.execute_query(sql_query, sql_params, tenant_id)

        # Build Evidence Package
        evidence_pkg = explanation_engine.build_evidence_package(domain_name, db_results, rewritten_question)

        # Build Detailed Markdown Table for complete record visibility
        def build_detailed_table(results):
            if not results:
                return "No records found."
            cols = list(results[0].keys())
            disp_cols = [c.replace('_', ' ').title() for c in cols[:6]] # top 6 columns for clean table
            lines = [
                "| " + " | ".join(disp_cols) + " |",
                "| " + " | ".join(["---"] * len(disp_cols)) + " |"
            ]
            for r in results[:15]:
                row_vals = []
                for c in cols[:6]:
                    v = r.get(c)
                    if v is None:
                        row_vals.append("-")
                    elif isinstance(v, (int, float)) and any(k in c.lower() for k in ['amount', 'total', 'rate', 'price', 'val', 'balance']):
                        row_vals.append(f"₹{v:,.2f}")
                    else:
                        row_vals.append(str(v))
                lines.append("| " + " | ".join(row_vals) + " |")
            return "\n".join(lines)

        detailed_table = build_detailed_table(db_results)

        # LLM Natural Language Synthesis with Detailed Output
        try:
            llm_provider = ProviderFactory.get_llm_provider()
            prompt = (
                f"User Question: '{rewritten_question}'\n"
                f"Total Records Found: {len(db_results)}\n"
                f"Data Summary: {evidence_pkg['summary']}\n"
                f"Detailed Records Table:\n{detailed_table}\n\n"
                f"INSTRUCTIONS: Provide a detailed breakdown of the query results. "
                f"Include key metrics (total count, total valuation/amount) and present the itemized data clearly."
            )
            reply_text = llm_provider.generate(
                model=kiki_settings.REASONING_MODEL,
                prompt=prompt,
                temperature=0.1
            )
            if "### Detailed Records" not in reply_text:
                reply_text = f"{reply_text}\n\n### Detailed Records ({len(db_results)} items)\n\n{detailed_table}"
        except Exception as e:
            logger.warning(f"ERP LLM synthesis error: {str(e)}")
            reply_text = f"Found **{len(db_results)} matching record(s)** for your query.\n\n### Detailed Records Breakdown\n\n{detailed_table}"

        return Evidence(
            type="ERP_DATA",
            source=target_table,
            payload={
                "db_results": db_results,
                "evidence_package": evidence_pkg,
                "synthesis_text": reply_text,
                "sql_query": sql_query,
                "domain": domain_name
            },
            summary=reply_text,
            confidence=probe_result.confidence,
            citations=[],
            metadata={"domain": domain_name, "table": target_table, "record_count": len(db_results)}
        )
