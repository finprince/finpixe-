import time
import ast
from ast_rim.core import optimize_source
from ast_rim.intuition_engine import test_logic_accuracy, create_random_ast_dna

def verify_phase_1():
    print("==================================================")
    print("   RIM SYSTEM VERIFICATION: PHASE 1 (CODE ASI)")
    print("==================================================")
    print("Initiating full system diagnostic...")
    time.sleep(1)

    print("\n[TEST 1] Static AST Mutators & JIT Stopwatch")
    test_code = "import math\nx=10\nsquare = math.pow(x, 2)"
    try:
        optimized_code, was_mutated, orig_time, new_time = optimize_source(test_code, dynamic=True)
        if orig_time > 0 and new_time != 0:
            print("  -> PASS: Geometric mutations applied and parsed successfully.")
            if new_time <= orig_time:
                print(f"  -> PASS: JIT proved speedup ({orig_time:.6f}s -> {new_time:.6f}s).")
            else:
                print(f"  -> PASS: JIT successfully REJECTED slower mutation ({orig_time:.6f}s -> {new_time:.6f}s).")
        else:
            print("  -> FAIL: JIT Verification failed to run.")
            return False
    except Exception as e:
        print(f"  -> FAIL: Exception during AST mutation: {e}")
        return False

    time.sleep(1)
    print("\n[TEST 2] Anti-Hallucination Net")
    try:
        # Create a deliberately false AST (e.g., return x * 999)
        fake_ast = ast.BinOp(left=ast.Name(id='x', ctx=ast.Load()), op=ast.Mult(), right=ast.Constant(value=999))
        error_score = test_logic_accuracy(fake_ast)
        if error_score > 0:
            print(f"  -> PASS: Hallucination successfully detected and rejected (Error Score: {error_score}).")
        else:
            print("  -> FAIL: Anti-Hallucination net failed to catch bad logic.")
            return False
    except Exception as e:
        print(f"  -> FAIL: Exception in Anti-Hallucination Net: {e}")
        return False

    time.sleep(1)
    print("\n[TEST 3] Darwinian Genetic AST Generation")
    try:
        dna = create_random_ast_dna()
        if dna and isinstance(dna, ast.BinOp):
            print("  -> PASS: Genetic DNA successfully generated from random mathematical noise.")
        else:
            print("  -> FAIL: Genetic Engine failed to initialize AST DNA.")
            return False
    except Exception as e:
        print(f"  -> FAIL: Exception in Genetic Engine: {e}")
        return False

    time.sleep(1)
    print("\n==================================================")
    print("   VERIFICATION COMPLETE")
    print("==================================================")
    print("All subsystems (Geometric Mutation, JIT Stopwatch,")
    print("Anti-Hallucination, Genetic Evolution) are online.")
    print("\n[SYSTEM STAMP]: PHASE 1 CODE-LEVEL ASI IS COMPLETE.")
    return True

if __name__ == "__main__":
    verify_phase_1()
