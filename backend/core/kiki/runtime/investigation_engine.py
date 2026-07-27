import hashlib
from typing import Optional, Dict, Any, List
from ..config.settings import KikiSettings
from ..models.dto import (
    InvestigationContext,
    InvestigationResult,
    QuestionUnderstanding,
    InvestigationPlan,
    QueryIntent,
    EvidencePackage,
    EvaluationResult,
)
from .ollama_runtime import OllamaRuntime
from ..schema.schema_service import SchemaService
from ..query.query_builder import QueryBuilder
from ..query.sql_read_tool import SqlReadTool
from ..query.kpi_resolver import KPIResolver
from ..evidence.evidence_builder import EvidenceBuilder
from ..evidence.evidence_validator import EvidenceValidator

from ..exceptions.kiki_exceptions import (
    KikiException,
    QueryBuilderException,
    SqlValidationException,
    SqlExecutionException,
    InvestigationException,
)
from ..utils.logger import kiki_logger


class InvestigationEngine:
    """
    Workflow Orchestrator for Kiki AI ERP Agent.
    Maintains and updates InvestigationContext state object.
    Coordinates component calls across OllamaRuntime, SchemaService, QueryBuilder,
    SqlReadTool, and EvidenceBuilder.
    Performs NO AI reasoning, NO SQL building, and NO direct database calls.
    """

    def __init__(
        self,
        ollama_runtime: Optional[OllamaRuntime] = None,
        schema_service: Optional[SchemaService] = None
    ):
        self.ollama = ollama_runtime or OllamaRuntime()
        self.schema_service = schema_service or SchemaService()
        self.query_builder = QueryBuilder()
        self.read_tool = SqlReadTool()
        self.evidence_builder = EvidenceBuilder()

    def run_investigation(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> InvestigationResult:
        """
        Executes the complete investigation lifecycle loop.
        """
        if not question or not isinstance(question, str):
            raise InvestigationException("Question must be a non-empty string.")

        context_dict = context or {}
        kiki_logger.info(f"Starting investigation for question: '{question}'")

        # 1. Initialize Investigation Context State with Context-Aware Defaults
        inv_context = InvestigationContext(
            question=question.strip(),
            tenant_id=str(context_dict.get("tenant_id", "") or ""),
            company_name=context_dict.get("company_name"),
            branch_name=context_dict.get("branch_name"),
            financial_year=context_dict.get("financial_year", "2025-2026"),
            current_page=context_dict.get("current_page", "Dashboard"),
            dashboard_filters=context_dict.get("dashboard_filters", {}),
            active_period=context_dict.get("active_period", "current_month")
        )

        # Phase 7: Fast Path KPI Resolution
        kpi_result = KPIResolver.resolve(inv_context.question, inv_context)
        if kpi_result is not None:
            kiki_logger.info("Question resolved instantly via KPI Fast-Path.")
            return kpi_result

        try:
            # Initialize schema cache
            self.schema_service.initialize_schema()

            # 2. Question Understanding
            inv_context.understanding = self.ollama.understand_question(inv_context.question)
            
            # Context-Aware Default Injection: If timeframe is unknown, inject active dashboard period
            if not inv_context.understanding.timeframe or inv_context.understanding.timeframe == "unknown":
                inv_context.understanding.timeframe = inv_context.active_period

            kiki_logger.info(f"Question Understanding: {inv_context.understanding.to_dict()}")

            # 3. Investigation Plan
            inv_context.plan = self.ollama.generate_investigation_plan(inv_context.question, inv_context.understanding)
            kiki_logger.info(f"Investigation Plan Goal: {inv_context.plan.goal}")

            # 4. Investigation Loop
            step_count = 0
            while not inv_context.completed and step_count < KikiSettings.MAX_INVESTIGATION_STEPS:
                step_count += 1
                inv_context.current_step_number = step_count

                step_desc = f"Investigation Step {step_count}"
                if inv_context.plan and inv_context.plan.steps and step_count <= len(inv_context.plan.steps):
                    step_desc = inv_context.plan.steps[step_count - 1].description

                kiki_logger.info(f"--- Executing Step {step_count}: {step_desc} ---")

                # a. Extract search terms
                inv_context.search_terms = self.ollama.extract_search_terms(inv_context)

                # b. Search metadata schema
                inv_context.relevant_schemas = self.schema_service.search_schema(inv_context.search_terms)
                kiki_logger.info(f"Schema matches: {[s.table_name for s in inv_context.relevant_schemas]}")

                # c. Generate Query Intent
                inv_context.query_intent = self.ollama.generate_query_intent(inv_context)

                # d. Build SQL via QueryBuilder
                try:
                    inv_context.generated_sql = self.query_builder.build_sql(
                        intent=inv_context.query_intent,
                        schemas=inv_context.relevant_schemas
                    )
                except QueryBuilderException as qbe:
                    kiki_logger.warning(f"QueryBuilder error on step {step_count}: {qbe}")
                    break

                # Phase 8: Investigation Memory & Deduplication
                sql_hash = hashlib.md5(inv_context.generated_sql.encode()).hexdigest()
                if sql_hash in inv_context.attempted_sqls:
                    kiki_logger.warning(f"Duplicate SQL detected on step {step_count}. Adapting strategy...")
                    if inv_context.query_intent.entity:
                        inv_context.query_intent.entity = None
                        inv_context.generated_sql = self.query_builder.build_sql(
                            intent=inv_context.query_intent,
                            schemas=inv_context.relevant_schemas
                        )
                        sql_hash = hashlib.md5(inv_context.generated_sql.encode()).hexdigest()

                    if sql_hash in inv_context.attempted_sqls:
                        kiki_logger.info("Duplicate query strategy exhausted. Terminating investigation loop.")
                        break

                inv_context.attempted_sqls.add(sql_hash)


                # e. Execute SQL via SqlReadTool
                try:
                    inv_context.query_results = self.read_tool.execute_query(inv_context.generated_sql)
                except (SqlValidationException, SqlExecutionException) as sqle:
                    kiki_logger.error(f"SqlReadTool error on step {step_count}: {sqle}")
                    break

                # f. Package Evidence via EvidenceBuilder
                evidence_pkg = self.evidence_builder.build_evidence(
                    step_number=step_count,
                    step_description=step_desc,
                    query=inv_context.generated_sql,
                    query_result=inv_context.query_results
                )
                inv_context.evidences.append(evidence_pkg)

                # g. Evaluate Evidence via OllamaRuntime
                inv_context.evaluation = self.ollama.evaluate_evidence(inv_context)
                kiki_logger.info(f"Evaluation result: has_enough_info={inv_context.evaluation.has_enough_info}")

                if inv_context.evaluation.has_enough_info:
                    inv_context.completed = True

            # 5. Generate Final Response
            raw_final_resp = self.ollama.generate_final_response(inv_context)
            inv_context.final_response = EvidenceValidator.validate_and_ground_response(
                raw_final_resp,
                inv_context.evidences,
                inv_context.question
            )
            inv_context.completed = True


            # Phase 9: Structured Telemetry Logging
            kiki_logger.info(
                f"\n[KIKI RUNTIME LOG]\n"
                f"Endpoint: /api/kiki/chat/\n"
                f"Runtime: OllamaRuntime\n"
                f"Provider: Ollama\n"
                f"Model: {KikiSettings.OLLAMA_MODEL}\n"
                f"Ollama Host: {KikiSettings.OLLAMA_HOST}\n"
                f"Tenant ID: {inv_context.tenant_id or 'Default'}\n"
                f"Company: {inv_context.company_name or 'Active Company'}\n"
                f"Branch: {inv_context.branch_name or 'Active Branch'}\n"
                f"Period: {inv_context.active_period}\n"
                f"Investigation Steps: {len(inv_context.evidences)}\n"
                f"SQL Queries Executed: {len(inv_context.evidences)}\n"
                f"Evidence Packages: {len(inv_context.evidences)}\n"
                f"Completed: {inv_context.completed}\n"
            )

            # Format steps history trace
            steps_history = []
            for ev in inv_context.evidences:
                steps_history.append({
                    "step_number": ev.step_number,
                    "description": ev.step_description,
                    "query": ev.query,
                    "row_count": ev.metadata.get("row_count", 0),
                    "execution_time_ms": ev.metadata.get("execution_time_ms", 0.0)
                })

            return InvestigationResult(
                question=inv_context.question,
                understanding=inv_context.understanding.to_dict() if inv_context.understanding else {},
                plan=inv_context.plan.to_dict() if inv_context.plan else {},
                investigation_steps=steps_history,
                evidences=[e.to_dict() for e in inv_context.evidences],
                final_response=inv_context.final_response
            )


        except Exception as e:
            kiki_logger.error(f"Investigation execution failed: {e}")
            if isinstance(e, KikiException):
                raise
            raise InvestigationException(f"Investigation failed: {str(e)}") from e
