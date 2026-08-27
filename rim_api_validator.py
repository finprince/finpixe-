import os
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.urls import get_resolver, URLPattern, URLResolver
from rest_framework.test import APIClient

class System1_EndpointDiscovery:
    """System 1 (Perception): Discovers all registered API endpoints."""

    def extract_urls(self, urlpatterns=None, prefix=''):
        if urlpatterns is None:
            urlpatterns = get_resolver().url_patterns

        endpoints = []
        for pattern in urlpatterns:
            if isinstance(pattern, URLPattern):
                path_str = prefix + str(pattern.pattern)
                # Clean up regex or path formatting
                path_clean = '/' + path_str.lstrip('/')
                # Replace url parameters like <str:session_id> or <uuid:job_id> with dummy values for testing
                test_path = re.sub(r'<[^:>]+:([^>]+)>', r'test-\1', path_clean)
                test_path = re.sub(r'<([^>]+)>', r'test-\1', test_path)
                
                endpoints.append({
                    "raw_pattern": path_clean,
                    "test_path": test_path,
                    "name": pattern.name,
                    "callback": str(pattern.callback)
                })
            elif isinstance(pattern, URLResolver):
                new_prefix = prefix + str(pattern.pattern)
                endpoints.extend(self.extract_urls(pattern.url_patterns, new_prefix))
        return endpoints

import re

class System2_APIEndpointTester:
    """System 2 (Deterministic Rules Engine): Tests every API endpoint."""

    def __init__(self, endpoints):
        self.endpoints = endpoints
        self.client = APIClient()

    def test_all_endpoints(self):
        results = []
        status_counts = {}

        for ep in self.endpoints:
            url = ep["test_path"]
            
            # Skip media/static paths
            if url.startswith('/media') or url.startswith('/static') or 'schema' in url or 'docs' in url:
                continue

            try:
                # Issue GET request first
                response = self.client.get(url)
                code = response.status_code

                status_counts[code] = status_counts.get(code, 0) + 1
                
                # Evaluation:
                # 200, 201, 204: Success
                # 400, 401, 403, 404, 405: Valid DRF / Django response (auth/params working)
                # 500: Server Exception (CRITICAL FAIL)
                passed = code in [200, 201, 204, 400, 401, 403, 404, 405]
                is_500 = code >= 500

                results.append({
                    "url": url,
                    "pattern": ep["raw_pattern"],
                    "name": ep["name"],
                    "status_code": code,
                    "passed": passed,
                    "is_500": is_500
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "pattern": ep["raw_pattern"],
                    "name": ep["name"],
                    "status_code": 500,
                    "passed": False,
                    "is_500": True,
                    "error": str(e)
                })

        return results, status_counts


class System3_MetaCognitiveAPIAuditor:
    """System 3 (Meta-Cognition): Evaluates overall API Ecosystem Health."""

    def __init__(self, s1, s2):
        self.s1 = s1
        self.s2 = s2

    def run_api_audit(self):
        print("\n=======================================================")
        print(" RIM SYSTEM 1-2-3 ALL API ENDPOINTS VALIDATION REPORT")
        print("=======================================================\n")

        # System 1: Endpoint Discovery
        print("[SYSTEM 1 - ENDPOINT DISCOVERY & ROUTE RESOLUTION]")
        endpoints = self.s1.extract_urls()
        print(f"  -> Total Registered API Routes Found: {len(endpoints)}")

        # System 2: Deterministic Testing
        print("\n[SYSTEM 2 - DETERMINISTIC HTTP API VERIFICATION]")
        test_results, status_counts = self.s2.test_all_endpoints()
        
        total_tested = len(test_results)
        passed_count = sum(1 for r in test_results if r["passed"])
        server_errors = [r for r in test_results if r["is_500"]]

        print(f"  -> Total Endpoints Tested: {total_tested}")
        print("  -> Status Code Telemetry:")
        for code, count in sorted(status_counts.items()):
            desc = {
                200: "200 OK (Public/Success)",
                201: "201 Created",
                400: "400 Bad Request (Validation Active)",
                401: "401 Unauthorized (Auth Layer Active)",
                403: "403 Forbidden (RBAC Guard Active)",
                404: "404 Not Found",
                405: "405 Method Not Allowed",
                500: "500 Internal Server Error (CRITICAL)"
            }.get(code, f"{code} Response")
            print(f"      - {code} [{desc}]: {count} endpoint(s)")

        if server_errors:
            print(f"\n  [FAIL] Server Errors (500) Detected ({len(server_errors)}):")
            for err in server_errors:
                print(f"   - {err['url']} (pattern: {err['pattern']}) -> Error: {err.get('error', '500 Internal Error')}")
        else:
            print("\n  [PASS] Zero 500 Server Errors Detected! All endpoints handled cleanly.")

        # System 3: Health Score Calculation
        print("\n=======================================================")
        health_score = int(((total_tested - len(server_errors)) / total_tested) * 100) if total_tested > 0 else 0
        
        print(f" ALL API ENDPOINTS HEALTH INDEX: {health_score}/100")
        print("=======================================================")
        print("Summary:")
        print(f" -> Total Discovered Routes: {len(endpoints)}")
        print(f" -> Tested Endpoints: {total_tested}")
        print(f" -> Protected/Auth Secured Endpoints: {status_counts.get(401, 0) + status_counts.get(403, 0)}")
        print(f" -> 500 Exception Free Rate: {health_score}%")
        print("=======================================================\n")

if __name__ == '__main__':
    s1 = System1_EndpointDiscovery()
    endpoints = s1.extract_urls()
    s2 = System2_APIEndpointTester(endpoints)
    s3 = System3_MetaCognitiveAPIAuditor(s1, s2)
    s3.run_api_audit()
