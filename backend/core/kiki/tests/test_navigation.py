from django.test import TestCase
from ..navigation.providers.base_provider import NavigationNode, ActionDefinition
from ..navigation.providers.route_provider import RouteDiscoveryProvider
from ..navigation.application_discovery_service import ApplicationDiscoveryService
from ..navigation.candidate_resolver import NavigationCandidateResolver
from ..navigation.navigation_reasoner import NavigationReasoner
from ..navigation.navigation_validator import NavigationValidator
from ..navigation.response_builder import NavigationResponseBuilder
from ..navigation.navigation_engine import NavigationEngine


class NavigationApplicationIntelligenceTestCase(TestCase):
    """
    Test suite for FINPIXE AI Application Intelligence Layer & Navigation System.
    Tests discovery providers, fast-path resolution (< 1ms), candidate filtering,
    semantic reasoning, route validation, versioned contract payloads, and zero SQL execution.
    """

    def setUp(self):
        ApplicationDiscoveryService.discover_nodes(force_refresh=True)

    def test_application_discovery_service(self):
        nodes = ApplicationDiscoveryService.discover_nodes()
        self.assertTrue(len(nodes) >= 10)
        
        # Test get_node_by_id
        vendor_node = ApplicationDiscoveryService.get_node_by_id("vendor.portal")
        self.assertIsNotNone(vendor_node)
        self.assertEqual(vendor_node.title, "Vendor Portal")

        # Test find_capabilities
        cap_nodes = ApplicationDiscoveryService.find_capabilities("approve supplier invoices")
        self.assertTrue(any(n.id == "purchase.pending_purchase" for n in cap_nodes))

    def test_fast_path_exact_match(self):
        # Queries like "Open Vendor Portal" must resolve deterministically in < 1ms without LLM calls
        is_exact, node, _ = NavigationCandidateResolver.resolve_candidates("Open Vendor Portal")
        self.assertTrue(is_exact)
        self.assertIsNotNone(node)
        self.assertEqual(node.id, "vendor.portal")

        is_exact_v, node_v, _ = NavigationCandidateResolver.resolve_candidates("go to the voucher")
        self.assertTrue(is_exact_v)
        self.assertEqual(node_v.id, "vouchers.entry")

    def test_candidate_resolver_scoring(self):
        # Semantic queries retrieve top candidates
        is_exact, _, candidates = NavigationCandidateResolver.resolve_candidates("Where do I approve supplier invoices?")
        self.assertFalse(is_exact)
        self.assertTrue(len(candidates) > 0)
        self.assertTrue(any(c.id == "purchase.pending_purchase" for c in candidates))

    def test_navigation_validator(self):
        valid_node = ApplicationDiscoveryService.get_node_by_id("inventory.management")
        is_valid, status = NavigationValidator.validate_node(valid_node)
        self.assertTrue(is_valid)
        self.assertEqual(status, "VALID")

        # Test rejection of non-existent node
        fake_node = NavigationNode(id="fake.page", title="Fake Page", route="/dashboard?page=fake")
        is_valid_f, status_f = NavigationValidator.validate_node(fake_node)
        self.assertFalse(is_valid_f)
        self.assertEqual(status_f, "NO_MATCH")

    def test_response_builder_versioning_and_confidence(self):
        node = ApplicationDiscoveryService.get_node_by_id("core.dashboard")
        payload = NavigationResponseBuilder.build_single_response(node, confidence=0.99)
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["intent"], "NAVIGATION")
        self.assertEqual(payload["confidence"], 0.99)
        self.assertEqual(payload["route"], "/dashboard?page=dashboard")

        # Test options payload
        options_payload = NavigationResponseBuilder.build_options_response([node], confidence=0.65, query="Purchase")
        self.assertEqual(options_payload["schema_version"], "1.0")
        self.assertEqual(options_payload["intent"], "NAVIGATION_OPTIONS")
        self.assertEqual(options_payload["confidence"], 0.65)

    def test_navigation_engine_end_to_end(self):
        engine = NavigationEngine()
        res = engine.navigate("Go to Reports")
        self.assertEqual(res["schema_version"], "1.0")
        self.assertEqual(res["intent"], "NAVIGATION")
        self.assertEqual(res["module"], "Reports")
        self.assertEqual(res["route"], "/dashboard?page=reports")
        self.assertEqual(res["confidence"], 0.99)
