from ast_rim.core import optimize_source

unoptimized_python = """
import math

def process_data(data, user_dict):
    # Example 1: Math Overhead
    x = 10
    square = math.pow(x, 2)
    
    # Example 2: Inefficient Dict Lookup
    if "admin_id" in user_dict:
        role = user_dict["admin_id"]
    else:
        role = "guest"
        
    # Example 3: Memory Wasting Loop (appending instead of extending)
    new_data = [4, 5, 6]
    for item in new_data:
        data.append(item)
        
    # Example 4: List Comprehension Loop
    result = []
    for num in data:
        result.append(num * square)
        
    return result

# Execute it so JIT can time it!
_ = process_data([1, 2, 3], {"admin_id": 99})
"""

def run_python_demonstration():
    print("==================================================")
    print("   AST-RIM PYTHON INTUITION FLOW DEMONSTRATION")
    print("==================================================")
    print("\n[STEP 1] Raw LLM Code Detected:")
    print(unoptimized_python)
    
    print("[STEP 2] RIM parsing Python into Abstract Syntax Tree...")
    print("[STEP 3] Applying Geometric Mutations & JIT Stopwatch...\n")
    
    # We turn dynamic=True so the JIT racer actually times the execution speed
    optimized_code, was_mutated = optimize_source(unoptimized_python, dynamic=True)
    
    if was_mutated:
        print("\n==================================================")
        print("   FINAL RIM-OPTIMIZED PYTHON CODE:")
        print("==================================================")
        print(optimized_code)
    else:
        print("Code was already optimal or JIT rejected the mutation.")

if __name__ == "__main__":
    run_python_demonstration()
