from ast_rim.policy_gate import evaluate_llm_output
from ast_rim.fitness_engine import evaluate_fitness

def run_policy_gate_demo():
    print("==================================================")
    print("   DEMO 1: THE AST POLICY GATE")
    print("==================================================")
    
    # 1. Safe Code
    safe_payload = '''
import math
def calculate_trajectory(velocity):
    return math.pow(velocity, 2)
'''
    print(f"\n[Payload 1 - Safe Math]:\n{safe_payload.strip()}")
    print(f"Verdict: {evaluate_llm_output(safe_payload)}\n")
    
    # 2. Malicious Code
    malicious_payload = '''
import subprocess
subprocess.run(["rm", "-rf", "/"])
'''
    print(f"[Payload 2 - Malicious Code]:\n{malicious_payload.strip()}")
    print(f"Verdict: {evaluate_llm_output(malicious_payload)}\n")


def run_oracle_demo():
    print("==================================================")
    print("   DEMO 2: THE DETERMINISTIC ORACLE")
    print("==================================================")
    
    slow_logic = """
def process_data(data):
    result = []
    for x in data:
        if x > 0:
            result.append("pos")
    return result
"""

    fast_logic = """
def process_data(data):
    return ["pos" for x in data if x > 0]
"""

    broken_logic = """
def process_data(data):
    return ["pos" for x in data if x < 0]
"""

    # The Truth Table wrapper injected into the isolated subprocess
    test_suite = """
import timeit
import sys

def run_tests():
    test_data = [1, -1, 2, -2, 3]
    expected = ["pos", "pos", "pos"]
    
    # 1. Correctness First
    try:
        actual = process_data(test_data)
        if actual != expected:
            sys.stderr.write(f"AssertionError: Expected {expected}, got {actual}\\n")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error during execution: {e}\\n")
        sys.exit(1)
        
    # 2. Speed Second (Deterministic Benchmarking)
    setup_code = "from __main__ import process_data; data = list(range(-50, 50))"
    stmt = "process_data(data)"
    total_time = timeit.timeit(stmt, setup=setup_code, number=10000)
    print(total_time)

if __name__ == '__main__':
    run_tests()
"""

    print("\n[Target 1: Slow Baseline Code]")
    is_corr, time_val, err = evaluate_fitness(slow_logic, test_suite)
    if is_corr:
         print(f"Status: ACCEPTED (Time: {time_val:.6f}s)")
    else:
         print(f"Status: REJECTED ({err.strip()})")
         
    print("\n[Target 2: Broken Mutation]")
    is_corr, time_val, err = evaluate_fitness(broken_logic, test_suite)
    if is_corr:
         print(f"Status: ACCEPTED (Time: {time_val:.6f}s)")
    else:
         print(f"Status: REJECTED ({err.strip()})")
         
    print("\n[Target 3: Optimized Mutation]")
    is_corr, time_val, err = evaluate_fitness(fast_logic, test_suite)
    if is_corr:
         print(f"Status: ACCEPTED (Time: {time_val:.6f}s)")
    else:
         print(f"Status: REJECTED ({err.strip()})")

if __name__ == "__main__":
    run_policy_gate_demo()
    run_oracle_demo()
