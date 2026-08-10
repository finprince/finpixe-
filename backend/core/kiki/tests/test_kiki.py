"""
KIKI AI Operating System Unit & Integration Tests
=================================================
Tests Phase 1 through 18 implementation components.
"""
from unittest import TestCase
from unittest.mock import MagicMock
from core.kiki.exceptions import KikiSQLValidationException
from core.kiki.security import sql_validator, tenant_guard
from core.kiki.metadata import metadata_registry
from core.kiki.ontology import ontology_graph
from core.kiki.router import intent_classifier
from core.kiki.schema_engine import schema_selector
from core.kiki.kernel import ai_kernel


class KikiArchitectureTestCase(TestCase):
    
    def setUp(self):
        self.user = MagicMock()
        self.user.id = 1
        self.user.username = "test_kiki_user"
        self.user.email = "test_kiki@example.com"
        self.user.tenant_id = "cmp_test_001"
        self.user.company_name = "Test Company"

    def test_tenant_guard_extraction(self):
        ctx = tenant_guard.extract_context(self.user)
        self.assertIsNotNone(ctx["tenant_id"])
        self.assertEqual(ctx["user_id"], self.user.id)

    def test_sql_validator_read_only_and_tenant_shield(self):
        valid_sql = "SELECT * FROM voucher_header WHERE tenant_id = %s"
        is_valid, msg = sql_validator.validate(valid_sql, "cmp_test_001")
        self.assertTrue(is_valid)

        # Test DDL/DML Rejection
        with self.assertRaises(KikiSQLValidationException):
            sql_validator.validate("DELETE FROM voucher_header WHERE tenant_id = %s", "cmp_test_001")

        # Test Missing Tenant Filter Rejection
        with self.assertRaises(KikiSQLValidationException):
            sql_validator.validate("SELECT * FROM voucher_header", "cmp_test_001")

    def test_metadata_registry_scan(self):
        catalog = metadata_registry.get_catalog()
        self.assertIn("tables", catalog)
        self.assertIsInstance(catalog["tables"], dict)

    def test_ontology_domain_mapping(self):
        domain = ontology_graph.resolve_domain_for_term("Sales Invoice")
        self.assertEqual(domain, "Sales")

    def test_intent_classification_navigation(self):
        res = intent_classifier.classify("Take me to Sales Orders")
        self.assertEqual(res["intent"], "NAVIGATION")

    def test_ai_kernel_end_to_end_request(self):
        res = ai_kernel.process_request("Show sales vouchers", self.user)
        self.assertIn("id", res)
        self.assertIn("intent", res)
        self.assertIn("reply", res)
        self.assertIn("evidence_package", res)
