from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from core.kiki.models.dto import (
    QuestionUnderstanding,
    InvestigationPlan,
    InvestigationStep,
    QueryIntent,
    SchemaMatch,
    QueryResultData,
    EvidencePackage,
    EvaluationResult,
    InvestigationContext,
    InvestigationResult,
)
from core.kiki.schema.schema_service import SchemaService
from core.kiki.query.query_builder import QueryBuilder
from core.kiki.query.sql_read_tool import SqlReadTool
from core.kiki.evidence.evidence_builder import EvidenceBuilder
from core.kiki.runtime.ollama_runtime import OllamaRuntime
from core.kiki.runtime.investigation_engine import InvestigationEngine
from core.kiki.exceptions.kiki_exceptions import (
    SqlValidationException,
    QueryBuilderException,
    KikiException,
)


class KikiDTOTestCase(TestCase):
    """Test suite for DTO dataclasses."""

    def test_dto_serialization(self):
        understanding = QuestionUnderstanding(
            intent="Business Investigation",
            objective="Determine sales reduction cause",
            entities=["ABC Traders"],
            timeframe="this month",
            scope="sales, invoices"
        )
        u_dict = understanding.to_dict()
        self.assertEqual(u_dict["intent"], "Business Investigation")
        self.assertEqual(u_dict["entities"], ["ABC Traders"])

        intent = QueryIntent(
            objective="Compare monthly sales",
            target_tables=["voucher_sales"],
            entity="ABC Traders",
            metrics=["total_amount"],
            limit=50
        )
        i_dict = intent.to_dict()
        self.assertEqual(i_dict["target_tables"], ["voucher_sales"])
        self.assertEqual(i_dict["limit"], 50)


class KikiSchemaServiceTestCase(TestCase):
    """Test suite for SchemaService metadata operations."""

    def test_search_schema_matching(self):
        matches = SchemaService.search_schema(["sales", "customer"])
        self.assertIsInstance(matches, list)
        for match in matches:
            self.assertIsInstance(match, SchemaMatch)
            self.assertTrue(hasattr(match, "table_name"))


class KikiQueryBuilderTestCase(TestCase):
    """Test suite for QueryBuilder SQL generation."""

    def test_query_builder_valid_sql(self):
        schema = SchemaMatch(
            table_name="voucher_sales",
            columns=[
                {"name": "id", "type": "int", "is_primary_key": True},
                {"name": "customer_name", "type": "varchar", "is_primary_key": False},
                {"name": "total_amount", "type": "decimal", "is_primary_key": False},
            ],
            primary_keys=["id"],
            foreign_keys=[]
        )
        intent = QueryIntent(
            objective="Compare sales",
            target_tables=["voucher_sales"],
            entity="ABC Traders",
            metrics=["total_amount"],
            limit=10
        )

        sql = QueryBuilder.build_sql(intent, [schema])
        self.assertTrue(sql.startswith("SELECT"))
        self.assertIn("FROM voucher_sales", sql)
        self.assertIn("ABC Traders", sql)

    def test_query_builder_empty_target_tables_raises(self):
        intent = QueryIntent(objective="Test", target_tables=[])
        schema = SchemaMatch(table_name="voucher_sales")
        with self.assertRaises(QueryBuilderException):
            QueryBuilder.build_sql(intent, [schema])


class KikiSqlReadToolTestCase(TestCase):
    """Test suite for SqlReadTool validation and read-only execution."""

    def test_sql_validation_allowed_select(self):
        safe_sql = "SELECT id, customer_name FROM voucher_sales WHERE total_amount > 1000;"
        cleaned = SqlReadTool.validate_sql(safe_sql)
        self.assertEqual(cleaned, safe_sql.strip())

    def test_sql_validation_allowed_with_cte(self):
        cte_sql = "WITH monthly_sales AS (SELECT * FROM voucher_sales) SELECT * FROM monthly_sales;"
        cleaned = SqlReadTool.validate_sql(cte_sql)
        self.assertEqual(cleaned, cte_sql.strip())

    def test_sql_validation_blocks_insert(self):
        bad_sql = "INSERT INTO voucher_sales (id, name) VALUES (1, 'Fake');"
        with self.assertRaises(SqlValidationException):
            SqlReadTool.validate_sql(bad_sql)

    def test_sql_validation_blocks_drop(self):
        bad_sql = "DROP TABLE voucher_sales;"
        with self.assertRaises(SqlValidationException):
            SqlReadTool.validate_sql(bad_sql)

    def test_sql_validation_blocks_multi_statements(self):
        bad_sql = "SELECT * FROM voucher_sales; DELETE FROM voucher_sales;"
        with self.assertRaises(SqlValidationException):
            SqlReadTool.validate_sql(bad_sql)


class KikiEvidenceBuilderTestCase(TestCase):
    """Test suite for EvidenceBuilder packaging."""

    def test_evidence_builder_packages_data(self):
        query_data = QueryResultData(
            rows=[{"customer_name": "ABC Traders", "total_amount": 145000.0}],
            row_count=1,
            execution_time_ms=12.5,
            status="SUCCESS"
        )
        pkg = EvidenceBuilder.build_evidence(
            step_number=1,
            step_description="Compare sales",
            query="SELECT * FROM voucher_sales",
            query_result=query_data
        )
        self.assertEqual(pkg.step_number, 1)
        self.assertEqual(pkg.rows[0]["customer_name"], "ABC Traders")
        self.assertEqual(pkg.metadata["row_count"], 1)


class KikiOllamaRuntimeTestCase(TestCase):
    """Test suite for OllamaRuntime LLM interaction using mocks."""

    @patch.object(OllamaRuntime, '_call_llm')
    def test_understand_question(self, mock_call_llm):
        mock_call_llm.return_value = '{"intent": "Sales Variance", "objective": "Why sales decreased", "entities": ["ABC Traders"], "timeframe": "this month", "scope": "sales"}'
        runtime = OllamaRuntime()
        understanding = runtime.understand_question("Why did ABC Traders sales decrease?")
        self.assertEqual(understanding.intent, "Sales Variance")
        self.assertIn("ABC Traders", understanding.entities)

    @patch.object(OllamaRuntime, '_call_llm')
    def test_evaluate_evidence(self, mock_call_llm):
        mock_call_llm.return_value = '{"has_enough_info": true, "reasoning": "Sufficient sales variance evidence gathered.", "next_search_terms": []}'
        runtime = OllamaRuntime()
        context = InvestigationContext(question="Why sales dropped?")
        context.evidences = [
            EvidencePackage(step_number=1, step_description="Sales check", query="SELECT...", rows=[{"sales": 100}])
        ]
        eval_res = runtime.evaluate_evidence(context)
        self.assertTrue(eval_res.has_enough_info)


class KikiInvestigationEngineTestCase(TestCase):
    """Test suite for InvestigationEngine workflow orchestration."""

    @patch.object(OllamaRuntime, '_call_llm')
    def test_investigation_engine_full_run(self, mock_call_llm):
        # Mock responses for Ollama calls in sequence: understand, plan, query_intent, evaluate, response
        mock_call_llm.side_effect = [
            '{"intent": "Sales Decrease", "objective": "Determine why sales decreased", "entities": ["ABC Traders"], "timeframe": "this month", "scope": "sales"}',
            '{"goal": "Find sales drop cause", "steps": [{"step_number": 1, "description": "Compare sales totals", "objective": "Variance"}]}',
            '{"objective": "Compare sales", "target_tables": ["voucher_sales"], "entity": "ABC Traders", "metrics": ["total_amount"], "period": [], "group_by": [], "order_by": [], "limit": 10}',
            '{"has_enough_info": true, "reasoning": "Complete evidence gathered", "next_search_terms": []}',
            'ABC Traders sales decreased by 34% due to lower volume.'
        ]

        engine = InvestigationEngine()
        result = engine.run_investigation("Why did ABC Traders sales decrease?")
        self.assertIsInstance(result, InvestigationResult)
        self.assertEqual(result.question, "Why did ABC Traders sales decrease?")
        self.assertIn("ABC Traders", result.final_response)


class KikiAPITestCase(TestCase):
    """Test suite for KikiChatView API endpoint."""

    def setUp(self):
        self.client = APIClient()

    @patch.object(InvestigationEngine, 'run_investigation')
    def test_api_investigate_endpoint(self, mock_run):
        mock_run.return_value = InvestigationResult(
            question="Why did ABC Traders sales decrease?",
            understanding={"intent": "Sales Variance"},
            plan={"goal": "Investigate"},
            investigation_steps=[],
            evidences=[],
            final_response="Sales dropped by 34%."
        )

        response = self.client.post(
            '/api/kiki/chat/',
            {"question": "Why did ABC Traders sales decrease?"},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["question"], "Why did ABC Traders sales decrease?")
        self.assertIn("Sales dropped", response.data["final_response"])


class KikiKPIResolverTestCase(TestCase):
    """Test suite for KPIFastPath resolver."""

    def test_kpi_resolver_sales(self):
        from core.kiki.query.kpi_resolver import KPIResolver
        res = KPIResolver.resolve("What is the total sales?")
        self.assertIsNotNone(res)
        self.assertIn("total sales", res.final_response.lower())


class KikiIntentRouterAndNavigationTestCase(TestCase):
    """Test suite for IntentRouter, NavigationEngine, and HelpHandler."""

    def test_intent_router_classification(self):
        from core.kiki.router.intent_router import IntentRouter
        self.assertEqual(IntentRouter.classify_intent("Hi"), "GREETING")
        self.assertEqual(IntentRouter.classify_intent("Open Vendor Portal"), "NAVIGATION")
        self.assertEqual(IntentRouter.classify_intent("How do I create a vendor?"), "HELP")
        self.assertEqual(IntentRouter.classify_intent("Total sales"), "KPI_QUERY")
        self.assertEqual(IntentRouter.classify_intent("Why did sales decrease?"), "BUSINESS_INVESTIGATION")

    def test_navigation_engine(self):
        from core.kiki.navigation.navigation_engine import NavigationEngine
        res = NavigationEngine.navigate("go to the voucher")
        self.assertEqual(res["intent"], "NAVIGATION")
        self.assertEqual(res["module"], "Voucher Entry")


    def test_evidence_validator_zero_rows(self):
        from core.kiki.evidence.evidence_validator import EvidenceValidator
        from core.kiki.models.dto import EvidencePackage, QueryResultData
        empty_pkg = EvidencePackage(
            step_number=1,
            step_description="Scan vouchers",
            query="SELECT * FROM vouchers WHERE party = 'NONEXISTENT';",
            rows=[],
            metadata={"rows_count": 0}
        )

        resp = EvidenceValidator.validate_and_ground_response("Hallucinated answer", [empty_pkg], "Find nonexistent vendor")
        self.assertIn("could not find any transaction records", resp)




