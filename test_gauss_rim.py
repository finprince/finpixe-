import random
import time

# 1. The LLM Hallucination (O(N) Time Complexity)
def slow_llm_loop(n):
    total = 0
    for i in range(n + 1):
        total += i
    return total

# 2. The Mathematical AST Template
# RIM will genetically evolve the operators and variables in this equation:
# Formula: ((N {op1} {val1}) {op2} N) {op3} {val3}
OPERATORS = ['+', '-', '*', '/']
VARIABLES = ['N', '1', '2', '3']

class MathAST:
    def __init__(self, op1, val1, op2, op3, val3):
        self.op1 = op1
        self.val1 = val1
        self.op2 = op2
        self.op3 = op3
        self.val3 = val3
        
    def get_equation_string(self):
        return f"((N {self.op1} {self.val1}) {self.op2} N) {self.op3} {self.val3}"
        
    def evaluate(self, N):
        """The JIT Math Execution Engine"""
        eq = self.get_equation_string().replace('N', str(N))
        try:
            return eval(eq)
        except ZeroDivisionError:
            return float('inf')

def calculate_fitness(ast_node):
    """The Anti-Hallucination Net: Does the formula match the loop?"""
    error = 0
    # Test the equation against the slow loop for random N values
    test_cases = [10, 50, 100, 500]
    for n in test_cases:
        truth = slow_llm_loop(n)
        prediction = ast_node.evaluate(n)
        error += abs(truth - prediction)
    return error

def mutate_ast(parent):
    """Genetic algorithm: randomly mutate a math node in the equation"""
    child = MathAST(parent.op1, parent.val1, parent.op2, parent.op3, parent.val3)
    mutation_point = random.randint(1, 5)
    
    if mutation_point == 1:
        child.op1 = random.choice(OPERATORS)
    elif mutation_point == 2:
        child.val1 = random.choice(VARIABLES)
    elif mutation_point == 3:
        child.op2 = random.choice(OPERATORS)
    elif mutation_point == 4:
        child.op3 = random.choice(OPERATORS)
    elif mutation_point == 5:
        child.val3 = random.choice(VARIABLES)
        
    return child

def main():
    print("==================================================")
    print("   TEST: ALGORITHMIC COMPLEXITY DISCOVERY")
    print("==================================================")
    print("Objective: Evolve an O(1) formula to replace an O(N) loop.")
    
    # LLM hallucinates a random, wrong formula
    llm_ast = MathAST('+', '1', '-', '*', '3')
    llm_error = calculate_fitness(llm_ast)
    
    print(f"\n[LLM Loop Speed]   O(N) Time Complexity")
    print(f"[LLM Math Guess]   {llm_ast.get_equation_string()} (Math Error: {llm_error})")
    print("[REJECTED] Math is hallucinated. Triggering Genetic Equation Engine...\n")
    
    best_ast = llm_ast
    best_error = llm_error
    
    generation = 0
    while best_error > 0:
        if generation % 100 == 0:
            print(f"Gen {generation:4d} | Math Error: {best_error:10.1f} | Eq: {best_ast.get_equation_string()}")
            
        mutated = mutate_ast(best_ast)
        mutated_error = calculate_fitness(mutated)
        
        # Survival of the fittest equation
        if mutated_error < best_error:
            best_ast = mutated
            best_error = mutated_error
            
        # Add random genetic drift if stuck in local minima
        if generation > 0 and generation % 500 == 0 and best_error > 0:
            best_ast = mutate_ast(best_ast)
            
        generation += 1

    print(f"Gen {generation:4d} | Math Error: {best_error:10.1f} | Eq: {best_ast.get_equation_string()}")

    print("\n[SUCCESS] O(1) ALGORITHM DISCOVERED!")
    print(f"[MOVE 37 DISCOVERED] RIM mathematically evolved Gauss's Formula:")
    print(f"Final O(1) Equation: {best_ast.get_equation_string()}")
    
    print("\n[FINAL VERIFICATION]")
    N = 1000000
    print(f"Testing huge number (N = {N})...")
    start = time.time()
    truth = slow_llm_loop(N)
    loop_time = time.time() - start
    
    start = time.time()
    rim_answer = best_ast.evaluate(N)
    rim_time = time.time() - start
    
    print(f"LLM O(N) Loop Answer: {truth} (Time: {loop_time:.4f}s)")
    print(f"RIM O(1) Math Answer: {int(rim_answer)} (Time: {rim_time:.4f}s)")
    
    speedup = loop_time / rim_time if rim_time > 0 else float('inf')
    print(f"\nAST-RIM is {speedup:,.0f}x faster than the LLM's original code.")

if __name__ == "__main__":
    main()
