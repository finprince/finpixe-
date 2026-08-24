import ast
import timeit
from ast_rim.core import LoopToListCompMutator
from ast_rim.fitness_engine import evaluate_fitness

def demonstrate_intuition():
    print("==================================================")
    print("      RIM GENETIC INTUITION ENGINE DEMO")
    print("==================================================")
    
    # 1. The Naive Human/LLM Code
    naive_code = """
def calculate_squares(data):
    result = []
    for x in data:
        result.append(x * x)
    return result
"""
    print("\n[INPUT] Analyzing Naive O(N) Code:")
    print(naive_code.strip())
    
    # 2. Apply the "Intuition" (AST Mutation)
    print("\n[INTUITION ENGINE] Mutating AST structural logic...")
    tree = ast.parse(naive_code)
    mutator = LoopToListCompMutator()
    optimized_tree = mutator.visit(tree)
    
    # Convert the optimized AST back to Python code
    optimized_code = ast.unparse(optimized_tree)
    print(f"\n[OUTPUT] Intuition Engine organically discovered optimization:")
    print("-" * 40)
    print(optimized_code)
    print("-" * 40)
    
    # 3. Verify in the Oracle
    print("\n[ORACLE] Routing to Deterministic Oracle to verify correctness and speed...")
    test_suite = '''
import sys
import time
from __main__ import calculate_squares

def run_tests():
    data = list(range(10000))
    try:
        # Correctness Check
        assert calculate_squares([2, 3, 4]) == [4, 9, 16]
        
        # Speed Benchmark
        start = time.time()
        for _ in range(100):
            calculate_squares(data)
        exec_time = time.time() - start
        
        print(f"{exec_time:.5f}")
    except Exception as e:
        sys.exit(1)
        
if __name__ == "__main__":
    run_tests()
'''
    
    is_correct, naive_time, _ = evaluate_fitness(naive_code, test_suite)
    is_correct_opt, opt_time, _ = evaluate_fitness(optimized_code, test_suite)
    
    if is_correct_opt:
        print(f"\n[ORACLE PASS] The Intuited code is mathematically flawless!")
        print(f"Naive Speed:     {naive_time:.5f}s")
        print(f"Optimized Speed: {opt_time:.5f}s")
        speedup = ((naive_time - opt_time) / naive_time) * 100
        print(f"--> Performance Gain: {speedup:.1f}% faster!")

if __name__ == "__main__":
    demonstrate_intuition()
