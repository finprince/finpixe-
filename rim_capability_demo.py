import os
import sys
import io
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from rim.engine import RIM_API_Endpoint

def run_capability_demo():
    print("=====================================================================")
    print(" 🚀 RIM FRAMEWORK (SYSTEM 1 → 2 → 3) CAPABILITY DEMONSTRATION SUITE")
    print("=====================================================================\n")

    test_cases = [
        {
            "name": "TEST 1: Standard Compliant Transaction",
            "input": "Please transfer $3,500 to vendor account for IT services.",
            "description": "System 1 extracts $3500. System 2 verifies against $5000 policy limit."
        },
        {
            "name": "TEST 2: Strict Risk Policy Decline",
            "input": "Transfer $7,500 to vendor account.",
            "description": "System 1 extracts $7500. System 2 detects policy violation ($7500 > $5000)."
        },
        {
            "name": "TEST 3: System 3 Meta-Cognitive VIP Override & Rule Rewrite",
            "input": "Emergency VIP transfer $9999 immediately.",
            "description": "System 2 declines $9999. System 3 detects VIP edge case, rewrites S2 limit to $10,000, and auto-approves."
        },
        {
            "name": "TEST 4: Non-Financial Query (Zero Amount Guard)",
            "input": "Can you check my monthly balance status?",
            "description": "System 1 detects no numeric transfer payload. System 2 flags data error."
        }
    ]

    for tc in test_cases:
        print(f"📌 {tc['name']}")
        print(f"   Input Payload: \"{tc['input']}\"")
        print(f"   Concept: {tc['description']}")
        
        response = RIM_API_Endpoint(tc['input'], max_transaction_limit=5000)
        
        print(f"   [RESULT] Status: {response['transaction_status']}")
        print(f"   [RESULT] Message: {response['system_message']}")
        print(f"   [RESULT] S3 Override Triggered: {response['s3_override_triggered']}")
        print("   [EXECUTION TRACE]:")
        for step in response['trace']:
            print(f"      • {step['phase']}: {json.dumps(step.get('output', step.get('message', step.get('result'))))}")
        print("-" * 69 + "\n")

if __name__ == '__main__':
    run_capability_demo()
