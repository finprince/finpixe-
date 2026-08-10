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
            schema_info = schema_selector.select_schema_for_domain("Sales")
            candidate_tables = list(schema_info.get("tables", {}).keys())
            target_table = candidate_tables[0] if candidate_tables else "customer_master_customer_basicdetails"

            plan_ir = execution_planner.plan(
                user_message=rewritten_question,
                domain=schema_info.get("domain", "Sales"),
                target_table=target_table,
                tenant_id=getattr(context, "tenant_id", "default")
            )

            # Evaluate execution plan completeness evidence
            has_selects = bool(plan_ir.get("select"))
            has_aggregation = bool(plan_ir.get("aggregation"))
            has_measure = bool(plan_ir.get("measure"))
            has_date_filter = bool(plan_ir.get("date_filter"))

            if not (has_aggregation or has_measure or has_date_filter):
                logger.info(f"[ERP PROBE] No analytical metrics/filters found for '{rewritten_question}' -> is_match=False")
                return CapabilityProbeResult(
                    capability_name=self.name,
                    is_match=False,
                    confidence=0.0,
                    estimated_latency_ms=2.0,
                    failure_reason="No analytical metrics, aggregations, or date filters detected in plan"
                )

            # Derive confidence strictly from plan evidence completeness
            confidence = 0.85 if (has_aggregation and (has_measure or has_date_filter)) else 0.55

            logger.info(f"[ERP PROBE] Plan feasible for '{rewritten_question}' | Confidence: {confidence:.2f}")

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

        # LLM Natural Language Synthesis
        try:
            llm_provider = ProviderFactory.get_llm_provider()
            prompt = (
                f"User Question: '{rewritten_question}'\n"
                f"Data Summary: {evidence_pkg['summary']}\n"
                f"Sample Records: {evidence_pkg['sample_records']}\n\n"
                f"Provide a clear, natural language executive summary based strictly on the data."
            )
            reply_text = llm_provider.generate(
                model=kiki_settings.REASONING_MODEL,
                prompt=prompt,
                temperature=0.1
            )
        except Exception as e:
            logger.warning(f"ERP LLM synthesis error: {str(e)}")
            reply_text = evidence_pkg["summary"]

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
