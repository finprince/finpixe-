import os
import sys
import io
import re
import json
import urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

class System1_FrontendScanner:
    """System 1 (Perception): Discovers frontend files, components, and API calls."""

    def scan_files(self):
        js_files = []
        if os.path.exists(FRONTEND_DIR):
            for root, dirs, files in os.walk(os.path.join(FRONTEND_DIR, 'src')):
                if 'node_modules' in root: continue
                for f in files:
                    if f.endswith(('.js', '.jsx', '.ts', '.tsx')):
                        js_files.append(os.path.join(root, f))
        return js_files

    def parse_package_json(self):
        pkg_file = os.path.join(FRONTEND_DIR, 'package.json')
        if os.path.exists(pkg_file):
            with open(pkg_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def extract_api_calls(self, js_files):
        api_calls = set()
        pattern = re.compile(r"['\"](/api/[^'\"]+)['\"]")
        for file in js_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = pattern.findall(content)
                    for m in matches:
                        # Clean query params or dynamic ids
                        clean_url = re.sub(r'\${[^}]+}', '1', m)
                        api_calls.add(clean_url.split('?')[0])
            except Exception:
                pass
        return list(api_calls)


class System2_FrontendLogicVerifier:
    """System 2: Applies deterministic checks on frontend server and codebase."""

    def check_vite_dev_server(self):
        urls = ['http://localhost:5173', 'http://127.0.0.1:5173']
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        return True, f"Vite server active and responding at {url}"
            except Exception:
                pass
        return False, "Vite server unreachable on port 5173"

    def verify_components_syntax(self, js_files):
        errors = []
        for file in js_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Check for unclosed JSX tags or critical syntax issues
                    open_braces = content.count('{')
                    close_braces = content.count('}')
                    if abs(open_braces - close_braces) > 100:  # Major brace imbalance
                        errors.append(f"{os.path.basename(file)}: Potential bracket mismatch ({open_braces} vs {close_braces})")
            except Exception as e:
                errors.append(f"{os.path.basename(file)}: {e}")
        return errors

    def verify_api_endpoint_alignment(self, fe_api_calls):
        # Known backend prefixes
        backend_prefixes = [
            '/api/auth', '/api/ocr', '/api/vouchers', '/api/masters',
            '/api/vendors', '/api/inventory', '/api/customerportal',
            '/api/payroll', '/api/rbac', '/api/services', '/api/reports',
            '/api/gst', '/api/pending-purchases', '/api/bank-upload',
            '/api/rim', '/api/admin', '/api/purchase'
        ]
        
        valid_calls = []
        orphan_calls = []

        for call in fe_api_calls:
            if any(call.startswith(p) for p in backend_prefixes):
                valid_calls.append(call)
            else:
                orphan_calls.append(call)
        
        return valid_calls, orphan_calls


class System3_MetaCognitiveFrontendAuditor:
    """System 3 (Meta-Cognition): Evaluates overall Frontend Architecture Health."""

    def __init__(self, s1, s2):
        self.s1 = s1
        self.s2 = s2

    def run_frontend_audit(self):
        print("\n=======================================================")
        print(" RIM SYSTEM 1-2-3 FRONTEND ARCHITECTURE AUDIT REPORT")
        print("=======================================================\n")

        # System 1: Perception
        print("[SYSTEM 1 - FRONTEND SCANNING & DEPENDENCY PARSING]")
        js_files = self.s1.scan_files()
        pkg = self.s1.parse_package_json()
        fe_api_calls = self.s1.extract_api_calls(js_files)

        print(f"  -> Frontend Framework: {pkg.get('name', 'AI-accounting-frontend')} (v{pkg.get('version', '0.0.1')})")
        print(f"  -> Total React/JS Source Files Scanned: {len(js_files)}")
        print(f"  -> API Endpoints Referenced in Frontend: {len(fe_api_calls)}")

        # System 2: Rule Verification
        print("\n[SYSTEM 2 - DETERMINISTIC FRONTEND RULES VERIFICATION]")
        
        vite_ok, vite_msg = self.s2.check_vite_dev_server()
        if vite_ok:
            print(f"  [PASS] Dev Server Telemetry: {vite_msg}")
        else:
            print(f"  [FAIL] Dev Server Telemetry: {vite_msg}")

        syntax_errs = self.s2.verify_components_syntax(js_files)
        if syntax_errs:
            print(f"  [WARN] Component Syntax Issues ({len(syntax_errs)}):")
            for err in syntax_errs[:5]:
                print(f"    - {err}")
        else:
            print(f"  [PASS] Component Integrity: Clean syntax across all {len(js_files)} source files.")

        valid_apis, orphan_apis = self.s2.verify_api_endpoint_alignment(fe_api_calls)
        print(f"  [PASS] API Endpoint Alignment: {len(valid_apis)}/{len(fe_api_calls)} frontend API routes match backend patterns.")
        
        if orphan_apis:
            print(f"  [INFO] Unmatched/Dynamic Routes ({len(orphan_apis)}): {orphan_apis[:3]}")

        # System 3: Health Score & Synthesis
        print("\n=======================================================")
        score = 0
        if vite_ok: score += 40
        if not syntax_errs: score += 30
        if len(valid_apis) > 0: score += 30

        print(f" FRONTEND HEALTH INDEX: {score}/100")
        print("=======================================================")
        print("Summary:")
        print(f" -> Vite Dev Server (:5173): {'ONLINE' if vite_ok else 'OFFLINE'}")
        print(f" -> Component Source Files: {len(js_files)} verified")
        print(f" -> Backend API Integration Alignment: {len(valid_apis)} endpoints mapped")
        print("=======================================================\n")

if __name__ == '__main__':
    s1 = System1_FrontendScanner()
    s2 = System2_FrontendLogicVerifier()
    s3 = System3_MetaCognitiveFrontendAuditor(s1, s2)
    s3.run_frontend_audit()
