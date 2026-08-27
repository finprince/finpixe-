import time
import random

class System1_Intuition:
    def __init__(self):
        # System 1 starts with basic, naive intuition
        self.learning_rate = 1.0
        self.approach = "random_guessing"

    def generate_solution(self, target_complexity):
        print(f"   [System 1] Using intuition ('{self.approach}') to generate a solution...")
        time.sleep(1)
        # Generates a solution based on its current neuroplastic state
        if self.approach == "random_guessing":
            return random.randint(1, 100)
        elif self.approach == "calculated_calibration":
            return int(target_complexity * self.learning_rate)

class System2_Logic:
    def __init__(self):
        # System 2 holds the absolute mathematical truth/laws
        self.absolute_truth = 73  # The target constraint (e.g., perfect fraud detection score)

    def evaluate(self, proposed_solution):
        print(f"   [System 2] Running strict mathematical verification on value: {proposed_solution}...")
        time.sleep(1)
        if proposed_solution == self.absolute_truth:
            print("   [System 2] RESULT: Approved. Mathematically flawless.")
            return True, 0
        else:
            error_margin = self.absolute_truth - proposed_solution
            print(f"   [System 2] RESULT: Rejected. Logic failure. Error margin: {error_margin}")
            return False, error_margin

class System3_MetaCognition:
    def __init__(self, sys1, sys2):
        print("\n[SYSTEM 3: META-COGNITION AWAKE] Overseeing Neural Architecture...")
        self.sys1 = sys1
        self.sys2 = sys2
        self.attempts = 0

    def think_about_thinking(self):
        """The Meta-Cognition Loop: Overseeing and rewriting the brain's logic."""
        print("\n========================================================")
        print("[SYSTEM 3] Initiating Cognitive Task...")
        print("========================================================")
        
        while True:
            self.attempts += 1
            print(f"\n--- Cognitive Cycle {self.attempts} ---")
            
            # Step 1: System 1 guesses
            idea = self.sys1.generate_solution(target_complexity=100)
            
            # Step 2: System 2 verifies
            approved, error = self.sys2.evaluate(idea)
            
            if approved:
                print(f"\n[SYSTEM 3] SUCCESS: Brain alignment achieved in {self.attempts} cycles.")
                break
            
            # Step 3: System 3 Meta-Cognition & Neuroplasticity (The Magic)
            print("\n[SYSTEM 3 - META-COGNITION] Conflict detected between S1 and S2.")
            print("[SYSTEM 3] Analyzing failure pattern...")
            time.sleep(1)
            
            # System 3 rewrites System 1's internal code/approach
            if self.sys1.approach == "random_guessing":
                print("[SYSTEM 3] Action: S1 intuition is too chaotic. Rewriting S1 neuro-pathways to 'calculated_calibration'.")
                self.sys1.approach = "calculated_calibration"
                self.sys1.learning_rate = 0.5 # Give it a baseline
            else:
                # Dynamically adjust the learning rate based on the exact mathematical error from S2
                adjustment = error / 100.0
                self.sys1.learning_rate += adjustment
                print(f"[SYSTEM 3] Action: Dynamically adjusting S1 neural weights. New learning rate: {self.sys1.learning_rate:.2f}")
            
            print("[SYSTEM 3] Neuroplasticity update complete. Forcing brain to re-evaluate.")
            time.sleep(1)

if __name__ == "__main__":
    # Booting up the 3-Tier Brain Architecture
    s1 = System1_Intuition()
    s2 = System2_Logic()
    
    # System 3 wraps around System 1 and System 2 to control them
    meta_brain = System3_MetaCognition(s1, s2)
    meta_brain.think_about_thinking()
