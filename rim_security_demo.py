from rim_gateway.rim_security import RIMSecurityAnalyzer

print("=======================================================")
print("  RIM SECURITY WORKFLOW DEMO")
print("=======================================================\n")

# 1. Developer modifies code
vulnerable_code = """
import requests
import ast

def get_user_data(user_id, user_input):
    # DANGEROUS: SQL Injection (f-string)
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    
    # DANGEROUS: eval()
    result = eval(user_input)
    return result
"""

dependencies = {
    "requests": "2.19.0", # Has a known CVE
    "django": "3.0.0"     # Has a known CVE
}

print("-> DEVELOPER COMMIT TRIGGERED.")
print("-> CURRENT DEPENDENCIES:", dependencies)
print("-> CURRENT CODE:")
print(vulnerable_code)
print("-" * 50)

# 2. Parallel Security Workflow Initialization
analyzer = RIMSecurityAnalyzer()

# 3. Analyze (NVD + RIM)
report = analyzer.analyze(vulnerable_code, dependencies)

print(f"\n[RISK ANALYSIS] Overall Risk Level: {report['risk_level']}")
print("[FINDINGS]:")
for v in report['findings']:
    print(f"  - [{v.source}] {v.vuln_id} ({v.severity}): {v.description}")

print("-" * 50)

# 4. Remediation (Code Fix Generation)
fixed_code, fixed_deps = analyzer.remediate(report, vulnerable_code, dependencies)

print("[PROPOSED FIX] Dependency Updates:")
for k, v in fixed_deps.items():
    if dependencies[k] != v:
        print(f"  - {k}: {dependencies[k]} -> {v}")

print("\n[PROPOSED FIX] Code Changes (Diff):")
print(fixed_code)

print("-" * 50)

# 5. Fix Verification
analyzer.verify_fix(fixed_code, fixed_deps)
