import time
from ast_rim.generator import run_evolution

STARTING_CODE = """
def compute():
    # Intentionally unoptimized code that allocates a massive list
    data = [x for x in range(500)]
    total = 0
    for num in data:
        total = total + num
    return total
"""

def main():
    print("======================================================")
    print(" [GENETIC] AST-RIM GENETIC GENERATOR (EVOLUTION) [GENETIC]")
    print("======================================================")
    
    print("\n[Stage 1] Validating Base Code & Establishing Ground Truth...")
    namespace = {}
    exec(STARTING_CODE, namespace)
    target_result = namespace["compute"]()
    print(f"-> Target Mathematical Result: {target_result}")
    
    print("\n[Stage 2] Commencing Darwinian AST Evolution...")
    print("RIM Intuition is acting as the Fitness Function (Survival of the Fastest).")
    print("Random mutations are breeding. Please wait... this may take 10-20 seconds.\n")
    
    best_code, best_fitness, history = run_evolution(
        STARTING_CODE, 
        target_result, 
        generations=20, 
        population_size=15
    )
    
    print("\n======================================================")
    print("[EVOLUTION COMPLETE]")
    
    start_time = history[0]['best_fitness'] if history else best_fitness
    print(f"Generation 0 Time: {start_time:.5f}s")
    print(f"Generation 20 Time: {best_fitness:.5f}s")
    
    if best_fitness < start_time:
        speedup = start_time / best_fitness
        print(f"-> The AI generated code that is {speedup:.2f}x faster!")
    else:
        print("-> The AI could not find a faster mutation that preserved mathematical integrity.")
        
    print("\n[FINAL GENERATED CODE]")
    print(best_code)
    print("======================================================")

if __name__ == "__main__":
    main()
