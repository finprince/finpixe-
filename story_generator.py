import random
import string
import time

TARGET_STORY = "The smart code evolved."
GENES = string.ascii_letters + " ."

def llm_draft():
    print("==================================================")
    print("   DRAFTING STORY WITHOUT RIM (LLM MODE)")
    print("==================================================")
    print("The LLM instantly predicts the tokens and prints the story:")
    time.sleep(1)
    print(f"\n-> '{TARGET_STORY}'\n")

def calculate_fitness(candidate):
    # RIM Intuition: Calculate how close the candidate string is to the target
    # Lower score is better (0 is a perfect match)
    score = 0
    for i in range(len(TARGET_STORY)):
        if candidate[i] != TARGET_STORY[i]:
            score += 1
    return score

def generate_random_dna():
    return "".join(random.choice(GENES) for _ in range(len(TARGET_STORY)))

def mutate(parent):
    # Randomly mutate one character in the DNA sequence
    index = random.randint(0, len(TARGET_STORY) - 1)
    new_char = random.choice(GENES)
    return parent[:index] + new_char + parent[index + 1:]

def rim_genetic_draft():
    print("==================================================")
    print("   DRAFTING STORY WITH RIM (GENETIC INTUITION)")
    print("==================================================")
    print("Starting from absolute random noise and evolving the text...")
    time.sleep(1)
    
    # 1. Initialize random garbage string
    best_dna = generate_random_dna()
    best_fitness = calculate_fitness(best_dna)
    
    generation = 0
    
    # 2. Darwinian Evolution Loop
    while best_fitness > 0:
        # Print progress every 50 generations to show the evolution
        if generation % 50 == 0:
            print(f"Gen {generation:4d} | Fitness {best_fitness:2d} | Text: {best_dna}")
            
        # Spawn a mutation
        mutated_dna = mutate(best_dna)
        mutated_fitness = calculate_fitness(mutated_dna)
        
        # RIM Intuition Judge: Does this mutation bring us closer to the target?
        if mutated_fitness < best_fitness:
            # Survival of the fittest!
            best_dna = mutated_dna
            best_fitness = mutated_fitness
            
        generation += 1

    print(f"Gen {generation:4d} | Fitness {best_fitness:2d} | Text: {best_dna}")
    print("\n[EVOLUTION COMPLETE] RIM Intuition successfully drafted the story!")

if __name__ == "__main__":
    llm_draft()
    time.sleep(1)
    rim_genetic_draft()
